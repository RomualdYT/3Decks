/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file icons.h
 * @brief Icônes dessinées en primitives citro2d.
 *
 * Aucun fichier graphique n'est nécessaire : les icônes sont vectorielles, donc
 * nettes à n'importe quelle taille et modifiables sans pipeline d'assets.
 */
#pragma once

#include "model.h"

/**
 * Dessine une icône centrée sur (`cx`, `cy`), inscrite dans un carré de côté
 * `size`, avec la couleur `color`.
 */
void icons_draw(IconId icon, float cx, float cy, float size, float depth,
                u32 color);
