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
#include "community_qr.h"
#include "platform_label.h"
#include "ui_companion.h"

/* --- Rendu de l'écran supérieur ------------------------------------------- */

/** Fil d'Ariane des étapes, pour situer la progression. */
static void draw_steps(const Setup *setup)
{
	const StringId labels[SETUP_STEP_COUNT] = {
	    STR_SETUP_STEP_LANGUAGE,
	    STR_SETUP_STEP_HOST,
	    STR_SETUP_STEP_DONE,
	};

	const float total = SCREEN_TOP_W - 60.0f;
	const float gap = total / (float)SETUP_STEP_COUNT;
	const float y = 46.0f;

	for (int i = 0; i < SETUP_STEP_COUNT; i++) {
		const float cx = 30.0f + gap * ((float)i + 0.5f);
		const bool done = i < (int)setup->step;
		const bool current = i == (int)setup->step;

		/* Trait reliant les étapes. */
		if (i > 0) {
			const float previous = 30.0f + gap * ((float)i - 0.5f);
			draw_rect(previous + 12.0f, y - 1.0f, cx - previous - 24.0f, 2.0f,
			          Z_CARD,
			          done || current ? theme_alpha(COL_ACCENT, 0x88)
			                          : theme_alpha(COL_BORDER, 0x88));
		}

		const u32 colour = (done || current) ? COL_ACCENT : COL_TEXT_FAINT;

		draw_circle(cx, y, 11.0f, Z_CARD,
		            current ? theme_alpha(COL_ACCENT, 0x44)
		                    : theme_alpha(COL_SURFACE_HI, 0xCC));
		draw_ring(cx, y, 11.0f, 1.5f, Z_CONTENT, theme_alpha(colour, 0xDD));

		char number[4];
		snprintf(number, sizeof(number), "%d", i + 1);
		text_draw(cx, y - TEXT_LINE_PX(TEXT_SMALL) * 0.5f, Z_OVERLAY, TEXT_SMALL,
		          colour, ALIGN_CENTER, number);

		text_draw(cx, y + 16.0f, Z_CONTENT, TEXT_MICRO,
		          current ? COL_TEXT : COL_TEXT_FAINT, ALIGN_CENTER,
		          tr(labels[i]));
	}
}

static void draw_language_step(const Setup *setup)
{
	(void)setup;
	const float cx = SCREEN_TOP_W * 0.5f;

	text_draw(cx, 96.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER,
	          tr(STR_CHOOSE_LANGUAGE));
	text_draw(cx, 128.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM, ALIGN_CENTER,
	          tr(STR_WELCOME_SUBTITLE));

}

