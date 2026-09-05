/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "setup.h"

#include <3ds.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "draw.h"
#include "discovery.h"
#include "i18n.h"
#include "icons.h"
#include "net.h"
#include "sound.h"
#include "text.h"
#include "theme.h"

#include "setup_internal.h"

static void draw_primary_button(const char *label, u32 accent)
{
	float x;
	float y;
	float w;
	float h;
	primary_button_bounds(&x, &y, &w, &h);

	draw_shadow(x, y, w, h, 10.0f, Z_BG);
	draw_round_rect_vgrad(x, y, w, h, 10.0f, Z_CARD,
	                      theme_mix(COL_SURFACE_HI, accent, 0.55f),
	                      theme_mix(COL_SURFACE_LO, accent, 0.30f));
	draw_round_rect_outline(x, y, w, h, 10.0f, 1.4f, Z_CONTENT,
	                        theme_alpha(accent, 0xDD));
	text_draw(x + w * 0.5f, y + (h - TEXT_LINE_PX(TEXT_BODY)) * 0.5f, Z_OVERLAY,
	          TEXT_BODY, COL_WHITE, ALIGN_CENTER, label);
}

/** Ligne de réglage : intitulé à gauche, valeur à droite. */
static void draw_row(int index, const char *label, const char *value,
                     bool highlight)
{
	float y;
	float h;
	row_bounds(index, &y, &h);

	draw_round_rect(14.0f, y, SCREEN_BOTTOM_W - 28.0f, h, 8.0f, Z_CARD,
	                highlight ? theme_alpha(COL_ACCENT, 0x28)
	                          : theme_alpha(COL_SURFACE, 0xBB));

	if (highlight) {
		draw_round_rect_outline(14.0f, y, SCREEN_BOTTOM_W - 28.0f, h, 8.0f, 1.0f,
		                        Z_CONTENT, theme_alpha(COL_ACCENT, 0x88));
	}

	const float text_y = y + (h - TEXT_LINE_PX(TEXT_SMALL)) * 0.5f;

	text_draw_clipped(26.0f, text_y, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM,
	                  ALIGN_LEFT, 150.0f, label);
	text_draw_clipped(SCREEN_BOTTOM_W - 26.0f, text_y, Z_CONTENT, TEXT_SMALL,
	                  highlight ? COL_ACCENT : COL_TEXT, ALIGN_RIGHT, 130.0f,
	                  value);
}

/** Choix de la langue, sous forme de grandes cartes. */
static void draw_language_choice(void)
{
	text_draw(SCREEN_BOTTOM_W * 0.5f, 14.0f, Z_CONTENT, TEXT_SMALL,
	          COL_TEXT_DIM, ALIGN_CENTER, tr(STR_CHOOSE_LANGUAGE));

	for (int i = 0; i < LANG_COUNT; i++) {
		const float y = ROWS_TOP + 10.0f + (float)i * LANG_CARD_PITCH;
		const bool current = (Language)i == i18n_language();

		draw_shadow(24.0f, y, SCREEN_BOTTOM_W - 48.0f, LANG_CARD_H, 10.0f, Z_BG);
		draw_round_rect_vgrad(24.0f, y, SCREEN_BOTTOM_W - 48.0f, LANG_CARD_H, 10.0f,
		                      Z_CARD,
		                      current ? theme_mix(COL_SURFACE_HI, COL_ACCENT,
		                                          0.45f)
		                              : COL_SURFACE_HI,
		                      current ? theme_mix(COL_SURFACE_LO, COL_ACCENT,
		                                          0.25f)
		                              : COL_SURFACE_LO);
		draw_round_rect_outline(24.0f, y, SCREEN_BOTTOM_W - 48.0f, LANG_CARD_H,
		                        10.0f, current ? 1.6f : 1.0f, Z_CONTENT,
		                        current ? theme_alpha(COL_ACCENT, 0xDD)
		                                : theme_alpha(COL_BORDER, 0xAA));

		text_draw(SCREEN_BOTTOM_W * 0.5f,
		          y + (LANG_CARD_H - TEXT_LINE_PX(TEXT_LARGE)) * 0.5f, Z_OVERLAY,
		          TEXT_LARGE, current ? COL_WHITE : COL_TEXT, ALIGN_CENTER,
		          i18n_language_name((Language)i));

		if (current) {
			draw_circle(SCREEN_BOTTOM_W - 44.0f, y + LANG_CARD_H * 0.5f, 4.0f,
			            Z_OVERLAY, COL_WHITE);
		}
	}
}

