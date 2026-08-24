/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file artwork.h
 * @brief Réception et affichage de la pochette d'album.
 *
 * L'agent transmet une image déjà convertie au format du processeur graphique
 * de la console : RGB565 réorganisé en tuiles. Le bloc reçu est donc téléversé
 * tel quel, sans aucune conversion sur la console.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>

#include <3ds.h>
#include <citro2d.h>

/** Côté de la pochette, en pixels. Doit correspondre à l'agent. */
#define ART_SIZE 128

/** Taille de la charge utile attendue : signature, en-tête et pixels. */
#define ART_PAYLOAD_SIZE (12 + ART_SIZE * ART_SIZE * 2)

/** Prépare la texture. À appeler après `C3D_Init`. */
bool artwork_init(void);

/** Libère la texture. */
void artwork_exit(void);

/**
 * Traite une charge utile reçue du réseau.
 *
 * Retourne `true` si la charge était bien une pochette, qu'elle ait été
 * acceptée ou rejetée. L'appelant sait ainsi qu'il ne doit pas tenter de
 * l'analyser comme du JSON.
 */
bool artwork_consume(const char *payload, size_t length);

/** Indique si une pochette est disponible à l'affichage. */
bool artwork_available(void);

/** Jeton de la pochette détenue, 0 si aucune. */
u32 artwork_token(void);

/**
 * Dessine la pochette dans un carré de côté `size`.
 * Ne fait rien si aucune image n'est disponible.
 */
void artwork_draw(float x, float y, float size, float depth, u8 alpha);
