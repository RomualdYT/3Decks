/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "net.h"

#include <3ds.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <malloc.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

/*
 * Le service SOC exige un tampon aligné sur 0x1000 dont la taille est un
 * multiple de 0x1000. Il est alloué en mémoire partagée par socInit et devient
 * inaccessible au processus, on ne doit donc jamais y toucher directement.
 */
#define SOC_ALIGN 0x1000
#define SOC_BUFFER_SIZE 0x100000

static u32 *s_soc_buffer = NULL;
static bool s_soc_ready = false;

static int s_socket = -1;
static NetState s_state = NET_IDLE;
static char s_error[96] = {0};

/*
 * Tampon de réception. On accumule les octets bruts et on extrait les messages
 * dès qu'un cadre complet est disponible. La taille couvre l'en-tête plus le
 * plus grand message autorisé.
 */
static char s_rx[NET_MAX_MESSAGE + 4];
static size_t s_rx_used = 0;

/*
 * Les requêtes de la console sont petites (appui, valeur, ping). Une file
 * statique évite toute allocation et, surtout, toute attente active lorsque
 * le tampon TCP est momentanément plein.
 */
#define NET_TX_QUEUE_SIZE 8
#define NET_TX_FRAME_MAX (NET_MAX_OUTBOUND + 4)

typedef struct {
	unsigned char data[NET_TX_FRAME_MAX];
	size_t length;
	size_t offset;
} TxFrame;

static TxFrame s_tx[NET_TX_QUEUE_SIZE];
static int s_tx_head = 0;
static int s_tx_count = 0;

static void set_error(const char *message)
{
	snprintf(s_error, sizeof(s_error), "%s", message);
}

static void set_error_errno(const char *context)
{
	snprintf(s_error, sizeof(s_error), "%s (%d)", context, errno);
}

bool net_init(void)
{
	if (s_soc_ready) {
		return true;
	}

	s_soc_buffer = (u32 *)memalign(SOC_ALIGN, SOC_BUFFER_SIZE);
	if (s_soc_buffer == NULL) {
		set_error("memoire SOC indisponible");
		return false;
	}

	const Result res = socInit(s_soc_buffer, SOC_BUFFER_SIZE);
	if (R_FAILED(res)) {
		free(s_soc_buffer);
		s_soc_buffer = NULL;
		set_error("socInit a echoue");
		return false;
	}

	s_soc_ready = true;
	s_error[0] = '\0';
	return true;
}

void net_exit(void)
{
	net_disconnect();

	if (s_soc_ready) {
		socExit();
		s_soc_ready = false;
	}
	if (s_soc_buffer != NULL) {
		free(s_soc_buffer);
		s_soc_buffer = NULL;
	}
}

void net_disconnect(void)
{
	if (s_socket >= 0) {
		close(s_socket);
		s_socket = -1;
	}
	s_state = NET_IDLE;
	s_rx_used = 0;
	s_tx_head = 0;
	s_tx_count = 0;
}

NetState net_state(void)
{
	return s_state;
}

const char *net_last_error(void)
{
	return s_error;
}

bool net_connect(const char *host, int port)
{
	if (!s_soc_ready) {
		set_error("reseau non initialise");
		return false;
	}

	net_disconnect();

	s_socket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	if (s_socket < 0) {
		set_error_errno("socket");
		return false;
	}

	/*
	 * Mode non bloquant avant connect : sur la 3DS un connect bloquant vers un
	 * hôte absent gèle l'application le temps du timeout TCP.
	 */
	const int flags = fcntl(s_socket, F_GETFL, 0);
	if (flags < 0 || fcntl(s_socket, F_SETFL, flags | O_NONBLOCK) < 0) {
		set_error_errno("fcntl");
		net_disconnect();
		return false;
	}

	/* Les messages sont petits et la latence perçue compte plus que le débit. */
	const int one = 1;
	setsockopt(s_socket, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

	struct sockaddr_in addr;
	memset(&addr, 0, sizeof(addr));
	addr.sin_family = AF_INET;
	addr.sin_port = htons((u16)port);

	if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
		/*
		 * L'adresse n'est pas numérique : on tente une résolution DNS. Elle est
		 * bloquante, d'où la recommandation d'utiliser une IP littérale dans la
		 * configuration.
		 */
		struct hostent *entry = gethostbyname(host);
		if (entry == NULL || entry->h_addr_list[0] == NULL) {
			set_error("hote introuvable");
			net_disconnect();
			return false;
		}
		memcpy(&addr.sin_addr, entry->h_addr_list[0], sizeof(addr.sin_addr));
	}

	const int rc = connect(s_socket, (struct sockaddr *)&addr, sizeof(addr));
	if (rc == 0) {
		s_state = NET_CONNECTED;
		s_rx_used = 0;
		s_error[0] = '\0';
		return true;
	}

	if (errno == EINPROGRESS || errno == EALREADY || errno == EWOULDBLOCK) {
		s_state = NET_CONNECTING;
		s_rx_used = 0;
		return true;
	}

	set_error_errno("connect");
	net_disconnect();
	return false;
}

