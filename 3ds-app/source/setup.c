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

/** Durée maximale du test de connexion, en secondes. */
#define PROBE_TIMEOUT 4.0f

/** Nombre de lignes de l'écran de réglages. */
#define SETTINGS_ROWS 6

/* Indices des lignes de réglages. */
enum {
	ROW_LANGUAGE = 0,
	ROW_CONNECTION,
	ROW_SOUND,
	ROW_DIM,
	ROW_STEREO,
	ROW_RESET,
};

void setup_begin(Setup *setup, bool first_run)
{
	memset(setup, 0, sizeof(*setup));
	setup->active = true;
	setup->first_run = first_run;
	setup->step = first_run ? SETUP_LANGUAGE : SETUP_DONE;
	setup->probe = PROBE_IDLE;
	setup->selected_agent = -1;
}

void setup_open_settings(Setup *setup)
{
	memset(setup, 0, sizeof(*setup));
	setup->active = true;
	setup->first_run = false;
	setup->step = SETUP_DONE;
	setup->probe = PROBE_IDLE;
	setup->selected_agent = -1;
}

void setup_close(Setup *setup)
{
	setup->active = false;
	setup->probe = PROBE_IDLE;
	discovery_stop();
}

static void begin_connection_step(Setup *setup)
{
	setup->step = SETUP_HOST;
	setup->probe = PROBE_IDLE;
	setup->probe_time = 0.0f;
	setup->discovery_retry = 0.0f;
	setup->manual_connection = false;
	setup->selected_agent = -1;
	discovery_start();
}

static void start_probe(Setup *setup, App *app);

/**
 * Ouvre le clavier logiciel pour saisir une valeur.
 *
 * Le clavier système est utilisé plutôt qu'une saisie maison : il gère déjà le
 * stylet, les corrections et la validation, et reste familier à l'utilisateur.
 */
static bool prompt_text(const char *hint, char *value, size_t size,
                        SwkbdType type, int max_length)
{
	SwkbdState keyboard;
	swkbdInit(&keyboard, type, 2, max_length);
	swkbdSetHintText(&keyboard, hint);
	swkbdSetInitialText(&keyboard, value);
	swkbdSetValidation(&keyboard, SWKBD_NOTEMPTY_NOTBLANK, 0, 0);

	/*
	 * Le tampon de saisie ne dépasse jamais la destination : la copie finale
	 * passe par `snprintf`, qui tronque proprement, et le clavier est déjà
	 * limité par `max_length`.
	 */
	char buffer[64] = {0};

	const SwkbdButton pressed =
	    swkbdInputText(&keyboard, buffer, sizeof(buffer));

	if (pressed != SWKBD_BUTTON_CONFIRM) {
		return false;
	}

	snprintf(value, size, "%s", buffer);
	return true;
}

static bool prompt_pairing_code(App *app)
{
	char code[8] = {0};
	if (!prompt_text(tr(STR_SETUP_PAIR_CODE), code, sizeof(code),
	                 SWKBD_TYPE_NUMPAD, 6)) {
		return false;
	}
	if (strlen(code) != 6) {
		app_notify(app, tr(STR_SETUP_PAIR_HELP), true);
		return false;
	}
	for (int i = 0; i < 6; i++) {
		if (code[i] < '0' || code[i] > '9') {
			app_notify(app, tr(STR_SETUP_PAIR_HELP), true);
			return false;
		}
	}
	snprintf(app->pair_code, sizeof(app->pair_code), "%s", code);
	return true;
}

static bool select_discovered_agent(Setup *setup, App *app, int index)
{
	const DiscoveredAgent *agent = discovery_at(index);
	if (agent == NULL) {
		return false;
	}

	const bool same_agent =
	    strcmp(app->settings.host, agent->host) == 0 &&
	    app->settings.port == agent->announcement.port;

	snprintf(app->settings.agent_name, sizeof(app->settings.agent_name), "%s",
	         agent->announcement.name);
	snprintf(app->settings.host, sizeof(app->settings.host), "%s", agent->host);
	app->settings.port = agent->announcement.port;
	app->host_from_netload = false;
	app->pair_code[0] = '\0';

	/* Un jeton appartient à un agent précis : ne jamais l'essayer ailleurs. */
	if (!same_agent || !agent->announcement.pairing_required) {
		app->settings.token[0] = '\0';
	}

	if (agent->announcement.pairing_required &&
	    app->settings.token[0] == '\0' && !prompt_pairing_code(app)) {
		return false;
	}

	setup->selected_agent = index;
	start_probe(setup, app);
	return true;
}

