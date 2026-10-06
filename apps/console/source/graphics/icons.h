/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file icons.h
 * @brief Icônes dessinées en primitives citro2d.
 *
 * Les atlas Lucide reprennent les icônes de l'éditeur PC. Les primitives
 * vectorielles assurent le repli si les atlas sont absents.
 */
#pragma once

#include "model.h"

/** Charge les atlas après C2D_Init ; libère avant C2D_Fini. */
void icons_init(void);
void icons_exit(void);

/**
 * Dessine une icône centrée sur (`cx`, `cy`), inscrite dans un carré de côté
 * `size`, avec la couleur `color`.
 */
void icons_draw(IconId icon, float cx, float cy, float size, float depth,
                u32 color);