static void draw_discovered_agents(const Setup *setup)
{
	text_draw(SCREEN_BOTTOM_W * 0.5f, 12.0f, Z_CONTENT, TEXT_SMALL,
	          COL_TEXT_DIM, ALIGN_CENTER,
	          discovery_count() > 0 ? tr(STR_SETUP_AGENTS_FOUND)
	                                : tr(STR_SETUP_SEARCHING));

	const int visible = discovery_count() < AGENT_VISIBLE ? discovery_count()
	                                                        : AGENT_VISIBLE;
	const int first = first_visible_agent(setup);
	for (int row = 0; row < visible; row++) {
		const int index = first + row;
		const DiscoveredAgent *agent = discovery_at(index);
		if (agent == NULL) {
			continue;
		}
		float y;
		agent_card_bounds(row, &y);
		const bool selected = setup->selected_agent == index;
		draw_round_rect(14.0f, y, SCREEN_BOTTOM_W - 28.0f, AGENT_CARD_H, 9.0f,
		                Z_CARD,
		                selected ? theme_alpha(COL_ACCENT, 0x24)
		                         : theme_alpha(COL_SURFACE, 0xCC));
		draw_round_rect_outline(
		    14.0f, y, SCREEN_BOTTOM_W - 28.0f, AGENT_CARD_H, 9.0f,
		    selected ? 1.4f : 1.0f, Z_CONTENT,
		    selected ? theme_alpha(COL_ACCENT, 0xCC)
		             : theme_alpha(COL_BORDER, 0x88));
		icons_draw(ICON_APP, 33.0f, y + AGENT_CARD_H * 0.5f, 16.0f, Z_OVERLAY,
		           selected ? COL_ACCENT : COL_TEXT_DIM);
		text_draw_clipped(49.0f, y + 3.0f, Z_OVERLAY, TEXT_SMALL,
		                  selected ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT, 188.0f,
		                  agent->announcement.name);
		text_draw_clipped(49.0f, y + 18.0f, Z_OVERLAY, TEXT_MICRO,
		                  COL_TEXT_FAINT, ALIGN_LEFT, 188.0f,
		                  agent->announcement.platform);
		if (agent->announcement.pairing_required) {
			icons_draw(ICON_LOCK, SCREEN_BOTTOM_W - 33.0f,
			           y + AGENT_CARD_H * 0.5f, 14.0f, Z_OVERLAY,
			           selected ? COL_ACCENT : COL_TEXT_FAINT);
		}
	}

	const bool manual_selected = setup->selected_agent == -2;
	draw_round_rect(14.0f, MANUAL_CARD_Y, SCREEN_BOTTOM_W - 28.0f, 28.0f, 9.0f,
	                Z_CARD,
	                manual_selected ? theme_alpha(COL_ACCENT, 0x20)
	                                : theme_alpha(COL_SURFACE, 0x88));
	draw_round_rect_outline(
	    14.0f, MANUAL_CARD_Y, SCREEN_BOTTOM_W - 28.0f, 28.0f, 9.0f, 1.0f,
	    Z_CONTENT, manual_selected ? theme_alpha(COL_ACCENT, 0xAA)
	                              : theme_alpha(COL_BORDER, 0x77));
	icons_draw(ICON_GEAR, 34.0f, MANUAL_CARD_Y + 14.0f, 14.0f, Z_OVERLAY,
	           manual_selected ? COL_ACCENT : COL_TEXT_FAINT);
	text_draw(51.0f, MANUAL_CARD_Y + 6.0f, Z_OVERLAY, TEXT_SMALL,
	          manual_selected ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT,
	          tr(STR_SETUP_MANUAL));

	const char *primary =
	    setup->probe == PROBE_SUCCESS
	        ? tr(STR_NEXT)
	        : (setup->selected_agent >= 0
	               ? tr(STR_SETUP_CONNECT)
	               : (setup->selected_agent == -2 ? tr(STR_SETUP_MANUAL)
	                                                : tr(STR_SETUP_SEARCH_AGAIN)));
	draw_primary_button(primary,
	                    setup->probe == PROBE_SUCCESS
	                        ? COL_OK
	                        : (setup->selected_agent != -1 ? COL_ACCENT
	                                                       : COL_TEXT_DIM));
}

