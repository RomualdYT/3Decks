/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/** @file app_feedback.h Cycle de vie du retour visuel des actions. */
#pragma once

#include "app.h"

#define APP_HOLD_THRESHOLD 0.45f

void app_feedback_begin(App *app, int request_id, const char *page_id,
	                    const char *item_id);
void app_feedback_finish(App *app, int request_id, bool success);
void app_feedback_update(App *app, float dt);
