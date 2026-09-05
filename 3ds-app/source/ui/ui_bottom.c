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

static void draw_title_bar(const App *app)
{
	const Page *page = app_current_page(app);

	draw_rect_vgrad(0.0f, 0.0f, SCREEN_BOTTOM_W, GRID_TOP - 6.0f, Z_CARD,
	                theme_alpha(COL_SURFACE, 0xE6),
	                theme_alpha(COL_SURFACE_LO, 0xB0));

	/*
	 * Pastille de couleur devant le titre : reprend l'accent de la page
	 * courante et sert de repère visuel lors des changements de page.
	 */
	const u32 accent = (app->link == LINK_ONLINE) ? COL_ACCENT : COL_ERR;
	draw_round_rect(GRID_MARGIN_X, 11.0f, 3.0f, 13.0f, 1.5f, Z_CONTENT, accent);

	const char *title = (page != NULL) ? page->title : "Deck3DS";
	text_draw_clipped(GRID_MARGIN_X + 9.0f, 8.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT,
	                  ALIGN_LEFT, 190.0f, title);

	/* Compteur de pages, à droite. */
	if (app->config.page_count > 1) {
		/*
		 * Les valeurs sont bornées par MAX_PAGES, mais le compilateur ne peut
		 * pas le déduire : on les restreint explicitement pour garantir que le
		 * formatage ne soit jamais tronqué.
		 */
		const unsigned current =
		    (unsigned)(app->current_page + 1) % (MAX_PAGES + 1);
		const unsigned total = (unsigned)app->config.page_count % (MAX_PAGES + 1);

		char counter[16];
		snprintf(counter, sizeof(counter), "%u / %u", current, total);
		text_draw(SCREEN_BOTTOM_W - GRID_MARGIN_X, 12.0f, Z_CONTENT, TEXT_SMALL,
		          COL_TEXT_FAINT, ALIGN_RIGHT, counter);
	}

	/*
	 * Trait de séparation en dégradé : plus lumineux au centre, il structure
	 * l'écran sans le cloisonner brutalement.
	 */
	const float y = GRID_TOP - 7.0f;
	const u32 edge = theme_alpha(accent, 0x00);
	const u32 middle = theme_alpha(accent, 0x88);
	C2D_DrawRectangle(0.0f, y, Z_CONTENT, SCREEN_BOTTOM_W * 0.5f, 1.0f, edge,
	                  middle, edge, middle);
	C2D_DrawRectangle(SCREEN_BOTTOM_W * 0.5f, y, Z_CONTENT,
	                  SCREEN_BOTTOM_W * 0.5f, 1.0f, middle, edge, middle, edge);
}

static void draw_tabs(const App *app)
{
	const int count = app->config.page_count;
	if (count <= 0) {
		return;
	}

	for (int i = 0; i < count; i++) {
		const Rect rect = tab_rect(i, count);
		const bool current = (i == app->current_page);
		const Page *page = model_page_at(&app->config, i);

		const float radius = rect.h * 0.5f;

		if (current) {
			/*
			 * Onglet actif : fond plus dense et contour net, pour qu'il se
			 * distingue immédiatement des autres.
			 */
			draw_round_rect_vgrad(rect.x, rect.y, rect.w, rect.h, radius, Z_CARD,
			                      theme_alpha(COL_ACCENT, 0x4A),
			                      theme_alpha(COL_ACCENT, 0x22));
			draw_round_rect_outline(rect.x, rect.y, rect.w, rect.h, radius, 1.2f,
			                        Z_CONTENT, theme_alpha(COL_ACCENT, 0xBB));
		} else {
			draw_round_rect(rect.x, rect.y, rect.w, rect.h, radius, Z_CARD,
			                theme_alpha(COL_SURFACE, 0x99));
		}

		const char *label = (page != NULL) ? page->title : "";
		const u32 fg = current ? COL_WHITE : COL_TEXT_DIM;

		/*
		 * Une icône plutôt qu'un numéro.
		 *
		 * Au-delà de cinq pages, un onglet mesure moins de cinquante pixels :
		 * le titre n'y tient plus, et un numéro n'apprend rien sur le contenu
		 * de la page. Une icône reste lisible et reconnaissable à cette taille.
		 * Quand la place le permet, les deux sont affichés ensemble.
		 */
		const IconId icon = (page != NULL) ? page->icon : ICON_PAGE;
		const float centre_y = rect.y + rect.h * 0.5f;

		if (rect.w >= 74.0f && label[0] != '\0') {
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
	const float settings_radius = settings.h * 0.5f;

	draw_round_rect(settings.x, settings.y, settings.w, settings.h,
	                settings_radius, Z_CARD, theme_alpha(COL_SURFACE, 0xBB));
	draw_round_rect_outline(settings.x, settings.y, settings.w, settings.h,
	                        settings_radius, 1.0f, Z_CONTENT,
	                        theme_alpha(COL_BORDER, 0x99));
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
