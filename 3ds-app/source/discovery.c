/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "discovery.h"

#include <3ds.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define DISCOVERY_PORT 38122
#define DISCOVERY_MULTICAST "239.255.77.83"
#define DISCOVERY_DURATION 3.6f
#define DISCOVERY_REPEAT 0.8f
#define DISCOVERY_BUFFER 512

static int s_socket = -1;
static float s_elapsed = 0.0f;
static float s_send_in = 0.0f;
static bool s_scanning = false;
static int s_nonce = 0;
static struct in_addr s_directed_broadcast;
static bool s_has_directed_broadcast = false;
static struct in_addr s_known_host;
static bool s_has_known_host = false;
static DiscoveredAgent s_agents[DISCOVERY_MAX_AGENTS];
static int s_count = 0;

/**
 * Lit la diffusion de l'interface Wi-Fi réellement utilisée.
 *
 * Certains points d'accès filtrent 255.255.255.255 mais acceptent la diffusion
 * dirigée (par exemple 192.168.1.255). La pile réseau de la 3DS fournit
 * directement l'adresse calculée avec le masque DHCP : aucun préfixe /24 ni
 * aucune adresse propre à un utilisateur ne sont supposés.
 */
static void detect_directed_broadcast(void)
{
	s_has_directed_broadcast = false;

	struct in_addr address;
	struct in_addr netmask;
	if (SOCU_GetIPInfo(&address, &netmask, &s_directed_broadcast) == 0 &&
	    address.s_addr != htonl(INADDR_ANY) &&
	    netmask.s_addr != htonl(INADDR_ANY)) {
		s_has_directed_broadcast = true;
	}
}

static void send_probe_to(const char *payload, size_t length,
                          struct in_addr address)
{
	struct sockaddr_in target;
	memset(&target, 0, sizeof(target));
	target.sin_family = AF_INET;
	target.sin_port = htons(DISCOVERY_PORT);
	target.sin_addr = address;
	(void)sendto(s_socket, payload, length, 0, (struct sockaddr *)&target,
	             sizeof(target));
}

static void send_probe(void)
{
	if (s_socket < 0) {
		return;
	}

	char payload[96];
	s_nonce++;
	const int written = snprintf(
	    payload, sizeof(payload),
	    "{\"type\":\"deck3ds.discover\",\"protocol\":%d,\"nonce\":%d}",
	    PROTOCOL_VERSION, s_nonce);
	if (written <= 0 || (size_t)written >= sizeof(payload)) {
		return;
	}

	struct in_addr limited;
	limited.s_addr = htonl(INADDR_BROADCAST);
	send_probe_to(payload, (size_t)written, limited);

	if (s_has_directed_broadcast &&
	    s_directed_broadcast.s_addr != limited.s_addr) {
		send_probe_to(payload, (size_t)written, s_directed_broadcast);
	}

	/* Le multicast passe sur les réseaux Wi-Fi qui filtrent les broadcasts. */
	struct in_addr multicast;
	if (inet_aton(DISCOVERY_MULTICAST, &multicast) != 0) {
		send_probe_to(payload, (size_t)written, multicast);
	}
	if (s_has_known_host && s_known_host.s_addr != limited.s_addr &&
	    (!s_has_directed_broadcast ||
	     s_known_host.s_addr != s_directed_broadcast.s_addr)) {
		send_probe_to(payload, (size_t)written, s_known_host);
	}
}

void discovery_set_known_host(const char *host)
{
	s_has_known_host =
	    host != NULL && host[0] != '\0' && inet_aton(host, &s_known_host) != 0 &&
	    s_known_host.s_addr != htonl(INADDR_ANY) &&
	    s_known_host.s_addr != htonl(INADDR_BROADCAST);
}

