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
#define PROBE_TIMEOUT 4.0f

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

void begin_connection_step(Setup *setup)
{
	setup->step = SETUP_HOST;
	setup->probe = PROBE_IDLE;
	setup->probe_time = 0.0f;
	setup->discovery_retry = 0.0f;
	setup->manual_connection = false;
	setup->selected_agent = -1;
	discovery_start();
}

void start_probe(Setup *setup, App *app);

/**
 * Ouvre le clavier logiciel pour saisir une valeur.
 *
 * Le clavier système est utilisé plutôt qu'une saisie maison : il gère déjà le
 * stylet, les corrections et la validation, et reste familier à l'utilisateur.
 */
bool prompt_text(const char *hint, char *value, size_t size,
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

bool prompt_pairing_code(App *app)
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

bool select_discovered_agent(Setup *setup, App *app, int index)
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
void start_probe(Setup *setup, App *app)
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
