/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_network.h Orchestration non bloquante de la liaison agent. */
#pragma once

#include "app.h"

/** Fait progresser le delai et demarre une reconnexion lorsque necessaire. */
void app_network_update(App *app);
