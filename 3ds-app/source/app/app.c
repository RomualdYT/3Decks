/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "app.h"
#include "monotonic.h"

#include <3ds.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "app_feedback.h"
#include "app_network.h"
#include "app_settings.h"
#include "i18n.h"
#include "protocol.h"
#include "sound.h"
#include "top_visuals.h"
#include "extension_ui.h"

/** Durée d'affichage d'une notification. */
#define TOAST_DURATION 2.6f

/** Inactivité avant assombrissement de l'écran. */
#define DIM_DELAY 45.0f

bool app_save_settings(App *app)
{
	if (!app_settings_save(&app->settings)) {
		return false;
	}
	app->settings.configured = true;
	return true;
}

void app_init(App *app)
{
	memset(app, 0, sizeof(*app));

	app_settings_load(&app->settings);

	/*
	 * L'adresse transmise par 3dslink est prioritaire sur le fichier de
	 * réglages : elle correspond à la machine qui vient d'envoyer
	 * l'application, ce qui est l'intention la plus probable et évite de
	 * modifier la carte SD à chaque changement de réseau.
	 */
	app->host_from_netload = app_settings_detect_netload_host(&app->settings);

	/* La langue enregistrée s'applique dès l'initialisation. */
	i18n_set_language((Language)app->settings.language);
	sound_set_enabled(app->settings.sound);

	model_config_clear(&app->config);
	model_state_clear(&app->state);

	app->link = LINK_OFFLINE;
	app->reconnect_at = monotonic_seconds() + 0.2;
	app->reconnect_in = 0.2f; /* première tentative presque immédiate */
	app->reconnect_attempt = 0;
	app->pending_ping_id = -1;
	app->current_page = 0;
	app->next_request_id = 1;
	app->pressed_slot = -1;
	app->page_fade = 1.0f;
	app->toast.ttl = 0.0f;
	app->toast.alpha = 0.0f;
	/* Valeur impossible : la première configuration jouera donc l'animation. */
	app->last_page_count = -1;
	app->list_focus = -1;
	app->grid_focus = -1;
	app->battery_level = -1;
	top_visuals_init(&app->top_visual);
	performance_history_init(&app->performance_history);

	/*
	 * Le service d'alimentation reste ouvert pendant toute la durée de vie de
	 * l'application : l'ouvrir à chaque relevé coûterait plus que la lecture
	 * elle-même.
	 */
	ptmuInit();
}

void app_notify(App *app, const char *text, bool error)
{
	snprintf(app->toast.text, sizeof(app->toast.text), "%s",
	         (text != NULL) ? text : "");
	app->toast.error = error;
	app->toast.ttl = TOAST_DURATION;
	app->toast.icon = ICON_NONE;

	/*
	 * Un échec mérite un retour sonore distinct : il se remarque même si
	 * l'utilisateur ne regarde pas l'écran supérieur.
	 */
	if (error) {
		sound_play(SOUND_ERROR);
	}
}

void app_touch_activity(App *app)
{
	/*
	 * Toute interaction met fin à la veille. Le plein écran n'est quitté que
	 * s'il avait été déclenché par elle : un passage volontaire en mode cadre
	 * doit survivre à un simple contact.
	 */
	const bool was_asleep = app->dimmed;

	app->idle_time = 0.0f;
	app->dimmed = false;

	/*
	 * Seul un plein écran issu de la veille est refermé : un passage volontaire
	 * doit survivre à un simple contact.
	 */
	if (was_asleep && app->frame_from_idle) {
		app->frame_mode = false;
		app->frame_from_idle = false;
	}
}

