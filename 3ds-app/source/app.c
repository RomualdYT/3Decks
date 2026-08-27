/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "app.h"

#include <3ds.h>
#include <arpa/inet.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#include "artwork.h"
#include "i18n.h"
#include "protocol.h"
#include "sound.h"

/** Délai entre deux tentatives de connexion, en secondes. */
#define RECONNECT_DELAY 2.0f

/** Durée d'affichage d'une notification. */
#define TOAST_DURATION 2.6f

/** Durée de maintien déclenchant l'action secondaire. */
#define HOLD_THRESHOLD 0.45f

/** Inactivité avant assombrissement de l'écran. */
#define DIM_DELAY 45.0f

#define SETTINGS_PATH "sdmc:/3ds/deck3ds/settings.cfg"

static char s_rx_message[NET_MAX_MESSAGE];

/** Retire les espaces en début et fin de chaîne, sur place. */
static void trim(char *text)
{
	size_t start = 0;
	while (text[start] == ' ' || text[start] == '\t') {
		start++;
	}

	size_t end = strlen(text);
	while (end > start) {
		const char c = text[end - 1];
		if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
			end--;
		} else {
			break;
		}
	}

	const size_t length = end - start;
	if (start > 0) {
		memmove(text, text + start, length);
	}
	text[length] = '\0';
}

/**
 * Charge les réglages depuis la carte SD.
 *
 * Le format est volontairement trivial (`clé=valeur`) pour être modifiable
 * depuis n'importe quel éditeur de texte, sans passer par l'application.
 */
static void load_settings(Settings *settings)
{
	/* Valeurs par défaut : adresse manifestement à personnaliser. */
	snprintf(settings->host, sizeof(settings->host), "192.168.1.10");
	settings->port = 38123;
	settings->token[0] = '\0';
	settings->sound = true;
	settings->language = (int)LANG_EN;
	settings->dim_delay = 45;
	settings->stereo = true;
	settings->configured = false;

	FILE *file = fopen(SETTINGS_PATH, "r");
	if (file == NULL) {
		return;
	}

	char line[192];
	while (fgets(line, sizeof(line), file) != NULL) {
		if (line[0] == '#' || line[0] == ';') {
			continue;
		}

		char *separator = strchr(line, '=');
		if (separator == NULL) {
			continue;
		}
		*separator = '\0';

		char *key = line;
		char *value = separator + 1;
		trim(key);
		trim(value);

		if (strcmp(key, "host") == 0) {
			snprintf(settings->host, sizeof(settings->host), "%s", value);
		} else if (strcmp(key, "port") == 0) {
			const int port = atoi(value);
			if (port > 0 && port < 65536) {
				settings->port = port;
			}
		} else if (strcmp(key, "token") == 0) {
			snprintf(settings->token, sizeof(settings->token), "%s", value);
		} else if (strcmp(key, "sound") == 0) {
			settings->sound = strcmp(value, "0") != 0 &&
			                  strcmp(value, "false") != 0 &&
			                  strcmp(value, "off") != 0;
		} else if (strcmp(key, "language") == 0) {
			/* Codes courts, plus lisibles qu'un numéro dans le fichier. */
			if (strcmp(value, "fr") == 0) {
				settings->language = (int)LANG_FR;
			} else {
				settings->language = (int)LANG_EN;
			}
		} else if (strcmp(key, "dim_delay") == 0) {
			const int delay = atoi(value);
			if (delay >= 0 && delay <= 600) {
				settings->dim_delay = delay;
			}
		} else if (strcmp(key, "stereo") == 0) {
			settings->stereo = strcmp(value, "0") != 0 &&
			                   strcmp(value, "false") != 0 &&
			                   strcmp(value, "off") != 0;
		} else if (strcmp(key, "configured") == 0) {
			settings->configured = strcmp(value, "0") != 0 &&
			                       strcmp(value, "false") != 0;
		}
	}

	fclose(file);
}

