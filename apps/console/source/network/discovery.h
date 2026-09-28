/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file discovery.h
 * @brief Recherche non bloquante des agents Deck3DS sur le réseau local.
 */
#pragma once

#include <stdbool.h>

#include "protocol.h"

#define DISCOVERY_MAX_AGENTS 4

typedef struct {
	AgentAnnouncement announcement;
	char host[64];
} DiscoveredAgent;

/** Démarre une nouvelle recherche et efface les anciens résultats. */
bool discovery_start(void);

/** Adresse connue à sonder aussi en unicast, vide pour la désactiver. */
void discovery_set_known_host(const char *host);

/** Ajoute l'ordinateur déjà connecté comme résultat de secours. */
void discovery_remember_known(const char *host, const char *name, int port,
                              bool pairing_required);

/** Fait progresser la recherche sans bloquer la boucle de rendu. */
void discovery_update(float dt);

/** Ferme la socket de découverte. */
void discovery_stop(void);

/** Vrai pendant la fenêtre active d'annonce. */
bool discovery_scanning(void);

/** Nombre d'agents actuellement connus. */
int discovery_count(void);

/** Agent d'index donné, ou NULL. */
const DiscoveredAgent *discovery_at(int index);