void setup_handle_pairing_request(Setup *setup, App *app)
{
	if (!setup->active) {
		setup_open_settings(setup);
		begin_connection_step(setup);
	}
	setup->step = SETUP_HOST;
	setup->probe = PROBE_FAILURE;

	if (prompt_pairing_code(app)) {
		start_probe(setup, app);
	}
}

/** Lance un test de connexion vers l'adresse configurée. */
static void start_probe(Setup *setup, App *app)
{
	setup->probe = PROBE_RUNNING;
	setup->probe_time = 0.0f;

	/*
	 * Le test réutilise la connexion normale : réussir ici garantit donc que
	 * l'application fonctionnera réellement, ce qu'un simple ping ne prouverait
	 * pas.
	 */
	app->pairing_requested = false;
	app_force_reconnect(app);
}

void setup_update(Setup *setup, App *app, float dt)
{
	if (!setup->active) {
		return;
	}

	if (setup->step == SETUP_HOST && !setup->manual_connection) {
		discovery_set_known_host(app->settings.host);
		discovery_update(dt);
		if (discovery_count() == 0 && app->handshake_ok &&
		    app->settings.host[0] != '\0') {
			const char *name = app->settings.agent_name[0] != '\0'
			                       ? app->settings.agent_name
			                       : app->state.host;
			discovery_remember_known(app->settings.host, name,
			                         app->settings.port,
			                         app->settings.token[0] != '\0');
		}
		if (discovery_count() == 0 && !discovery_scanning()) {
			setup->discovery_retry += dt;
			if (setup->discovery_retry >= 1.5f) {
				discovery_start();
				setup->discovery_retry = 0.0f;
			}
		} else {
			setup->discovery_retry = 0.0f;
		}
		if (setup->selected_agent >= discovery_count()) {
			setup->selected_agent = -1;
		}
		if (setup->selected_agent == -1 && discovery_count() > 0) {
			setup->selected_agent = 0;
		}
	}

	if (setup->probe != PROBE_RUNNING) {
		return;
	}

	setup->probe_time += dt;

	if (app->handshake_ok && app->config_received) {
		setup->probe = PROBE_SUCCESS;
		return;
	}

	if (setup->probe_time > PROBE_TIMEOUT) {
		setup->probe = PROBE_FAILURE;
	}
}

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
			snprintf(detail, sizeof(detail), "%s · %s", agent->announcement.platform,
			         agent->host);
			text_draw_clipped(110.0f, 140.0f, Z_OVERLAY, TEXT_MICRO,
			                  COL_TEXT_FAINT, ALIGN_LEFT, 205.0f, detail);
		} else {
			icons_draw(ICON_POWER, cx, 126.0f, 30.0f, Z_CONTENT,
			           discovery_scanning() ? COL_ACCENT : COL_TEXT_FAINT);
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
	case PROBE_SUCCESS:
		icons_draw(ICON_STAR, cx - 60.0f, y + 8.0f, 15.0f, Z_CONTENT, COL_OK);
		text_draw(cx + 8.0f, y, Z_CONTENT, TEXT_SMALL, COL_OK, ALIGN_CENTER,
		          tr(STR_SETUP_TEST_OK));
		break;
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
		icons_draw(ICON_STAR, cx, 92.0f, 40.0f, Z_CONTENT, COL_ACCENT);
		text_draw(cx, 122.0f, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_CENTER,
		          tr(STR_SETUP_DONE_TITLE));
		text_draw_clipped(cx, 152.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM,
		                  ALIGN_CENTER, SCREEN_TOP_W - 48.0f,
		                  tr(STR_SETUP_DONE_HELP));
		return;
	}

	/* Hors premier démarrage : rappel des commandes. */
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