/**
 * Détecte l'adresse du PC ayant envoyé l'application par Wi-Fi.
 *
 * Lorsque l'application est transmise avec `3dslink`, le Homebrew Launcher
 * renseigne `__3dslink_host` avec l'adresse de l'ordinateur émetteur. C'est
 * presque toujours celui qui fait tourner l'agent : on peut donc s'y connecter
 * sans que l'utilisateur ait à saisir quoi que ce soit.
 *
 * Retourne `true` si une adresse a été trouvée et écrite dans `settings`.
 */
static bool detect_netload_host(Settings *settings)
{
	if (__3dslink_host.s_addr == 0) {
		return false; /* lancement depuis la carte SD */
	}

	const char *text = inet_ntoa(__3dslink_host);
	if (text == NULL || text[0] == '\0') {
		return false;
	}

	snprintf(settings->host, sizeof(settings->host), "%s", text);
	return true;
}

bool app_save_settings(App *app)
{
	/*
	 * Le dossier peut ne pas exister au premier enregistrement : on le crée
	 * sans considérer comme une erreur le cas où il est déjà présent.
	 */
	mkdir("sdmc:/3ds", 0777);
	mkdir("sdmc:/3ds/deck3ds", 0777);

	FILE *file = fopen(SETTINGS_PATH, "w");
	if (file == NULL) {
		return false;
	}

	app->settings.configured = true;

	/*
	 * Le fichier reste volontairement lisible et commenté : il doit pouvoir
	 * être corrigé depuis un ordinateur si la console ne démarre plus
	 * correctement.
	 */
	fprintf(file,
	        "# Reglages Deck3DS\n"
	        "# Fichier ecrit par l'application. Modifiable a la main.\n"
	        "\n"
	        "# Adresse de l'ordinateur qui execute l'agent.\n"
	        "host = %s\n"
	        "port = %d\n"
	        "\n"
	        "# Jeton partage, si l'agent en exige un.\n"
	        "token = %s\n"
	        "\n"
	        "# Langue de l'interface : en ou fr.\n"
	        "language = %s\n"
	        "\n"
	        "# Retour au toucher : 1 ou 0.\n"
	        "sound = %d\n"
	        "\n"
	        "# Assombrissement apres inactivite, en secondes. 0 pour jamais.\n"
	        "dim_delay = %d\n"
	        "\n"
	        "# Relief 3D de l'ecran du haut : 1 ou 0.\n"
	        "# L'intensite suit le curseur 3D de la console.\n"
	        "stereo = %d\n"
	        "\n"
	        "# Mis a 1 une fois la configuration initiale effectuee.\n"
	        "configured = 1\n",
	        app->settings.host, app->settings.port, app->settings.token,
	        app->settings.language == (int)LANG_FR ? "fr" : "en",
	        app->settings.sound ? 1 : 0, app->settings.dim_delay,
	        app->settings.stereo ? 1 : 0);

	return fclose(file) == 0;
}