/** Vérifie l'aboutissement d'un connect non bloquant. */
static void poll_connecting(void)
{
	struct pollfd pfd;
	pfd.fd = s_socket;
	pfd.events = POLLOUT;
	pfd.revents = 0;

	const int rc = poll(&pfd, 1, 0);
	if (rc <= 0) {
		return; /* toujours en cours */
	}

	/*
	 * POLLOUT signale la fin de la phase de connexion : la socket est alors
	 * utilisable.
	 *
	 * On ne consulte volontairement pas SO_ERROR. Le service réseau de la 3DS y
	 * renvoie des valeurs qui ne sont pas des codes errno POSIX : on observe
	 * par exemple -26 sur une socket pourtant connectée, alors que les codes
	 * errno sont toujours positifs. S'y fier faisait fermer des liaisons
	 * valides et provoquait un cycle sans fin de connexion puis déconnexion
	 * immédiate.
	 *
	 * Si la connexion avait réellement échoué, le premier envoi ou la première
	 * réception le révélera, et la reconnexion automatique repartira d'un état
	 * propre. Mieux vaut cela que rejeter une connexion établie.
	 */
	if (pfd.revents & POLLOUT) {
		s_state = NET_CONNECTED;
		s_error[0] = '\0';
		return;
	}

	/*
	 * Sans POLLOUT, une erreur signalée correspond à un vrai refus : l'hôte est
	 * absent ou aucun agent n'écoute sur ce port.
	 */
	if (pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) {
		set_error("connexion refusee");
		net_disconnect();
	}
}

/** Lit ce qui est disponible sans bloquer. */
static void poll_reading(void)
{
	for (;;) {
		if (s_rx_used >= sizeof(s_rx)) {
			/*
			 * Le tampon est plein alors qu'aucun message complet n'a pu être
			 * extrait : le pair ne respecte pas le protocole.
			 */
			set_error("tampon sature");
			net_disconnect();
			return;
		}

		const ssize_t got = recv(s_socket, s_rx + s_rx_used,
		                         sizeof(s_rx) - s_rx_used, 0);

		if (got > 0) {
			s_rx_used += (size_t)got;
			continue; /* il peut rester des données */
		}

		if (got == 0) {
			set_error("connexion fermee par le PC");
			net_disconnect();
			return;
		}

		if (errno == EWOULDBLOCK || errno == EAGAIN) {
			return; /* plus rien pour l'instant */
		}
		if (errno == EINTR) {
			continue;
		}

		set_error_errno("recv");
		net_disconnect();
		return;
	}
}

/** Vide autant que possible la file d'émission, sans jamais attendre. */
static void poll_writing(void)
{
	while (s_state == NET_CONNECTED && s_tx_count > 0) {
		TxFrame *frame = &s_tx[s_tx_head];
		const ssize_t sent = send(s_socket, frame->data + frame->offset,
		                          frame->length - frame->offset, 0);

		if (sent > 0) {
			frame->offset += (size_t)sent;
			if (frame->offset >= frame->length) {
				memset(frame, 0, sizeof(*frame));
				s_tx_head = (s_tx_head + 1) % NET_TX_QUEUE_SIZE;
				s_tx_count--;
			}
			continue;
		}

		if (sent < 0 && (errno == EWOULDBLOCK || errno == EAGAIN)) {
			return;
		}
		if (sent < 0 && errno == EINTR) {
			continue;
		}

		set_error_errno("send");
		net_disconnect();
		return;
	}
}

void net_poll(void)
{
	if (s_socket < 0) {
		return;
	}

	if (s_state == NET_CONNECTING) {
		poll_connecting();
		return;
	}

	if (s_state == NET_CONNECTED) {
		poll_writing();
		if (s_state != NET_CONNECTED) {
			return;
		}
		poll_reading();
	}
}

bool net_receive(char *out, size_t out_size, size_t *out_length)
{
	if (out_length != NULL) {
		*out_length = 0;
	}
	if (out == NULL || out_size == 0) {
		return false;
	}
	if (s_rx_used < 4) {
		return false;
	}

	const unsigned char *header = (const unsigned char *)s_rx;
	const size_t length = ((size_t)header[0] << 24) | ((size_t)header[1] << 16) |
	                      ((size_t)header[2] << 8) | (size_t)header[3];

	if (length > NET_MAX_MESSAGE) {
		set_error("message trop grand");
		net_disconnect();
		return false;
	}

	if (s_rx_used < 4 + length) {
		return false; /* cadre incomplet */
	}

	/*
	 * On copie au plus out_size - 1 octets et on termine toujours par zéro.
	 * Le message est consommé même s'il ne tient pas, pour ne pas bloquer le
	 * flux sur un message anormalement grand.
	 */
	const size_t copy = (length < out_size - 1) ? length : out_size - 1;
	memcpy(out, s_rx + 4, copy);
	out[copy] = '\0';

	const size_t consumed = 4 + length;
	const size_t remaining = s_rx_used - consumed;
	if (remaining > 0) {
		memmove(s_rx, s_rx + consumed, remaining);
	}
	s_rx_used = remaining;

	if (out_length != NULL) {
		*out_length = copy;
	}
	return true;
}

bool net_send(const char *payload, size_t length)
{
	if (s_state != NET_CONNECTED || s_socket < 0) {
		return false;
	}
	if (payload == NULL || length == 0 || length > NET_MAX_OUTBOUND) {
		return false;
	}
	if (s_tx_count >= NET_TX_QUEUE_SIZE) {
		set_error("file d'envoi pleine");
		return false;
	}

	const int tail = (s_tx_head + s_tx_count) % NET_TX_QUEUE_SIZE;
	TxFrame *frame = &s_tx[tail];
	memset(frame, 0, sizeof(*frame));
	frame->data[0] = (unsigned char)((length >> 24) & 0xFF);
	frame->data[1] = (unsigned char)((length >> 16) & 0xFF);
	frame->data[2] = (unsigned char)((length >> 8) & 0xFF);
	frame->data[3] = (unsigned char)(length & 0xFF);
	memcpy(frame->data + 4, payload, length);
	frame->length = length + 4;
	s_tx_count++;

	/* Tente immédiatement une écriture, puis laisse `net_poll` poursuivre. */
	poll_writing();
	return s_state == NET_CONNECTED;
}

bool net_send_text(const char *payload)
{
	if (payload == NULL) {
		return false;
	}
	return net_send(payload, strlen(payload));
}
