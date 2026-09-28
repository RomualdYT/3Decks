/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file top_visuals.h Animation persistante de l'ecran superieur. */
#pragma once

#include "app.h"

/** Place les sentinelles et valeurs initiales apres l'effacement de `App`. */
void top_visuals_init(TopVisualState *visual);

/** Met a jour transitions, progression locale et enveloppes audio. */
void top_visuals_update(App *app, float dt);
