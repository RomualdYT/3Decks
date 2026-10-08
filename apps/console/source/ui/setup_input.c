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
#include <arpa/inet.h>

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
	case ROW_COMPANION:
		app->settings.companion = (app->settings.companion + 1) % 3;
		break;
	default:
		break;
	}
}

static void edit_manual_host(Setup *setup, App *app)
{
	char host[sizeof(app->settings.host)];
	snprintf(host, sizeof(host), "%s", app->settings.host);
	if (prompt_text(tr(STR_SETTINGS_HOST), host, sizeof(host), SWKBD_TYPE_QWERTY, 15)) {
		struct in_addr address;
		if (inet_pton(AF_INET, host, &address) != 1) {
			app_notify(app, tr(STR_SETTINGS_IPV4_REQUIRED), true);
			return;
		}
		snprintf(app->settings.host, sizeof(app->settings.host), "%s", host);
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

	if (setup->community_open) {
		if (y >= SCREEN_H - PRIMARY_BUTTON_MARGIN - PRIMARY_BUTTON_H) setup->community_open = false;
		return true;
	}

	/* Bouton principal. */
	float bx;
	float by;
	float bw;
	float bh;
	primary_button_bounds(&bx, &by, &bw, &bh);

	if (x >= bx && x < bx + bw && y >= by && y < by + bh) {
		if (setup->step == SETUP_DONE && !setup->first_run && x >= SETTINGS_COMMUNITY_X) {
			setup->community_open = true;
			return true;
		}
		if (setup->step == SETUP_DONE && !setup->first_run && x >= 20.0f + SETTINGS_SAVE_W) return true;
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

	if (setup->community_open) {
		if (pressed & (KEY_A | KEY_B | KEY_X)) setup->community_open = false;
		return;
	}
	if (setup->step == SETUP_DONE && !setup->first_run && (pressed & KEY_X)) {
		setup->community_open = true;
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