void app_init(App *app)
{
	memset(app, 0, sizeof(*app));

	load_settings(&app->settings);

	/*
	 * L'adresse transmise par 3dslink est prioritaire sur le fichier de
	 * réglages : elle correspond à la machine qui vient d'envoyer
	 * l'application, ce qui est l'intention la plus probable et évite de
	 * modifier la carte SD à chaque changement de réseau.
	 */
	app->host_from_netload = detect_netload_host(&app->settings);

	/* La langue enregistrée s'applique dès l'initialisation. */
	i18n_set_language((Language)app->settings.language);
	sound_set_enabled(app->settings.sound);

	model_config_clear(&app->config);
	model_state_clear(&app->state);

	app->link = LINK_OFFLINE;
	app->reconnect_in = 0.2f; /* première tentative presque immédiate */
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

const Page *app_current_page(const App *app)
{
	return model_page_at(&app->config, app->current_page);
}

DashboardMode app_effective_dashboard(const App *app)
{
	/*
	 * Le plein écran est un état de l'affichage, pas une page : il prime donc
	 * sur le tableau de bord de la page courante. C'est ce qui permet de
	 * l'activer depuis n'importe où et de le réutiliser pour la veille.
	 */
	if (app->frame_mode) {
		return DASH_FRAME;
	}

	const Page *page = app_current_page(app);
	const DashboardMode mode = (page != NULL) ? page->dashboard : DASH_AUTO;

	if (mode != DASH_AUTO) {
		return mode;
	}

	/*
	 * En mode automatique, le média prime dès qu'un titre est connu : c'est
	 * l'information la plus utile en un coup d'œil.
	 */
	if (app->state.media_present) {
		return DASH_MEDIA;
	}
	return DASH_APPS;
}

void app_goto_page(App *app, int index)
{
	if (app->config.page_count <= 0) {
		return;
	}
	if (index < 0 || index >= app->config.page_count) {
		return;
	}
	if (index == app->current_page) {
		return;
	}

	app->current_page = index;
	app->page_fade = 0.0f; /* relance l'animation d'entrée */
	sound_play(SOUND_PAGE);
	app->enter_anim = 0.0f;

	/* Le défilement repart du haut à chaque changement de page. */
	app->list_scroll = 0.0f;
	app->list_target = 0.0f;
	app->list_focus = -1;
	app->grid_focus = -1;
	app_touch_activity(app);
}

void app_cycle_page(App *app, int delta)
{
	const int count = app->config.page_count;
	if (count <= 0) {
		return;
	}

	int index = app->current_page + delta;
	while (index < 0) {
		index += count;
	}
	index %= count;

	app_goto_page(app, index);
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

	if (app->link != LINK_ONLINE) {
		app_notify(app, tr(STR_PC_DISCONNECTED), true);
		return;
	}

	char payload[320];
	const int written = protocol_encode_button(payload, sizeof(payload),
	                                           app->next_request_id, page->id,
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
	const int written = protocol_encode_button(payload, sizeof(payload),
	                                           app->next_request_id, page->id,
	                                           entry->id, hold);
	if (written <= 0 || (size_t)written >= sizeof(payload)) {
		app_notify(app, tr(STR_COMMAND_TOO_LONG), true);
		return;
	}

	if (!net_send(payload, (size_t)written)) {
		app_notify(app, tr(STR_SEND_FAILED), true);
		return;
	}

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

/** Envoie le message `hello` dès que la connexion est établie. */
static void send_hello(App *app)
{
	char payload[192];
	const int written = protocol_encode_hello(
	    payload, sizeof(payload), "new3dsxl", app->settings.token,
	    i18n_language() == LANG_FR ? "fr" : "en");

	if (written > 0 && (size_t)written < sizeof(payload) &&
	    net_send(payload, (size_t)written)) {
		app->hello_sent = true;
	}
}

void app_pump_network(App *app)
{
	net_poll();

	const NetState state = net_state();

	switch (state) {
	case NET_IDLE:
		if (app->link != LINK_OFFLINE) {
			app->link = LINK_OFFLINE;
			app->hello_sent = false;
			app->config_received = false;
			snprintf(app->link_error, sizeof(app->link_error), "%s",
			         net_last_error());
			app->reconnect_in = RECONNECT_DELAY;
		}
		break;

	case NET_CONNECTING:
		app->link = LINK_CONNECTING;
		break;

	case NET_CONNECTED:
		if (!app->hello_sent) {
			send_hello(app);
		}
		if (app->link != LINK_ONLINE) {
			/* Signale la reprise de liaison sans avoir à surveiller l'écran. */
			sound_play(SOUND_CONNECT);
		}
		app->link = LINK_ONLINE;
		break;
	}

	if (app->link != LINK_ONLINE) {
		return;
	}

	/* On traite tous les messages disponibles, en bornant le travail par frame. */
	for (int budget = 0; budget < 8; budget++) {
		size_t length = 0;
		if (!net_receive(s_rx_message, sizeof(s_rx_message), &length)) {
			break;
		}

		/*
		 * Les pochettes arrivent sous forme binaire et non en JSON : elles sont
		 * donc reconnues et consommées avant toute tentative d'analyse.
		 */
		if (artwork_consume(s_rx_message, length)) {
			continue;
		}

		IncomingMessage message;
		if (!protocol_decode(s_rx_message, length, &message, &app->config,
		                     &app->state)) {
			continue; /* message illisible : on l'ignore */
		}

		switch (message.kind) {
		case MSG_CONFIG_SNAPSHOT: {
			/*
			 * L'animation d'entrée ne doit se rejouer que si la mise en page a
			 * réellement changé.
			 *
			 * L'ordinateur renvoie la configuration dès que la liste des
			 * fenêtres évolue, ce qui arrive sans cesse : un titre de navigateur
			 * ou un morceau qui défile suffit. Rejouer l'animation à chaque fois
			 * donnait l'impression que l'interface se réinitialisait toute
			 * seule.
			 *
			 * La configuration reçue est toujours appliquée. Seul le nombre de
			 * pages décide si l'animation structurelle doit être rejouée : les
			 * changements de libellés n'affectent pas l'animation.
			 */
			const bool first_config = !app->config_received;
			const bool layout_changed =
			    app->config.page_count != app->last_page_count;

			app->config_received = true;
			app->last_page_count = app->config.page_count;

			if (app->current_page >= app->config.page_count) {
				app->current_page = 0;
			}

			if (first_config || layout_changed) {
				app->page_fade = 0.0f;
				app->enter_anim = 0.0f;
			}
			break;
		}

		case MSG_STATE_UPDATE:
			/*
			 * Une notification venant d'arriver est annoncée comme les autres
			 * messages, mais avec un timbre distinct : elle vient de
			 * l'ordinateur et non d'une action de l'utilisateur.
			 */
			if (message.has_notification) {
				/*
				 * Application et titre sont réunis directement dans la
				 * destination : `snprintf` tronque alors proprement si la
				 * somme des deux dépasse la place disponible.
				 */
				if (message.notification_app[0] != '\0') {
					/*
					 * Le nom de l'application est borné explicitement : la
					 * troncature du titre est voulue, et le compilateur ne peut
					 * pas le déduire seul.
					 */
					snprintf(app->toast.text, sizeof(app->toast.text),
					         "%.16s : %.40s", message.notification_app,
					         message.notification_title);
				} else {
					snprintf(app->toast.text, sizeof(app->toast.text), "%s",
					         message.notification_title);
				}

				app->toast.error = false;
				app->toast.ttl = TOAST_DURATION;
				app->toast.icon = message.notification_icon;
				sound_play(SOUND_CONNECT);
				/* Alerte visible du coin de l'œil, même de loin. */
				app->alert_glow = 1.0f;
			}
			break;

		case MSG_ACTION_RESULT:
			if (message.open_settings) {
				app->settings_requested = true;
			}
			if (message.open_modal) {
				app->modal_requested = true;
			}
			if (message.toggle_frame) {
				app->frame_requested = true;
			}
			if (message.open_page[0] != '\0') {
				const int index = model_find_page(&app->config,
				                                  message.open_page);
				if (index >= 0) {
					app_goto_page(app, index);
				}
			}
			if (message.message[0] != '\0') {
				app_notify(app, message.message, !message.action_ok);
			} else if (!message.action_ok) {
				app_notify(app, tr(STR_ACTION_REFUSED), true);
			}
			break;

		case MSG_HELLO_ERROR:
			app_notify(app, message.reason[0] != '\0' ? message.reason
			                                          : tr(STR_OFFLINE),
			           true);
			net_disconnect();
			break;

		case MSG_HELLO_OK:
		case MSG_PONG:
		case MSG_UNKNOWN:
		default:
			break;
		}
	}
}

/** Met à jour l'horloge locale de repli. */
static void update_local_clock(App *app)
{
	const time_t now = time(NULL);
	const struct tm *local = localtime(&now);
	if (local != NULL) {
		snprintf(app->local_time, sizeof(app->local_time), "%02d:%02d",
		         local->tm_hour, local->tm_min);
	}
}

void app_update(App *app, float dt)
{
	app->uptime += dt;
	app->idle_time += dt;
	update_local_clock(app);

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

	/* Reconnexion automatique, sans jamais bloquer le rendu. */
	if (net_state() == NET_IDLE) {
		app->reconnect_in -= dt;
		if (app->reconnect_in <= 0.0f) {
			app->reconnect_in = RECONNECT_DELAY;
			app->hello_sent = false;
			net_connect(app->settings.host, app->settings.port);
		}
	}

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

		if (!app->hold_fired && app->press_time >= HOLD_THRESHOLD &&
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
