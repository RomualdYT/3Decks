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

/** Dessine un élément de liste. */
void draw_list_item(const App *app, const ListEntry *entry, int index)
{
	const Rect rect = list_item_rect(index, app->list_scroll);

	/* Rien à faire si l'élément est hors de la zone visible. */
	if (rect.y + rect.h < GRID_TOP - 2.0f ||
	    rect.y > SCREEN_H - GRID_BOTTOM_BAR + 2.0f) {
		return;
	}

	const bool focused = (index == app->list_focus);
	const Page *page = app_current_page(app);
	const ActionFeedbackState feedback =
	    page != NULL ? app_action_feedback(app, page->id, entry->id)
	                 : ACTION_FEEDBACK_NONE;
	const float radius = 8.0f;

	/*
	 * L'élément actif est mis en évidence par son fond et un liseré coloré :
	 * on repère ainsi immédiatement la fenêtre au premier plan.
	 */
	u32 top;
	u32 bottom;
	if (entry->active) {
		top = theme_mix(COL_SURFACE_HI, entry->color, 0.38f);
		bottom = theme_mix(COL_SURFACE_LO, entry->color, 0.20f);
	} else if (focused) {
		top = COL_SURFACE_HI;
		bottom = COL_SURFACE;
	} else {
		top = COL_SURFACE;
		bottom = COL_SURFACE_LO;
	}
	if (feedback == ACTION_FEEDBACK_PENDING) {
		top = theme_mix(top, COL_ACCENT, 0.08f);
	} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
		top = theme_mix(top, COL_OK, 0.12f);
	} else if (feedback == ACTION_FEEDBACK_ERROR) {
		top = theme_mix(top, COL_ERR, 0.12f);
	}

	draw_round_rect_vgrad(rect.x, rect.y, rect.w, rect.h, radius, Z_CARD, top,
	                      bottom);

	if (entry->active || focused || feedback != ACTION_FEEDBACK_NONE) {
		u32 outline_color = theme_alpha(
		    entry->color, entry->active ? 0xDD : 0x77);
		float outline = entry->active ? 1.4f : 1.0f;
		if (feedback == ACTION_FEEDBACK_PENDING) {
			outline_color = theme_alpha(COL_ACCENT, 0xD0);
			outline = 1.4f;
		} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
			outline_color = COL_OK;
			outline = 1.6f;
		} else if (feedback == ACTION_FEEDBACK_ERROR) {
			outline_color = COL_ERR;
			outline = 1.6f;
		}
		draw_round_rect_outline(rect.x, rect.y, rect.w, rect.h, radius,
		                        outline, Z_CONTENT, outline_color);
	}

	/* Bandeau vertical coloré : repère discret, aligné à gauche. */
	if (entry->active) {
		draw_round_rect(rect.x + 3.0f, rect.y + 7.0f, 2.5f, rect.h - 14.0f,
		                1.25f, Z_CONTENT, entry->color);
	}

	const float icon_cx = rect.x + 19.0f;
	const float middle = rect.y + rect.h * 0.5f;

	icons_draw(entry->icon, icon_cx, middle, 17.0f, Z_OVERLAY,
	           entry->active ? COL_WHITE
	                         : theme_mix(entry->color, COL_WHITE, 0.35f));

	/* Deux lignes : l'application, puis le détail qui la précise. */
	const float text_x = rect.x + 32.0f;
	const float text_w = rect.w - 48.0f;

	const bool has_detail = entry->detail[0] != '\0';
	const float label_y =
	    has_detail ? rect.y + 6.0f
	               : middle - TEXT_LINE_PX(TEXT_SMALL) * 0.5f;

	text_draw_clipped(text_x, label_y, Z_OVERLAY, TEXT_SMALL,
	                  entry->active ? COL_WHITE : COL_TEXT, ALIGN_LEFT, text_w,
	                  entry->label);

	if (has_detail) {
		text_draw_clipped(text_x, rect.y + 21.0f, Z_OVERLAY, TEXT_MICRO,
		                  entry->active ? theme_alpha(COL_WHITE, 0xBB)
		                                : COL_TEXT_FAINT,
		                  ALIGN_LEFT, text_w, entry->detail);
	}

	draw_action_feedback(feedback, rect.x + rect.w - 14.0f, middle,
	                     app->uptime);
}

/** Barre de position, à droite, indiquant l'étendue du défilement. */
void draw_list_scrollbar(const App *app, int count)
{
	const int rows = list_total_rows(count);
	const int visible = list_visible_rows();

	if (rows <= visible) {
		return; /* tout est visible, la barre serait inutile */
	}

	const float track_x = SCREEN_BOTTOM_W - 5.0f;
	const float track_y = GRID_TOP + 2.0f;
	const float track_h = SCREEN_H - GRID_BOTTOM_BAR - GRID_TOP - 4.0f;

	draw_round_rect(track_x, track_y, 3.0f, track_h, 1.5f, Z_CARD,
	                theme_alpha(COL_SURFACE_HI, 0x99));

	const float ratio = (float)visible / (float)rows;
	const float thumb_h = track_h * ratio;
	const float max_scroll = (float)(rows - visible);
	const float progress =
	    (max_scroll > 0.0f) ? app->list_scroll / max_scroll : 0.0f;

	draw_round_rect(track_x, track_y + (track_h - thumb_h) * progress, 3.0f,
	                thumb_h, 1.5f, Z_CONTENT, theme_alpha(COL_ACCENT, 0xCC));
}

/** Dessine la page en mode liste. */
void draw_list(const App *app, const Page *page)
{
	for (int i = 0; i < page->entry_count; i++) {
		if (page->entries[i].used) {
			draw_list_item(app, &page->entries[i], i);
		}
	}

	draw_list_scrollbar(app, page->entry_count);

	if (page->entry_count == 0) {
		text_draw(SCREEN_BOTTOM_W * 0.5f, SCREEN_H * 0.45f, Z_CONTENT,
		          TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER, tr(STR_NO_APPS));
	}
}