void app_press_button(App *app, int slot, bool hold)
{
	const Page *page = app_current_page(app);
	if (page == NULL) {
		return;
	}
	if (slot < 0 || slot >= MAX_BUTTONS) {
		return;
	}

	const Button *button = &page->buttons[slot];
	if (!button->used) {
		return;
	}
	const ExtensionButtonState *extension = extension_button_state(&app->state, page->id, button->id);
	if (!hold && extension && !extension->available) {
		app_notify(app, tr(STR_EXTENSION_UNAVAILABLE), true);
		return;
	}

	if (app->link != LINK_ONLINE) {
		app_notify(app, tr(STR_PC_DISCONNECTED), true);
		return;
	}

	char payload[320];
	const int request_id = app->next_request_id;
	const int written = protocol_encode_button(payload, sizeof(payload),
	                                           request_id, page->id,
	                                           button->id, hold);
	if (written <= 0 || (size_t)written >= sizeof(payload)) {
		app_notify(app, tr(STR_COMMAND_TOO_LONG), true);
		return;
	}

	if (!net_send(payload, (size_t)written)) {
		app_notify(app, tr(STR_SEND_FAILED), true);
		return;
	}

	/*
	 * Le son accompagne l'envoi, pas la réponse : attendre la confirmation de
	 * l'ordinateur introduirait un décalage perceptible avec le geste.
	 */
	sound_play(button->toggle[0] != '\0' ? SOUND_TOGGLE : SOUND_TAP);

	app_feedback_begin(app, request_id, page->id, button->id);
	app->next_request_id++;
}

void app_press_action(App *app, const char *action)
{
	if (app->link != LINK_ONLINE || action == NULL) {
		return;
	}

	/*
	 * Le nom de l'action est transmis comme identifiant de bouton, sur une page
	 * réservée. L'ordinateur reconnaît ce préfixe et exécute l'action
	 * directement, sans qu'elle ait besoin de figurer dans la configuration.
	 */
	char payload[256];
	const int written = protocol_encode_button(
	    payload, sizeof(payload), app->next_request_id, "__direct", action,
	    false);

	if (written > 0 && (size_t)written < sizeof(payload) &&
	    net_send(payload, (size_t)written)) {
		app->next_request_id++;
	}
}

void app_press_entry(App *app, int index, bool hold)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_LIST) {
		return;
	}
	if (index < 0 || index >= page->entry_count) {
		return;
	}

	const ListEntry *entry = &page->entries[index];
	if (!entry->used) {
		return;
	}

	if (app->link != LINK_ONLINE) {
		app_notify(app, tr(STR_PC_DISCONNECTED), true);
		return;
	}

	/*
	 * Les éléments de liste empruntent le même message que les boutons :
	 * l'ordinateur retrouve l'action à partir de l'identifiant, sans avoir à
	 * distinguer les deux présentations.
	 */
	char payload[320];
	const int request_id = app->next_request_id;
	const int written = protocol_encode_button(payload, sizeof(payload),
	                                           request_id, page->id,
	                                           entry->id, hold);
	if (written <= 0 || (size_t)written >= sizeof(payload)) {
		app_notify(app, tr(STR_COMMAND_TOO_LONG), true);
		return;
	}

	if (!net_send(payload, (size_t)written)) {
		app_notify(app, tr(STR_SEND_FAILED), true);
		return;
	}

	app_feedback_begin(app, request_id, page->id, entry->id);
	sound_play(SOUND_TAP);
	app->next_request_id++;
}

int app_list_focus(const App *app)
{
	return app->list_focus;
}

void app_clear_focus(App *app)
{
	app->list_focus = -1;
	app->grid_focus = -1;
	app->battery_level = -1;

	/*
	 * Le service d'alimentation reste ouvert pendant toute la durée de vie de
	 * l'application : l'ouvrir à chaque relevé coûterait plus que la lecture
	 * elle-même.
	 */
	ptmuInit();
}

void app_move_grid_focus(App *app, int dx, int dy)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_GRID) {
		return;
	}

	/*
	 * Premier appui : on désigne le premier emplacement occupé, plutôt que
	 * l'emplacement zéro qui peut être vide.
	 */
	if (app->grid_focus < 0) {
		for (int i = 0; i < MAX_BUTTONS; i++) {
			if (page->buttons[i].used) {
				app->grid_focus = i;
				return;
			}
		}
		return;
	}

	int column = app->grid_focus % GRID_COLS;
	int row = app->grid_focus / GRID_COLS;

	column += dx;
	row += dy;

	/* On s'arrête aux bords : reboucler ferait perdre ses repères. */
	if (column < 0 || column >= GRID_COLS || row < 0 || row >= GRID_ROWS) {
		return;
	}

	const int target = row * GRID_COLS + column;

	/*
	 * Un emplacement vide n'est pas sélectionnable : la sélection reste sur
	 * place plutôt que de désigner un bouton inexistant.
	 */
	if (target < MAX_BUTTONS && page->buttons[target].used) {
		app->grid_focus = target;
		/* Retour discret : confirme que la sélection a bien bougé. */
		sound_play(SOUND_PAGE);
	}
}