static void draw_host_step(const Setup *setup, const App *app)
{
	const float cx = SCREEN_TOP_W * 0.5f;

	text_draw(cx, 86.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER,
	          setup->manual_connection ? tr(STR_SETUP_MANUAL)
	                                   : tr(STR_SETUP_HOST_TITLE));

	if (!setup->manual_connection) {
		const DiscoveredAgent *agent = discovery_at(setup->selected_agent);
		if (agent != NULL) {
			draw_round_rect(70.0f, 116.0f, SCREEN_TOP_W - 140.0f, 42.0f, 11.0f,
			                Z_CARD, theme_alpha(COL_SURFACE_HI, 0xE8));
			draw_round_rect_outline(70.0f, 116.0f, SCREEN_TOP_W - 140.0f,
			                        42.0f, 11.0f, 1.2f, Z_CONTENT,
			                        theme_alpha(COL_ACCENT, 0x99));
			icons_draw(ICON_APP, 92.0f, 137.0f, 20.0f, Z_OVERLAY,
			           COL_ACCENT);
			text_draw_clipped(110.0f, 121.0f, Z_OVERLAY, TEXT_BODY, COL_TEXT,
			                  ALIGN_LEFT, 205.0f, agent->announcement.name);
			char detail[96];
			snprintf(detail, sizeof(detail), "%s · %s", platform_label(agent->announcement.platform),
			         agent->host);
			text_draw_clipped(110.0f, 140.0f, Z_OVERLAY, TEXT_MICRO,
			                  COL_TEXT_FAINT, ALIGN_LEFT, 205.0f, detail);
		} else {
			if (app->settings.companion) {
				ui_companion_draw(discovery_scanning() ? DECKY_SEARCH : DECKY_CONFUSED,
				                  app->uptime, cx - 20, 106, 1);
			} else {
				icons_draw(ICON_POWER, cx, 126.0f, 30.0f, Z_CONTENT,
				           discovery_scanning() ? COL_ACCENT : COL_TEXT_FAINT);
			}
			text_draw(cx, 148.0f, Z_CONTENT, TEXT_SMALL,
			          discovery_scanning() ? COL_TEXT_DIM : COL_TEXT_FAINT,
			          ALIGN_CENTER,
			          discovery_scanning() ? tr(STR_SETUP_SEARCHING)
			                               : tr(STR_SETUP_NO_AGENT));
		}
	} else {
		char address[96];
		snprintf(address, sizeof(address), "%s:%d", app->settings.host,
		         app->settings.port);
		const float width = text_width(address, TEXT_LARGE) + 32.0f;
		const float box_x = cx - width * 0.5f;
		draw_round_rect(box_x, 118.0f, width, 30.0f, 8.0f, Z_CARD,
		                theme_alpha(COL_SURFACE_HI, 0xDD));
		draw_round_rect_outline(box_x, 118.0f, width, 30.0f, 8.0f, 1.0f,
		                        Z_CONTENT, theme_alpha(COL_BORDER, 0x99));
		text_draw(cx, 124.0f, Z_OVERLAY, TEXT_LARGE, COL_TEXT, ALIGN_CENTER,
		          address);
		text_draw(cx, 154.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_CENTER, tr(STR_SETUP_HOST_HELP));
	}

	/* Résultat du test de connexion. */
	const float y = 178.0f;

	switch (setup->probe) {
	case PROBE_RUNNING: {
		text_draw(cx, y, Z_CONTENT, TEXT_SMALL, COL_WARN, ALIGN_CENTER,
		          tr(STR_SETUP_TESTING));
		/* Petit indicateur d'activité, pour montrer que rien n'est figé. */
		const float phase = setup->probe_time * 4.0f;
		for (int i = 0; i < 3; i++) {
			const float alpha =
			    0.3f + 0.7f * (0.5f + 0.5f * sinf(phase - (float)i * 0.7f));
			draw_circle(cx - 12.0f + (float)i * 12.0f, y + 26.0f, 3.0f,
			            Z_CONTENT,
			            theme_alpha(COL_WARN, (u8)(alpha * 255.0f)));
		}
		break;
	}
	case PROBE_SUCCESS: {
		const char *label = tr(STR_SETUP_TEST_OK);
		const float left = cx - (text_width(label, TEXT_SMALL) + 24.0f) * 0.5f;
		draw_line(left + 2.0f, y + 8.0f, left + 6.0f, y + 12.0f,
		          2.0f, Z_CONTENT, COL_OK);
		draw_line(left + 6.0f, y + 12.0f, left + 14.0f, y + 4.0f,
		          2.0f, Z_CONTENT, COL_OK);
		text_draw(left + 24.0f, y, Z_CONTENT, TEXT_SMALL, COL_OK, ALIGN_LEFT, label);
		break;
	}
	case PROBE_FAILURE:
		text_draw(cx, y, Z_CONTENT, TEXT_SMALL, COL_ERR, ALIGN_CENTER,
		          tr(STR_SETUP_TEST_FAIL));
		break;
	case PROBE_IDLE:
	default:
		break;
	}
}

static void draw_done_step(const Setup *setup, const App *app)
{
	(void)app;
	const float cx = SCREEN_TOP_W * 0.5f;

	if (setup->first_run) {
		if (app->settings.companion) {
			ui_companion_draw(DECKY_WAVE, app->uptime, cx - 20, 76, 1);
		} else {
			icons_draw(ICON_STAR, cx, 92.0f, 40.0f, Z_CONTENT, COL_ACCENT);
		}
		text_draw(cx, 122.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER,
		          tr(STR_SETUP_DONE_TITLE));
		text_draw_clipped(cx, 152.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM,
		                  ALIGN_CENTER, SCREEN_TOP_W - 48.0f,
		                  tr(STR_SETUP_DONE_HELP));
		return;
	}

	/* Hors premier démarrage : rappel des commandes. */
	if (setup->selection == ROW_COMPANION) {
		text_draw(cx, 59, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER, "Decky");
		if (app->settings.companion) {
			/* Cycle the six expressions here so the setting is also a live preview. */
			const DeckyMood mood = (DeckyMood)((int)(fmodf(app->uptime, 24.0f) / 4.0f));
			ui_companion_draw(mood, app->uptime, cx - 60, 85, 3);
		} else {
			text_draw(cx, 140, Z_CONTENT, TEXT_LARGE, COL_TEXT_DIM, ALIGN_CENTER, tr(STR_OFF));
		}
		text_draw_clipped(cx, 214, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM,
		                  ALIGN_CENTER, 380, tr(STR_DECKY_HELP));
		return;
	}
	text_draw(cx, 70.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER,
	          tr(STR_SETTINGS));

	const StringId help[4] = {
	    STR_HELP_TOUCH,
	    STR_HELP_PAGES,
	    STR_HELP_RELOAD,
	    STR_HELP_QUIT,
	};

	for (int i = 0; i < 4; i++) {
		const float y = 108.0f + (float)i * 24.0f;
		draw_circle(34.0f, y + 7.0f, 2.5f, Z_CONTENT,
		            theme_alpha(COL_ACCENT, 0xAA));
		text_draw_clipped(46.0f, y, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM,
		                  ALIGN_LEFT, SCREEN_TOP_W - 70.0f, tr(help[i]));
	}
}