void setup_draw_top(const Setup *setup, const App *app)
{
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, COL_ACCENT, 0.10f), COL_BG);

	/* Titre de l'application, en tête. */
	text_draw(SCREEN_TOP_W * 0.5f, 14.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT,
	          ALIGN_CENTER,
	          setup->first_run ? tr(STR_WELCOME_TITLE) : "Deck3DS");

	if (setup->first_run) {
		draw_steps(setup);
	}

	switch (setup->step) {
	case SETUP_LANGUAGE:
		draw_language_step(setup);
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

/* --- Rendu de l'écran tactile --------------------------------------------- */

/* --- Découpage vertical de l'écran tactile -------------------------------- */

/** Hauteur du bouton principal. */
#define PRIMARY_BUTTON_H 36.0f

/** Marge sous le bouton principal. */
#define PRIMARY_BUTTON_MARGIN 10.0f

/** Première ligne de liste, sous le titre. */
#define ROWS_TOP 36.0f

/** Carte de choix de langue : hauteur et pas vertical. */
#define LANG_CARD_H 48.0f
#define LANG_CARD_PITCH 58.0f

/** Espace laissé entre la dernière ligne et le bouton. */
#define ROWS_GAP 8.0f

/** Espace vertical réellement disponible pour les lignes. */
#define ROWS_AVAILABLE                                                        \
	(SCREEN_H - PRIMARY_BUTTON_MARGIN - PRIMARY_BUTTON_H - ROWS_GAP - ROWS_TOP)

/** Bouton principal, en bas de l'écran. */
static void primary_button_bounds(float *x, float *y, float *w, float *h)
{
	*w = SCREEN_BOTTOM_W - 40.0f;
	*h = PRIMARY_BUTTON_H;
	*x = 20.0f;
	*y = SCREEN_H - PRIMARY_BUTTON_MARGIN - PRIMARY_BUTTON_H;
}

/**
 * Géométrie d'une ligne de liste.
 *
 * Le pas est calculé à partir de l'espace réellement disponible et du nombre de
 * lignes, jamais codé en dur : ajouter un réglage resserre automatiquement la
 * liste au lieu de la faire déborder sous le bouton.
 *
 * Le pas est plafonné pour que quelques lignes ne s'étalent pas sur tout
 * l'écran, et un plancher garantit que le texte reste lisible.
 */
static void row_bounds(int index, float *y, float *height)
{
	float pitch = ROWS_AVAILABLE / (float)SETTINGS_ROWS;

	if (pitch > 30.0f) {
		pitch = 30.0f;
	}
	if (pitch < 18.0f) {
		/*
		 * En deçà, le texte ne tiendrait plus : mieux vaut accepter un léger
		 * dépassement visuel qu'un texte illisible.
		 */
		pitch = 18.0f;
	}

	*height = pitch - 4.0f;
	*y = ROWS_TOP + (float)index * pitch;
}

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

#define AGENT_CARD_TOP 38.0f
#define AGENT_CARD_H 34.0f
#define AGENT_CARD_GAP 5.0f
#define AGENT_VISIBLE 3
#define MANUAL_CARD_Y 160.0f

/** Premier résultat à afficher lorsque la liste dépasse trois ordinateurs. */
static int first_visible_agent(const Setup *setup)
{
	const int count = discovery_count();
	if (count <= AGENT_VISIBLE || setup->selected_agent < AGENT_VISIBLE) {
		return 0;
	}

	int first = setup->selected_agent - AGENT_VISIBLE + 1;
	const int maximum = count - AGENT_VISIBLE;
	if (first > maximum) {
		first = maximum;
	}
	return first;
}

static void agent_card_bounds(int index, float *y)
{
	*y = AGENT_CARD_TOP + (float)index * (AGENT_CARD_H + AGENT_CARD_GAP);
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
static void advance(Setup *setup, App *app)
{
	if (setup->step == SETUP_LANGUAGE) {
		begin_connection_step(setup);
		return;
	}

	if (setup->step == SETUP_HOST) {
		if (setup->probe != PROBE_SUCCESS) {
			start_probe(setup, app);
			return;
		}
		discovery_stop();
		setup->step = SETUP_DONE;
		return;
	}

	/* Dernière étape : on enregistre et on quitte l'assistant. */
	app_save_settings(app);
	setup_close(setup);
}

/** Modifie la valeur d'une ligne de réglage. */
static void activate_row(Setup *setup, App *app, int row)
{
	switch (row) {
	case ROW_LANGUAGE: {
		const Language next =
		    (Language)((i18n_language() + 1) % LANG_COUNT);
		i18n_set_language(next);
		app->settings.language = (int)next;
		break;
	}
	case ROW_CONNECTION:
		begin_connection_step(setup);
		break;
	case ROW_SOUND:
		app->settings.sound = !app->settings.sound;
		/*
		 * Prise d'effet immédiate, puis son de confirmation : on entend donc
		 * le résultat du réglage au moment où on l'active.
		 */
		sound_set_enabled(app->settings.sound);
		if (app->settings.sound) {
			sound_play(SOUND_TOGGLE);
		}
		break;
	case ROW_DIM: {
		/* Cycle sur quelques durées usuelles, plus « jamais ». */
		static const int steps[] = {0, 15, 30, 45, 60, 120};
		const int count = (int)(sizeof(steps) / sizeof(steps[0]));

		int index = 0;
		for (int i = 0; i < count; i++) {
			if (steps[i] == app->settings.dim_delay) {
				index = i;
				break;
			}
		}
		app->settings.dim_delay = steps[(index + 1) % count];
		break;
	}
	case ROW_STEREO:
		app->settings.stereo = !app->settings.stereo;
		break;
	case ROW_RESET:
		/* Relance le parcours guidé depuis le début. */
		setup->first_run = true;
		discovery_stop();
		setup->step = SETUP_LANGUAGE;
		setup->probe = PROBE_IDLE;
		break;
	default:
		break;
	}
}

static void edit_manual_host(Setup *setup, App *app)
{
	if (prompt_text(tr(STR_SETTINGS_HOST), app->settings.host,
	                sizeof(app->settings.host), SWKBD_TYPE_QWERTY, 63)) {
		app->settings.agent_name[0] = '\0';
		app->settings.token[0] = '\0';
		app->pair_code[0] = '\0';
		setup->probe = PROBE_IDLE;
		app_force_reconnect(app);
	}
}

static void edit_manual_port(Setup *setup, App *app)
{
	char port[16];
	snprintf(port, sizeof(port), "%d", app->settings.port);
	if (prompt_text(tr(STR_SETTINGS_PORT), port, sizeof(port),
	                SWKBD_TYPE_NUMPAD, 5)) {
		const int value = atoi(port);
		if (value > 0 && value < 65536) {
			app->settings.port = value;
			app->settings.agent_name[0] = '\0';
			app->settings.token[0] = '\0';
			app->pair_code[0] = '\0';
			setup->probe = PROBE_IDLE;
			app_force_reconnect(app);
		}
	}
}

bool setup_touch(Setup *setup, App *app, float x, float y)
{
	if (!setup->active) {
		return false;
	}

	/* Bouton principal. */
	float bx;
	float by;
	float bw;
	float bh;
	primary_button_bounds(&bx, &by, &bw, &bh);

	if (x >= bx && x < bx + bw && y >= by && y < by + bh) {
		if (setup->step == SETUP_DONE && !setup->first_run) {
			if (app_save_settings(app)) {
				app_notify(app, tr(STR_SETTINGS_SAVED), false);
			} else {
				app_notify(app, tr(STR_SETTINGS_SAVE_FAILED), true);
			}
			setup_close(setup);
			return true;
		}
		if (setup->step == SETUP_HOST && !setup->manual_connection) {
			if (setup->probe == PROBE_SUCCESS) {
				advance(setup, app);
			} else if (setup->selected_agent >= 0) {
				select_discovered_agent(setup, app, setup->selected_agent);
			} else if (setup->selected_agent == -2) {
				setup->manual_connection = true;
				setup->selection = 0;
				discovery_stop();
			} else {
				discovery_start();
			}
		} else {
			advance(setup, app);
		}
		return true;
	}

	/* Choix de la langue. */
	if (setup->step == SETUP_LANGUAGE) {
		for (int i = 0; i < LANG_COUNT; i++) {
			const float row_y = ROWS_TOP + 10.0f + (float)i * LANG_CARD_PITCH;
			if (y >= row_y && y < row_y + LANG_CARD_H && x >= 24.0f &&
			    x < SCREEN_BOTTOM_W - 24.0f) {
				i18n_set_language((Language)i);
				app->settings.language = i;
				return true;
			}
		}
		return true;
	}

	/* Lignes de l'étape « ordinateur ». */
	if (setup->step == SETUP_HOST) {
		if (!setup->manual_connection) {
			const int visible = discovery_count() < AGENT_VISIBLE
			                        ? discovery_count()
			                        : AGENT_VISIBLE;
			const int first = first_visible_agent(setup);
			for (int row = 0; row < visible; row++) {
				float row_y;
				agent_card_bounds(row, &row_y);
				if (x >= 14.0f && x < SCREEN_BOTTOM_W - 14.0f &&
				    y >= row_y && y < row_y + AGENT_CARD_H) {
					setup->selected_agent = first + row;
					return true;
				}
			}
			if (x >= 14.0f && x < SCREEN_BOTTOM_W - 14.0f &&
			    y >= MANUAL_CARD_Y && y < MANUAL_CARD_Y + 28.0f) {
				setup->manual_connection = true;
				setup->selected_agent = -2;
				setup->selection = 0;
				discovery_stop();
				return true;
			}
			return true;
		}

		for (int i = 0; i < 3; i++) {
			float row_y;
			float row_h;
			row_bounds(i, &row_y, &row_h);

			if (y >= row_y && y < row_y + row_h) {
				if (i == 0) {
					edit_manual_host(setup, app);
				} else if (i == 1) {
					edit_manual_port(setup, app);
				} else {
					begin_connection_step(setup);
				}
				return true;
			}
		}
		return true;
	}

	/* Lignes de réglages. */
	for (int i = 0; i < SETTINGS_ROWS; i++) {
		float row_y;
		float row_h;
		row_bounds(i, &row_y, &row_h);

		if (y >= row_y && y < row_y + row_h) {
			setup->selection = i;
			activate_row(setup, app, i);
			return true;
		}
	}

	return true;
}

void setup_buttons(Setup *setup, App *app, u32 pressed)
{
	if (!setup->active) {
		return;
	}

	if (pressed & KEY_A) {
		if (setup->step == SETUP_DONE && !setup->first_run) {
			activate_row(setup, app, setup->selection);
		} else if (setup->step == SETUP_HOST && !setup->manual_connection) {
			if (setup->probe == PROBE_SUCCESS) {
				advance(setup, app);
			} else if (setup->selected_agent >= 0) {
				select_discovered_agent(setup, app, setup->selected_agent);
			} else if (setup->selected_agent == -2) {
				setup->manual_connection = true;
				setup->selection = 0;
				discovery_stop();
			} else {
				discovery_start();
			}
		} else if (setup->step == SETUP_HOST && setup->manual_connection) {
			if (setup->selection == 0) {
				edit_manual_host(setup, app);
			} else if (setup->selection == 1) {
				edit_manual_port(setup, app);
			} else if (setup->selection == 2) {
				begin_connection_step(setup);
			} else {
				advance(setup, app);
			}
		} else {
			advance(setup, app);
		}
	}

	if (pressed & KEY_B) {
		if (setup->step == SETUP_HOST) {
			if (setup->manual_connection) {
				begin_connection_step(setup);
			} else if (setup->first_run) {
				discovery_stop();
				setup->step = SETUP_LANGUAGE;
			} else {
				discovery_stop();
				setup->step = SETUP_DONE;
			}
		} else if (setup->step == SETUP_DONE && setup->first_run) {
			begin_connection_step(setup);
		} else if (!setup->first_run) {
			/* Hors premier démarrage, B ferme les réglages. */
			app_save_settings(app);
			setup_close(setup);
		}
	}

	if (setup->step == SETUP_DONE && !setup->first_run) {
		if (pressed & KEY_DOWN) {
			setup->selection = (setup->selection + 1) % SETTINGS_ROWS;
		}
		if (pressed & KEY_UP) {
			setup->selection =
			    (setup->selection + SETTINGS_ROWS - 1) % SETTINGS_ROWS;
		}
	}

	if (setup->step == SETUP_HOST && !setup->manual_connection) {
		const int count = discovery_count();
		if (pressed & KEY_DOWN) {
			if (setup->selected_agent == -2) {
				setup->selected_agent = count > 0 ? 0 : -2;
			} else if (setup->selected_agent >= 0 &&
			           setup->selected_agent < count - 1) {
				setup->selected_agent++;
			} else {
				setup->selected_agent = -2;
			}
		}
		if (pressed & KEY_UP) {
			if (setup->selected_agent == -2) {
				setup->selected_agent = count > 0 ? count - 1 : -2;
			} else if (setup->selected_agent > 0) {
				setup->selected_agent--;
			} else {
				setup->selected_agent = -2;
			}
		}
	}

	if (setup->step == SETUP_HOST && setup->manual_connection) {
		if (pressed & KEY_DOWN) {
			setup->selection = (setup->selection + 1) % 4;
		}
		if (pressed & KEY_UP) {
			setup->selection = (setup->selection + 3) % 4;
		}
	}

	if (setup->step == SETUP_LANGUAGE) {
		if (pressed & (KEY_DOWN | KEY_UP)) {
			const Language next =
			    (Language)((i18n_language() + 1) % LANG_COUNT);
			i18n_set_language(next);
			app->settings.language = (int)next;
		}
	}
}