void app_move_list_focus(App *app, int dx, int dy, int columns,
                         int visible_rows)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_LIST ||
	    page->entry_count == 0) {
		return;
	}

	const int count = page->entry_count;

	/*
	 * Premier appui sur la croix : on désigne l'élément visible en haut plutôt
	 * que le premier de la liste, afin que la sélection apparaisse là où se
	 * porte le regard.
	 */
	if (app->list_focus < 0) {
		app->list_focus = (int)(app->list_scroll + 0.5f) * columns;
		if (app->list_focus >= count) {
			app->list_focus = count - 1;
		}
		return;
	}

	int index = app->list_focus;

	if (dx != 0) {
		/*
		 * Déplacement horizontal : il reste dans la même rangée, sauf en bout
		 * de ligne où il passe naturellement à la suivante.
		 */
		index += dx;
	}

	if (dy != 0) {
		index += dy * columns;
	}

	if (index < 0 || index >= count) {
		return; /* on ne sort pas de la liste */
	}

	app->list_focus = index;
	sound_play(SOUND_PAGE);

	/*
	 * Défilement suiveur : la sélection doit rester visible, sans quoi la
	 * navigation au clavier deviendrait aveugle.
	 */
	const int row = index / columns;
	const int first_visible = (int)(app->list_target + 0.5f);
	const int last_visible = first_visible + visible_rows - 1;

	if (row < first_visible) {
		app->list_target = (float)row;
	} else if (row > last_visible) {
		app->list_target = (float)(row - visible_rows + 1);
	}
}

void app_scroll_list(App *app, float rows, float max_scroll)
{
	app->list_target += rows;

	if (app->list_target < 0.0f) {
		app->list_target = 0.0f;
	}
	if (app->list_target > max_scroll) {
		app->list_target = max_scroll;
	}
}

/** Met à jour l'horloge locale de repli. */
static void update_local_clock(App *app)
{
	static const char *const months_en[] = {
	    "January", "February", "March", "April", "May", "June",
	    "July", "August", "September", "October", "November", "December",
	};
	static const char *const months_fr[] = {
	    "janvier", "fevrier", "mars", "avril", "mai", "juin",
	    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
	};
	const time_t now = time(NULL);
	const struct tm *local = localtime(&now);
	if (local != NULL) {
		snprintf(app->local_time, sizeof(app->local_time), "%02d:%02d",
		         local->tm_hour, local->tm_min);
		const int month = local->tm_mon >= 0 && local->tm_mon < 12
		                      ? local->tm_mon
		                      : 0;
		if (i18n_language() == LANG_FR) {
			snprintf(app->local_date, sizeof(app->local_date), "%d %s",
			         local->tm_mday, months_fr[month]);
		} else {
			snprintf(app->local_date, sizeof(app->local_date), "%s %d",
			         months_en[month], local->tm_mday);
		}
	}
}