static void draw_community_qr(void)
{
	/* Four physical pixels per module: crisp edges and a full quiet zone. */
	const float module = 4.0f;
	const float size = COMMUNITY_QR_SIZE * module;
	const float left = (SCREEN_TOP_W - size) * 0.5f;
	const float top = 48.0f;
	draw_rect(left, top, size, size, Z_CARD, COL_WHITE);
	for (int row = 0; row < COMMUNITY_QR_SIZE; row++) {
		for (int col = 0; col < COMMUNITY_QR_SIZE;) {
			if (!community_qr[row][col]) { col++; continue; }
			const int first = col;
			while (col < COMMUNITY_QR_SIZE && community_qr[row][col]) col++;
			draw_rect(left + first * module, top + row * module,
			          (col - first) * module, module, Z_CONTENT,
			          C2D_Color32(0, 0, 0, 255));
		}
	}
	text_draw(SCREEN_TOP_W * 0.5f, 210.0f, Z_CONTENT, TEXT_SMALL,
	          COL_TEXT_DIM, ALIGN_CENTER, COMMUNITY_URL + 8);
}

void setup_draw_top(const Setup *setup, const App *app)
{
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, COL_ACCENT, 0.10f), COL_BG);

	if (setup->community_open) {
		text_draw(SCREEN_TOP_W * 0.5f, 14.0f, Z_CONTENT, TEXT_LARGE,
		          COL_TEXT, ALIGN_CENTER, "3Decks · Discord");
		draw_community_qr();
		return;
	}

	/* Titre de l'application, en tête. */
	text_draw(SCREEN_TOP_W * 0.5f, 14.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT,
	          ALIGN_CENTER,
	          setup->first_run ? tr(STR_WELCOME_TITLE) : "3Decks");

	if (setup->save_error[0] != '\0' && setup->step == SETUP_DONE) {
		/* The dashboard toast is not drawn while setup owns the top screen. */
		text_draw_clipped(SCREEN_TOP_W * 0.5f, 94.0f, Z_CONTENT,
		                  TEXT_BODY, COL_ERR, ALIGN_CENTER, 376.0f,
		                  tr(STR_SETTINGS_SAVE_FAILED));
		text_draw(SCREEN_TOP_W * 0.5f, 126.0f, Z_CONTENT, TEXT_BODY,
		          COL_TEXT, ALIGN_CENTER, setup->save_error);
		return;
	}

	if (setup->first_run) {
		draw_steps(setup);
	}

	switch (setup->step) {
	case SETUP_LANGUAGE:
		draw_language_step(setup);
		if (app->settings.companion) {
			ui_companion_draw(DECKY_WAVE, app->uptime, 160, 153, 2);
		}
		break;
	case SETUP_HOST:
		draw_host_step(setup, app);
		break;
	case SETUP_DONE:
	default:
		draw_done_step(setup, app);
		break;
	}
}

void setup_draw_pairing_top(const App *app)
{
	const float cx = SCREEN_TOP_W * 0.5f;
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, COL_ACCENT, 0.10f), COL_BG);
	text_draw(cx, 27.0f, Z_CONTENT, TEXT_HUGE, COL_TEXT, ALIGN_CENTER, "3Decks");
	if (app->settings.companion) {
		ui_companion_draw(DECKY_WAVE, app->uptime, cx - 40.0f, 68.0f, 2);
	} else {
		icons_draw(ICON_LOCK, cx, 108.0f, 32.0f, Z_CONTENT, COL_ACCENT);
	}
	text_draw_clipped(cx, 159.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT,
	                  ALIGN_CENTER, 352.0f, tr(STR_SETUP_PAIR_COMPUTER));
	text_draw_clipped(cx, 185.0f, Z_CONTENT, TEXT_BODY, COL_TEXT_DIM,
	                  ALIGN_CENTER, 352.0f, tr(STR_SETUP_PAIR_ENTER));
}