bool discovery_start(void)
{
	discovery_stop();
	memset(s_agents, 0, sizeof(s_agents));
	s_count = 0;
	s_elapsed = 0.0f;
	s_send_in = 0.0f;

	s_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
	if (s_socket < 0) {
		return false;
	}

	const int flags = fcntl(s_socket, F_GETFL, 0);
	if (flags < 0 || fcntl(s_socket, F_SETFL, flags | O_NONBLOCK) < 0) {
		discovery_stop();
		return false;
	}

	const int enabled = 1;
	/*
	 * Certains firmwares refusent SO_BROADCAST. Ce n'est pas fatal : le
	 * multicast et la sonde unicast de l'ordinateur déjà connu restent valides.
	 */
	(void)setsockopt(s_socket, SOL_SOCKET, SO_BROADCAST, &enabled,
	                 sizeof(enabled));
	const int multicast_ttl = 1;
	(void)setsockopt(s_socket, IPPROTO_IP, IP_MULTICAST_TTL, &multicast_ttl,
	                 sizeof(multicast_ttl));
	detect_directed_broadcast();

	s_scanning = true;
	send_probe();
	s_send_in = DISCOVERY_REPEAT;
	return true;
}

static void remember_agent_at(const AgentAnnouncement *announcement,
                              const char *host)
{
	if (host == NULL || host[0] == '\0') {
		return;
	}

	for (int i = 0; i < s_count; i++) {
		if (strcmp(s_agents[i].host, host) == 0 &&
		    s_agents[i].announcement.port == announcement->port) {
			s_agents[i].announcement = *announcement;
			return;
		}
	}

	if (s_count >= DISCOVERY_MAX_AGENTS) {
		return;
	}

	s_agents[s_count].announcement = *announcement;
	snprintf(s_agents[s_count].host, sizeof(s_agents[s_count].host), "%s",
	         host);
	s_count++;
}

static void remember_agent(const AgentAnnouncement *announcement,
                           const struct sockaddr_in *source)
{
	const char *address = inet_ntoa(source->sin_addr);
	remember_agent_at(announcement, address);
}

void discovery_remember_known(const char *host, const char *name, int port,
                              bool pairing_required)
{
	if (host == NULL || host[0] == '\0' || port <= 0 || port > 65535) {
		return;
	}

	AgentAnnouncement announcement;
	memset(&announcement, 0, sizeof(announcement));
	snprintf(announcement.name, sizeof(announcement.name), "%s",
	         name != NULL && name[0] != '\0' ? name : host);
	snprintf(announcement.platform, sizeof(announcement.platform), "%s",
	         "3Decks");
	announcement.port = port;
	announcement.pairing_required = pairing_required;
	remember_agent_at(&announcement, host);
}

static void receive_available(void)
{
	for (;;) {
		char payload[DISCOVERY_BUFFER + 1];
		struct sockaddr_in source;
		socklen_t source_size = sizeof(source);
		const ssize_t length = recvfrom(
		    s_socket, payload, DISCOVERY_BUFFER, 0, (struct sockaddr *)&source,
		    &source_size);

		if (length < 0 && (errno == EWOULDBLOCK || errno == EAGAIN)) {
			return;
		}
		if (length < 0 && errno == EINTR) {
			continue;
		}
		if (length <= 0) {
			return;
		}

		payload[length] = '\0';
		AgentAnnouncement announcement;
		if (protocol_decode_discovery(payload, (size_t)length, &announcement)) {
			remember_agent(&announcement, &source);
		}
	}
}

void discovery_update(float dt)
{
	if (s_socket < 0) {
		return;
	}
	receive_available();

	if (!s_scanning) {
		return;
	}
	s_elapsed += dt;
	s_send_in -= dt;
	if (s_send_in <= 0.0f && s_elapsed < DISCOVERY_DURATION) {
		send_probe();
		s_send_in = DISCOVERY_REPEAT;
	}
	if (s_elapsed >= DISCOVERY_DURATION) {
		s_scanning = false;
	}
}

void discovery_stop(void)
{
	if (s_socket >= 0) {
		close(s_socket);
		s_socket = -1;
	}
	s_scanning = false;
}

bool discovery_scanning(void)
{
	return s_scanning;
}

int discovery_count(void)
{
	return s_count;
}

const DiscoveredAgent *discovery_at(int index)
{
	if (index < 0 || index >= s_count) {
		return NULL;
	}
	return &s_agents[index];
}
