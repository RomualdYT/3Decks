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

/* Returns the left edge reserved for navigation, or the right margin. */
static float draw_page_indicator(const App *app, u32 accent)
{
	int count = app->config.page_count;
	const float right = SCREEN_BOTTOM_W - GRID_MARGIN_X;
	if (count <= 1) return right;
	if (count > MAX_PAGES) count = MAX_PAGES;
	int current = app->current_page;
	if (current < 0 || current >= count) current = 0;

	const float dot = 4.0f, active = 10.0f, gap = 4.0f;
	const float width = (count - 1) * (dot + gap) + active;
	const float left = right - width;
	float x = left;
	for (int i = 0; i < count; ++i) {
		const float w = i == current ? active : dot;
		draw_round_rect(x, 15.0f, w, dot, 2.0f, Z_CONTENT,
		                i == current ? accent : COL_TEXT_FAINT);
		x += w + gap;
	}
	return left;
}

static void draw_title_bar(const App *app)
{
	const Page *page = app_current_page(app);


	const float indicator_left = draw_page_indicator(
	    app, page != NULL && page->accent_custom ? page->accent : COL_ACCENT);
	const float title_x = GRID_MARGIN_X;
	const char *title = (page != NULL) ? page->title : "3Decks";
	text_draw_clipped(title_x, 8.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT,
	                  ALIGN_LEFT, indicator_left - title_x - 10.0f, title);

	draw_rect(GRID_MARGIN_X, GRID_TOP - 7.0f,
	          SCREEN_BOTTOM_W - GRID_MARGIN_X * 2.0f, 1.0f,
	          Z_CONTENT, theme_alpha(COL_BORDER, 0x88));
	if (page != NULL && page->dashboard == DASH_LYRICS &&
	    app->state.media_seekable && app->state.media_duration > 0) {
		const float width = SCREEN_BOTTOM_W - GRID_MARGIN_X * 2.0f;
		float progress = app->top_visual.media_position_display /
		                 (float)app->state.media_duration;
		if (progress < 0.0f) progress = 0.0f;
		if (progress > 1.0f) progress = 1.0f;
		draw_round_rect(GRID_MARGIN_X, 32.0f, width, 4.0f, 2.0f,
		                Z_CONTENT, COL_BORDER);
		draw_round_rect(GRID_MARGIN_X, 32.0f, width * progress, 4.0f, 2.0f,
		                Z_OVERLAY, page->accent_custom ? page->accent : COL_ACCENT);
	}
}

static void draw_tabs(const App *app)
{
	const int count = app->config.page_count;
	if (count <= 0) {
		return;
	}

	const Rect first = tab_rect(0, count, app->current_page);
	const Rect last = tab_rect(count - 1, count, app->current_page);
	draw_round_rect(first.x - 3.0f, first.y,
	                last.x + last.w - first.x + 6.0f, first.h,
	                10.0f, Z_CARD, COL_SURFACE_LO);

	for (int i = 0; i < count; i++) {
		const Rect rect = tab_rect(i, count, app->current_page);
		const bool current = (i == app->current_page);
		const Page *page = model_page_at(&app->config, i);

		const u32 page_accent = page != NULL && page->accent_custom
		                            ? page->accent : COL_ACCENT;
		if (current) {
			draw_round_rect(rect.x, rect.y, rect.w, rect.h, 8.0f, Z_CONTENT,
			                theme_mix(COL_BG, page_accent, 0.24f));
		}

		const char *label = (page != NULL) ? page->title : "";
		u32 fg = current ? theme_mix(page_accent, COL_WHITE, 0.35f) : COL_TEXT_FAINT;
		if (current) {
			float reveal = app->enter_anim * 0.32f / 0.18f;
			if (reveal > 1.0f) reveal = 1.0f;
			fg = theme_alpha(fg, (u8)(255.0f * (0.55f + 0.45f * reveal)));
		}

		/* Only the selected page uses a label; crowded decks keep icons only. */
		const IconId icon = (page != NULL) ? page->icon : ICON_PAGE;
		const float centre_y = rect.y + rect.h * 0.5f;

		if (current && rect.w >= 64.0f && label[0] != '\0') {
			icons_draw(icon, rect.x + 15.0f, centre_y, 15.0f, Z_OVERLAY, fg);
			text_draw_clipped(
			    rect.x + 26.0f,
			    rect.y + (rect.h - TEXT_LINE_PX(TEXT_MICRO)) * 0.5f, Z_OVERLAY,
			    TEXT_MICRO, fg, ALIGN_LEFT, rect.w - 32.0f, label);
		} else {
			/*
			 * L'icône s'adapte à la largeur disponible : avec le nombre maximal
			 * de pages, un onglet descend sous vingt pixels et une icône de
			 * taille fixe dépasserait de son cadre.
			 */
			float icon_size = 17.0f;
			if (rect.w < 24.0f) {
				icon_size = rect.w * 0.72f;
			}
			icons_draw(icon, rect.x + rect.w * 0.5f, centre_y, icon_size,
			           Z_OVERLAY, fg);
		}
	}

	/* Bouton des réglages, à place fixe pour rester toujours repérable. */
	const Rect settings = settings_rect();
	const float settings_radius = 6.0f;

	draw_round_rect(settings.x, settings.y, settings.w, settings.h,
	                settings_radius, Z_CARD, theme_alpha(COL_SURFACE, 0xBB));
	icons_draw(ICON_GEAR, settings.x + settings.w * 0.5f,
	           settings.y + settings.h * 0.5f, 16.0f, Z_OVERLAY, COL_TEXT_DIM);
}

/** Écran affiché tant qu'aucune configuration n'est disponible. */
void ui_draw_bottom(const App *app)
{
	/*
	 * En veille, l'écran tactile devient un panneau d'information : aucun
	 * bouton n'est actionnable puisque le moindre contact réveille
	 * l'application.
	 */
	if (app->frame_mode && app->frame_from_idle) {
		draw_standby(app);
		return;
	}

	const u32 top = app->dimmed ? C2D_Color32(0x06, 0x07, 0x0B, 0xFF) : COL_BG_ALT;
	const u32 bottom = app->dimmed ? C2D_Color32(0x03, 0x04, 0x07, 0xFF) : COL_BG;
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_BG, top, bottom);

	if (!app->config_received) {
		draw_waiting(app);
		return;
	}

	draw_title_bar(app);

	const Page *page = app_current_page(app);
	if (page != NULL) {
		if (page->layout == LAYOUT_LIST) {
			draw_list(app, page);
		} else {
			for (int slot = 0; slot < MAX_BUTTONS; slot++) {
				draw_button(app, &page->buttons[slot], slot);
			}
		}
	}

	draw_tabs(app);

	/*
	 * Voile d'assombrissement en veille. L'écran reste lisible mais cesse
	 * d'attirer l'attention, et l'usure de la dalle est limitée.
	 */
	if (app->dimmed) {
		draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_OVERLAY,
		          C2D_Color32(0x00, 0x00, 0x00, 0x66));
	}
}