void setup_draw_bottom(const Setup *setup, const App *app)
{
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_BG, COL_BG_ALT,
	                COL_BG);

	if (setup->step == SETUP_LANGUAGE) {
		draw_language_choice();
		draw_primary_button(tr(STR_NEXT), COL_ACCENT);
		return;
	}

	if (setup->step == SETUP_HOST) {
		if (!setup->manual_connection) {
			draw_discovered_agents(setup);
			return;
		}

		text_draw(SCREEN_BOTTOM_W * 0.5f, 14.0f, Z_CONTENT, TEXT_SMALL,
		          COL_TEXT_DIM, ALIGN_CENTER, tr(STR_SETUP_MANUAL));

		char port[16];
		snprintf(port, sizeof(port), "%d", app->settings.port);

		draw_row(0, tr(STR_SETTINGS_HOST), app->settings.host,
		         setup->selection == 0);
		draw_row(1, tr(STR_SETTINGS_PORT), port, setup->selection == 1);
		draw_row(2, tr(STR_SETUP_AUTOMATIC), "", setup->selection == 2);

		draw_primary_button(setup->probe == PROBE_SUCCESS ? tr(STR_NEXT)
		                                                  : tr(STR_SETUP_TEST),
		                    setup->probe == PROBE_SUCCESS ? COL_OK : COL_ACCENT);
		return;
	}

	/* Écran de réglages. */
	text_draw(SCREEN_BOTTOM_W * 0.5f, 14.0f, Z_CONTENT, TEXT_SMALL,
	          COL_TEXT_DIM, ALIGN_CENTER, tr(STR_SETTINGS));

	char dim[24];
	if (app->settings.dim_delay <= 0) {
		snprintf(dim, sizeof(dim), "%s", tr(STR_NEVER));
	} else {
		snprintf(dim, sizeof(dim), "%d %s", app->settings.dim_delay,
		         tr(STR_SECONDS));
	}

	draw_row(ROW_LANGUAGE, tr(STR_SETTINGS_LANGUAGE),
	         i18n_language_name(i18n_language()),
	         setup->selection == ROW_LANGUAGE);
	draw_row(ROW_CONNECTION, tr(STR_SETTINGS_COMPUTER),
	         app->settings.agent_name[0] != '\0' ? app->settings.agent_name
	                                                : app->settings.host,
	         setup->selection == ROW_CONNECTION);
	draw_row(ROW_SOUND, tr(STR_SETTINGS_SOUND),
	         app->settings.sound ? tr(STR_ON) : tr(STR_OFF),
	         setup->selection == ROW_SOUND);
	draw_row(ROW_DIM, tr(STR_SETTINGS_DIM), dim, setup->selection == ROW_DIM);
	draw_row(ROW_STEREO, tr(STR_SETTINGS_STEREO),
	         app->settings.stereo ? tr(STR_ON) : tr(STR_OFF),
	         setup->selection == ROW_STEREO);
	draw_row(ROW_RESET, tr(STR_SETTINGS_RESET_SETUP), "",
	         setup->selection == ROW_RESET);

	draw_primary_button(tr(STR_SETTINGS_SAVE), COL_OK);
}

/* --- Interaction ---------------------------------------------------------- */

/** Fait avancer l'assistant à l'étape suivante. */