void app_update(App *app, float dt)
{
	app->uptime += dt;
	app->idle_time += dt;
	update_local_clock(app);
	top_visuals_update(app, dt);
	performance_history_update(&app->performance_history, &app->state, dt);

	/*
	 * L'agent n'envoie plus la liste entière uniquement parce que son âge a
	 * avancé. Une horloge locale garde donc les libellés « il y a … » justes,
	 * sans trafic ni analyse JSON supplémentaires à chaque seconde.
	 */
	app->notification_age_timer += dt;
	while (app->notification_age_timer >= 1.0f) {
		app->notification_age_timer -= 1.0f;
		for (int i = 0; i < app->state.notification_count; i++) {
			if (app->state.notifications[i].age < INT_MAX) {
				app->state.notifications[i].age++;
			}
		}
	}

	/*
	 * Batterie relevée une fois par seconde : la valeur ne change que très
	 * lentement, et l'appel traverse un service du système.
	 */
	app->battery_timer -= dt;
	if (app->battery_timer <= 0.0f) {
		app->battery_timer = 1.0f;

		u8 level = 0;
		if (R_SUCCEEDED(PTMU_GetBatteryLevel(&level))) {
			app->battery_level = (int)level;
		}

		u8 charging = 0;
		if (R_SUCCEEDED(PTMU_GetBatteryChargeState(&charging))) {
			app->battery_charging = charging != 0;
		}
	}

	/* Le liseré d'alerte s'estompe progressivement. */
	if (app->alert_glow > 0.0f) {
		app->alert_glow -= dt * 0.5f;
		if (app->alert_glow < 0.0f) {
			app->alert_glow = 0.0f;
		}
	}

	app_network_update(app);

	/* Notification : décompte puis fondu. */
	if (app->toast.ttl > 0.0f) {
		app->toast.ttl -= dt;
		const float target = 1.0f;
		app->toast.alpha += (target - app->toast.alpha) * dt * 12.0f;
	} else {
		app->toast.alpha += (0.0f - app->toast.alpha) * dt * 8.0f;
		if (app->toast.alpha < 0.01f) {
			app->toast.alpha = 0.0f;
		}
	}

	app_feedback_update(app, dt);

	/*
	 * Animation d'entrée des boutons.
	 *
	 * Le rythme est délibérément posé : environ huit dixièmes de seconde du
	 * premier au dernier bouton. Plus rapide, le mouvement paraissait nerveux à
	 * chaque changement de page.
	 */
	if (app->enter_anim < 1.0f) {
		app->enter_anim += dt * 1.5f;
		if (app->enter_anim > 1.0f) {
			app->enter_anim = 1.0f;
		}
	}

	/*
	 * Défilement de liste : la position rejoint sa cible en douceur, ce qui
	 * évite les sauts brusques quand le pavé circulaire est poussé à fond.
	 */
	const float scroll_delta = app->list_target - app->list_scroll;
	if (scroll_delta > 0.001f || scroll_delta < -0.001f) {
		app->list_scroll += scroll_delta * dt * 12.0f;
	} else {
		app->list_scroll = app->list_target;
	}

	/* Transition de page. */
	if (app->page_fade < 1.0f) {
		app->page_fade += dt * 4.5f;
		if (app->page_fade > 1.0f) {
			app->page_fade = 1.0f;
		}
	}

	/* Animation d'enfoncement des boutons. */
	const Page *page = app_current_page(app);
	if (page != NULL) {
		for (int i = 0; i < MAX_BUTTONS; i++) {
			Button *button = (Button *)&page->buttons[i];
			const float target = (app->pressed_slot == i) ? 1.0f : 0.0f;
			button->press += (target - button->press) * dt * 16.0f;
			if (button->press < 0.001f) {
				button->press = 0.0f;
			}
		}
	}

	/* Maintien : déclenche l'action secondaire une seule fois. */
	if (app->pressed_slot >= 0) {
		app->press_time += dt;

		if (!app->hold_fired && app->press_time >= APP_HOLD_THRESHOLD &&
		    page != NULL) {
			const Button *button = &page->buttons[app->pressed_slot];
			if (button->used && button->hold_label[0] != '\0') {
				app->hold_fired = true;
				app_press_button(app, app->pressed_slot, true);
			}
		}
	}

	/*
	 * Mise en veille de l'affichage. Le délai est configurable, et une valeur
	 * nulle désactive la fonction.
	 */
	if (app->settings.dim_delay > 0 &&
	    app->idle_time > (float)app->settings.dim_delay) {
		app->dimmed = true;

		/*
		 * La veille réutilise l'affichage plein écran : la pochette et l'heure
		 * valent mieux qu'un simple assombrissement, et l'image changeant à
		 * chaque morceau, l'usure de la dalle reste maîtrisée.
		 */
		if (app->state.media_present && !app->frame_mode) {
			app->frame_mode = true;
			app->frame_from_idle = true;
		}
	}
}
