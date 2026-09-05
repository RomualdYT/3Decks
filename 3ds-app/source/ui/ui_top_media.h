/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file ui_top_media.h Rendus audio et media de l'ecran superieur. */
#pragma once

#include "app.h"

/** Vue pochette sous le bandeau heure/date. Elle dessine son propre fond. */
void ui_top_media_draw(const App *app);

/** Vue des sorties audio, egaliseur et dock de volumes. */
void ui_top_audio_draw(const App *app);

/** Mode cadre sans bandeau, utilise notamment pendant la veille. */
void ui_top_frame_draw(const App *app);
