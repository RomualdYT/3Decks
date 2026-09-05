/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "draw.h"
#include "i18n.h"
#include "icons.h"
#include "text.h"
#include "theme.h"
#include "ui.h"
#include "extension_ui.h"

#include "ui_bottom_internal.h"

/** Retour compact d'une action, sans recouvrir son libellé. */
void draw_action_feedback(ActionFeedbackState state, float cx, float cy,
                                 float uptime)
{
	if (state == ACTION_FEEDBACK_NONE) {
		return;
	}

	draw_circle(cx, cy, 7.5f, Z_OVERLAY, theme_alpha(COL_BG, 0xE8));

	if (state == ACTION_FEEDBACK_PENDING) {
		draw_ring(cx, cy, 5.4f, 1.2f, Z_OVERLAY,
		          theme_alpha(COL_ACCENT, 0x42));
		draw_arc(cx, cy, 5.4f, 1.8f, fmodf(uptime * 1.4f, 1.0f), 0.30f,
		         Z_OVERLAY, COL_ACCENT);
		return;
	}

	const u32 fill =
	    state == ACTION_FEEDBACK_SUCCESS ? COL_OK : COL_ERR;
	draw_circle(cx, cy, 5.7f, Z_OVERLAY, fill);

	if (state == ACTION_FEEDBACK_SUCCESS) {
		draw_line(cx - 3.0f, cy, cx - 0.8f, cy + 2.3f, 1.4f,
		          Z_OVERLAY, COL_BG);
		draw_line(cx - 0.8f, cy + 2.3f, cx + 3.4f, cy - 2.7f, 1.4f,
		          Z_OVERLAY, COL_BG);
	} else {
		draw_line(cx - 2.4f, cy - 2.4f, cx + 2.4f, cy + 2.4f, 1.4f,
		          Z_OVERLAY, COL_WHITE);
		draw_line(cx - 2.4f, cy + 2.4f, cx + 2.4f, cy - 2.4f, 1.4f,
		          Z_OVERLAY, COL_WHITE);
	}
}
