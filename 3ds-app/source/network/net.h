/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file net.h
 * @brief Transport TCP non bloquant avec framing par longueur.
 *
 * Contrainte de conception : aucune fonction ne doit bloquer la boucle de
 * rendu. La connexion elle-même est asynchrone (`connect` non bloquant puis
 * surveillance de l'écriture), sans quoi l'application semblerait figée
 * plusieurs secondes sur matériel réel quand le PC est absent.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>

/** Taille maximale d'un message, doit rester alignée sur PROTOCOL.md. */
#define NET_MAX_MESSAGE 65536

/** Les messages émis par la console sont volontairement compacts. */
#define NET_MAX_OUTBOUND 508

typedef enum {
	NET_IDLE = 0,      /**< Socket fermée, aucune tentative en cours. */
	NET_CONNECTING,    /**< `connect` en cours. */
	NET_CONNECTED,     /**< Prêt à échanger des messages. */
} NetState;

/** Initialise le service SOC. Retourne `false` si le réseau est indisponible. */
bool net_init(void);

/** Libère le service SOC. */
void net_exit(void);

/** Ouvre une connexion IPv4 numérique non bloquante (pas de DNS synchrone). */
bool net_connect(const char *host, int port);

/** Ferme la connexion courante s'il y en a une. */
void net_disconnect(void);

/** État courant du transport. */
NetState net_state(void);

/**
 * Fait progresser la connexion et la réception.
 * À appeler une fois par frame. Ne bloque jamais.
 */
void net_poll(void);

/**
 * Récupère le prochain message complet reçu.
 * Retourne `false` si aucun message n'est disponible.
 * `out` reçoit une chaîne terminée par zéro ; `out_length` la longueur utile.
 * Prévoir NET_MAX_MESSAGE + 1 octets. Une destination trop petite ferme
 * la liaison explicitement : aucune charge utile n'est tronquée.
 */
bool net_receive(char *out, size_t out_size, size_t *out_length);

/**
 * Place un message dans la file d'émission. Le framing est ajouté
 * automatiquement et `net_poll` l'envoie sans bloquer la boucle de rendu.
 * Retourne `false` si la connexion est absente ou la file pleine.
 */
bool net_send(const char *payload, size_t length);

/** Envoie une chaîne terminée par zéro. */
bool net_send_text(const char *payload);

/** Dernier message d'erreur lisible, chaîne vide si aucune erreur. */
const char *net_last_error(void);
