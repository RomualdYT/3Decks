/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "protocol.h"

#include <stdio.h>
#include <string.h>

#include "json.h"
#include "extension_state.h"

/*
 * Un unique document JSON est réutilisé pour tous les messages entrants. Il
 * pèse plusieurs dizaines de kilooctets, on évite donc de l'empiler sur la
 * pile d'une fonction.
 */
static JsonDoc s_doc;

/** Échappe une chaîne pour l'insérer dans du JSON. */
static void escape_json(const char *src, char *dest, size_t dest_size)
{
	if (dest_size == 0) {
		return;
	}

	size_t out = 0;
	const size_t limit = dest_size - 1;

	for (size_t i = 0; src != NULL && src[i] != '\0' && out < limit; i++) {
		const unsigned char c = (unsigned char)src[i];

		if (c == '"' || c == '\\') {
			if (out + 2 > limit) {
				break;
			}
			dest[out++] = '\\';
			dest[out++] = (char)c;
			continue;
		}

		if (c < 0x20) {
			/* Les caractères de contrôle sont simplement omis. */
			continue;
		}

		dest[out++] = (char)c;
	}

	dest[out] = '\0';
}

static void parse_buttons(const JsonDoc *doc, const JsonToken *array,
                          Page *page)
{
	const int count = json_size(array);

	for (int i = 0; i < count; i++) {
		const JsonToken *item = json_at(doc, array, i);
		if (item == NULL || item->type != JSON_OBJECT) {
			continue;
		}

		/*
		 * Le slot détermine la position dans la grille. Un slot hors bornes est
		 * ignoré plutôt que ramené de force, pour ne pas écraser un autre
		 * bouton légitime.
		 */
		const int slot = json_get_int(doc, item, "slot", i);
		if (slot < 0 || slot >= MAX_BUTTONS) {
			continue;
		}

		Button *button = &page->buttons[slot];
		memset(button, 0, sizeof(*button));

		json_get_string(doc, item, "id", button->id, sizeof(button->id));
		json_get_string(doc, item, "label", button->label, sizeof(button->label));
		json_get_string(doc, item, "hold_label", button->hold_label,
		                sizeof(button->hold_label));
		json_get_string(doc, item, "toggle", button->toggle,
		                sizeof(button->toggle));

		char icon_name[LEN_ICON];
		json_get_string(doc, item, "icon", icon_name, sizeof(icon_name));
		button->icon = model_icon_from_name(icon_name);

		char color[16];
		if (json_get_string(doc, item, "color", color, sizeof(color))) {
			button->color = theme_parse_hex(color, COL_BLUE);
		} else {
			button->color = COL_BLUE;
		}

		/* Un bouton sans identifiant ne pourrait pas être actionné. */
		button->used = button->id[0] != '\0';
	}
}

/** Lit les éléments d'une page en mode liste. */
static void parse_entries(const JsonDoc *doc, const JsonToken *array,
                          Page *page)
{
	const int count = json_size(array);
	int written = 0;

	for (int i = 0; i < count && written < MAX_ENTRIES; i++) {
		const JsonToken *item = json_at(doc, array, i);
		if (item == NULL || item->type != JSON_OBJECT) {
			continue;
		}

		ListEntry *entry = &page->entries[written];
		memset(entry, 0, sizeof(*entry));

		json_get_string(doc, item, "id", entry->id, sizeof(entry->id));
		if (entry->id[0] == '\0') {
			continue; /* sans identifiant, l'élément ne pourrait être actionné */
		}

		json_get_string(doc, item, "label", entry->label, sizeof(entry->label));
		json_get_string(doc, item, "detail", entry->detail,
		                sizeof(entry->detail));

		char icon_name[LEN_ICON];
		json_get_string(doc, item, "icon", icon_name, sizeof(icon_name));
		entry->icon = model_icon_from_name(icon_name);

		char color[16];
		if (json_get_string(doc, item, "color", color, sizeof(color))) {
			entry->color = theme_parse_hex(color, COL_BLUE);
		} else {
			entry->color = COL_BLUE;
		}

		entry->active = json_get_bool(doc, item, "active", false);
		entry->used = true;
		written++;
	}

	page->entry_count = written;
}

static bool parse_config(const JsonDoc *doc, const JsonToken *root,
                         Config *config)
{
	const JsonToken *pages = json_get(doc, root, "pages");
	if (pages == NULL || pages->type != JSON_ARRAY) {
		return false;
	}

	/*
	 * La configuration est volumineuse : plus de cinquante kilooctets depuis
	 * l'ajout des listes, alors que la pile du fil principal n'en offre qu'une
	 * trentaine. La déclarer localement provoquait un débordement de pile, et
	 * donc l'arrêt brutal de l'application dès la réception d'une page en mode
	 * liste.
	 *
	 * Elle est donc allouée statiquement. Ce n'est pas gênant : le décodage est
	 * séquentiel et n'a jamais lieu depuis deux fils à la fois.
	 */
	static Config parsed;

	model_config_clear(&parsed);
	parsed.revision = json_get_int(doc, root, "revision", 0);

	const int total = json_size(pages);
	int written = 0;

	for (int i = 0; i < total && written < MAX_PAGES; i++) {
		const JsonToken *item = json_at(doc, pages, i);
		if (item == NULL || item->type != JSON_OBJECT) {
			continue;
		}

		Page *page = &parsed.pages[written];
		json_get_string(doc, item, "id", page->id, sizeof(page->id));
		if (page->id[0] == '\0') {
			continue; /* une page sans identifiant est inutilisable */
		}

		json_get_string(doc, item, "title", page->title, sizeof(page->title));
		if (page->title[0] == '\0') {
			/*
			 * Repli sur l'identifiant. On copie octet à octet : `page->title` et
			 * `page->id` appartiennent à la même structure, ce qui interdit
			 * l'emploi de snprintf (comportement indéfini si les objets se
			 * recouvrent du point de vue du compilateur).
			 */
			size_t i = 0;
			while (i + 1 < sizeof(page->title) && page->id[i] != '\0') {
				page->title[i] = page->id[i];
				i++;
			}
			page->title[i] = '\0';
		}

		char dash[LEN_ICON];
		json_get_string(doc, item, "dashboard", dash, sizeof(dash));
		page->dashboard = model_dashboard_from_name(dash);
		page->lyrics_lines = json_get_int(doc, item, "lyrics_lines", 3);
		if (page->lyrics_lines < 2 || page->lyrics_lines > 5) page->lyrics_lines = 3;
		char custom_accent[16];
		page->accent_custom = json_get_string(doc, item, "accent", custom_accent, sizeof(custom_accent)) &&
		                      custom_accent[0] == '#' && strlen(custom_accent) == 7;
		if (page->accent_custom) page->accent = theme_parse_hex(custom_accent, COL_ACCENT);

		char page_icon[LEN_ICON];
		json_get_string(doc, item, "icon", page_icon, sizeof(page_icon));
		page->icon = model_icon_from_name(page_icon);

		char layout[LEN_ICON];
		json_get_string(doc, item, "layout", layout, sizeof(layout));
		page->layout =
		    (strcmp(layout, "list") == 0) ? LAYOUT_LIST : LAYOUT_GRID;

		if (page->layout == LAYOUT_LIST) {
			const JsonToken *entries = json_get(doc, item, "entries");
			if (entries != NULL && entries->type == JSON_ARRAY) {
				parse_entries(doc, entries, page);
			}
		} else {
			const JsonToken *buttons = json_get(doc, item, "buttons");
			if (buttons != NULL && buttons->type == JSON_ARRAY) {
				parse_buttons(doc, buttons, page);
			}
		}

		page->used = true;
		written++;
	}

	if (written == 0) {
		return false; /* configuration vide : on garde l'ancienne */
	}

	parsed.page_count = written;
	*config = parsed;
	return true;
}

static void parse_state(const JsonDoc *doc, const JsonToken *root,
                       PcState *state)
{
	/*
	 * `state.update` est un patch : chaque champ absent laisse la valeur
	 * précédente intacte. On teste donc la présence avant d'écrire.
	 */
	const JsonToken *token;

	token = json_get(doc, root, "volume");
	if (token != NULL && token->type == JSON_NUMBER) {
		int volume = json_int(doc, token, state->volume);
		if (volume < 0) {
			volume = 0;
		}
		if (volume > 100) {
			volume = 100;
		}
		state->volume = volume;
	}

	token = json_get(doc, root, "app_volume");
	if (token != NULL && token->type == JSON_NUMBER) {
		int volume = json_int(doc, token, state->app_volume);
		if (volume < 0) {
			volume = 0;
		}
		if (volume > 100) {
			volume = 100;
		}
		state->app_volume = volume;
	}

	token = json_get(doc, root, "muted");
	if (token != NULL && token->type == JSON_BOOL) {
		state->muted = json_bool(doc, token, state->muted);
	}

	token = json_get(doc, root, "mic_muted");
	if (token != NULL && token->type == JSON_BOOL) {
		state->mic_muted = json_bool(doc, token, state->mic_muted);
		state->mic_known = true;
	}

	token = json_get(doc, root, "cpu");
	if (token != NULL && token->type == JSON_NUMBER) {
		state->cpu = json_int(doc, token, state->cpu);
	}

	token = json_get(doc, root, "memory");
	if (token != NULL && token->type == JSON_NUMBER) {
		state->memory = json_int(doc, token, state->memory);
	}

	/*
	 * Mesures enrichies : toutes sont optionnelles afin qu'une console récente
	 * reste compatible avec un agent plus ancien et avec un capteur absent.
	 */
	#define PARSE_PERFORMANCE_INT(json_name, member)                         \
		do {                                                               \
			token = json_get(doc, root, json_name);                        \
			if (token != NULL && token->type == JSON_NUMBER) {             \
				state->member = json_int(doc, token, state->member);       \
			}                                                              \
		} while (0)

	PARSE_PERFORMANCE_INT("memory_used_mb", memory_used_mb);
	PARSE_PERFORMANCE_INT("memory_total_mb", memory_total_mb);
	PARSE_PERFORMANCE_INT("disk", disk);
	PARSE_PERFORMANCE_INT("disk_free_mb", disk_free_mb);
	PARSE_PERFORMANCE_INT("disk_total_mb", disk_total_mb);
	PARSE_PERFORMANCE_INT("network_down_kbps", network_down_kbps);
	PARSE_PERFORMANCE_INT("network_up_kbps", network_up_kbps);
	PARSE_PERFORMANCE_INT("top_process_cpu", top_process_cpu);
	PARSE_PERFORMANCE_INT("gpu", gpu);
	PARSE_PERFORMANCE_INT("temperature", temperature);

	#undef PARSE_PERFORMANCE_INT

	token = json_get(doc, root, "top_process");
	if (token != NULL && token->type == JSON_STRING) {
		json_copy_string(doc, token, state->top_process,
		                 sizeof(state->top_process));
	}

	token = json_get(doc, root, "active_app");
	if (token != NULL && token->type == JSON_STRING) {
		json_copy_string(doc, token, state->active_app,
		                 sizeof(state->active_app));
	}

	token = json_get(doc, root, "host");
	if (token != NULL && token->type == JSON_STRING) {
		json_copy_string(doc, token, state->host, sizeof(state->host));
	}

	token = json_get(doc, root, "time");
	if (token != NULL && token->type == JSON_STRING) {
		json_copy_string(doc, token, state->time, sizeof(state->time));
	}

	token = json_get(doc, root, "date");
	if (token != NULL && token->type == JSON_STRING) {
		json_copy_string(doc, token, state->date, sizeof(state->date));
	}

	token = json_get(doc, root, "notifications");
	if (token != NULL && token->type == JSON_ARRAY) {
		const int count = json_size(token);
		int written = 0;

		for (int i = 0; i < count && written < MAX_NOTIFICATIONS; i++) {
			const JsonToken *item = json_at(doc, token, i);
			if (item == NULL || item->type != JSON_OBJECT) {
				continue;
			}

			json_get_string(doc, item, "app", state->notifications[written].app,
			                sizeof(state->notifications[written].app));
			json_get_string(doc, item, "title",
			                state->notifications[written].title,
			                sizeof(state->notifications[written].title));
			json_get_string(doc, item, "body",
			                state->notifications[written].body,
			                sizeof(state->notifications[written].body));

			char icon_name[LEN_ICON];
			json_get_string(doc, item, "icon", icon_name, sizeof(icon_name));
			state->notifications[written].icon =
			    model_icon_from_name(icon_name);

			state->notifications[written].age =
			    json_get_int(doc, item, "age", 0);

			if (state->notifications[written].title[0] != '\0') {
				written++;
			}
		}

		state->notification_count = written;
	}

	token = json_get(doc, root, "notification_count");
	if (token != NULL && token->type == JSON_NUMBER) {
		state->notification_total = json_int(doc, token, 0);
	}

	token = json_get(doc, root, "audio_output");
	if (token != NULL && token->type == JSON_STRING) {
		json_copy_string(doc, token, state->audio_output,
		                 sizeof(state->audio_output));
	}

	token = json_get(doc, root, "audio_outputs");
	if (token != NULL && token->type == JSON_ARRAY) {
		const int count = json_size(token);
		int written = 0;
		for (int i = 0; i < count && written < MAX_OUTPUTS; i++) {
			const JsonToken *item = json_at(doc, token, i);
			if (item == NULL || item->type != JSON_STRING) {
				continue;
			}
			if (json_copy_string(doc, item, state->audio_outputs[written],
			                     sizeof(state->audio_outputs[written])) &&
			    state->audio_outputs[written][0] != '\0') {
				written++;
			}
		}
		state->audio_output_count = written;
	}

	token = json_get(doc, root, "apps");
	if (token != NULL && token->type == JSON_ARRAY) {
		const int count = json_size(token);
		int written = 0;
		for (int i = 0; i < count && written < MAX_APPS; i++) {
			const JsonToken *item = json_at(doc, token, i);
			if (item == NULL || item->type != JSON_STRING) {
				continue;
			}
			if (json_copy_string(doc, item, state->apps[written],
			                     sizeof(state->apps[written]))) {
				if (state->apps[written][0] != '\0') {
					written++;
				}
			}
		}
		state->app_count = written;
	}

	token = json_get(doc, root, "media");
	if (token != NULL && token->type == JSON_OBJECT) {
		char previous_title[LEN_TEXT];
		char previous_artist[LEN_TEXT];
		memcpy(previous_title, state->media_title, sizeof(previous_title));
		memcpy(previous_artist, state->media_artist, sizeof(previous_artist));
		json_get_string(doc, token, "title", state->media_title,
		                sizeof(state->media_title));
		json_get_string(doc, token, "artist", state->media_artist,
		                sizeof(state->media_artist));
		if (strcmp(previous_title, state->media_title) != 0 ||
		    strcmp(previous_artist, state->media_artist) != 0) {
			state->lyrics_count = 0;
			strcpy(state->lyrics_status, "loading");
		}
		json_get_string(doc, token, "album", state->media_album,
		                sizeof(state->media_album));
		json_get_string(doc, token, "app", state->media_app,
		                sizeof(state->media_app));
		state->media_playing = json_get_bool(doc, token, "playing", false);
		state->media_seekable = json_get_bool(doc, token, "seekable", false);
		state->media_present = state->media_title[0] != '\0';

		state->media_art = (u32)json_get_int(doc, token, "art", 0);

		/*
		 * Couleur dominante de la pochette : elle sert d'accent au mode cadre,
		 * ce qui accorde l'interface au morceau écouté.
		 */
		char accent[16];
		if (json_get_string(doc, token, "accent", accent, sizeof(accent)) &&
		    accent[0] != '\0') {
			state->media_accent = theme_parse_hex(accent, COL_ACCENT);
			state->media_accent_known = true;
		} else {
			state->media_accent_known = false;
		}

		/*
		 * Position et durée sont facultatives : tous les lecteurs ne les
		 * exposent pas. La valeur -1 signale l'absence d'information et évite
		 * d'afficher une progression trompeuse.
		 */
		state->media_duration = json_get_int(doc, token, "duration", -1);
		state->media_position = json_get_int(doc, token, "position", -1);

		if (state->media_duration <= 0) {
			state->media_duration = -1;
			state->media_position = -1;
		} else if (state->media_position > state->media_duration) {
			state->media_position = state->media_duration;
		}
	} else if (token != NULL && token->type == JSON_NULL) {
		/* `null` signifie explicitement « plus rien ne joue ». */
		state->media_title[0] = '\0';
		state->media_artist[0] = '\0';
		state->media_album[0] = '\0';
		state->media_app[0] = '\0';
		state->media_playing = false;
		state->media_seekable = false;
		state->media_present = false;
		state->media_art = 0;
		state->media_accent_known = false;
		state->media_position = -1;
		state->media_duration = -1;
		state->lyrics_count = 0;
		strcpy(state->lyrics_status, "idle");
	}
}

bool protocol_decode(const char *json, size_t length, IncomingMessage *out,
                     Config *config, PcState *state)
{
	memset(out, 0, sizeof(*out));
	out->kind = MSG_UNKNOWN;
	out->action_id = -1;

	if (!json_parse(&s_doc, json, length)) {
		return false;
	}

	const JsonToken *root = json_root(&s_doc);
	if (root == NULL || root->type != JSON_OBJECT) {
		return false;
	}

	char type[32];
	if (!json_get_string(&s_doc, root, "type", type, sizeof(type))) {
		return false;
	}

	if (strcmp(type, "hello.ok") == 0) {
		out->kind = MSG_HELLO_OK;
		json_get_string(&s_doc, root, "host", state->host, sizeof(state->host));
		json_get_string(&s_doc, root, "token", out->paired_token,
		                sizeof(out->paired_token));
		return true;
	}

	if (strcmp(type, "hello.error") == 0) {
		out->kind = MSG_HELLO_ERROR;
		json_get_string(&s_doc, root, "reason", out->reason,
		                sizeof(out->reason));
		char code[32];
		json_get_string(&s_doc, root, "code", code, sizeof(code));
		out->pairing_required = strcmp(code, "pairing_required") == 0;
		return true;
	}

	if (strcmp(type, "config.snapshot") == 0) {
		out->kind = MSG_CONFIG_SNAPSHOT;
		return parse_config(&s_doc, root, config);
	}

	if (strcmp(type, "state.update") == 0) {
		out->kind = MSG_STATE_UPDATE;
		parse_state(&s_doc, root, state);
		extension_state_parse(&s_doc, root, state);

		/*
		 * Une notification venant d'arriver est signalée à part : la console
		 * l'annonce, quelle que soit la page affichée.
		 */
		const JsonToken *fresh = json_get(&s_doc, root, "notification_new");
		if (fresh != NULL && fresh->type == JSON_OBJECT) {
			json_get_string(&s_doc, fresh, "app", out->notification_app,
			                sizeof(out->notification_app));
			json_get_string(&s_doc, fresh, "title", out->notification_title,
			                sizeof(out->notification_title));

			char icon_name[LEN_ICON];
			json_get_string(&s_doc, fresh, "icon", icon_name,
			                sizeof(icon_name));
			out->notification_icon = model_icon_from_name(icon_name);

			out->has_notification = out->notification_title[0] != '\0';
		}

		return true;
	}

	if (strcmp(type, "media.lyrics") == 0) {
		out->kind = MSG_MEDIA_LYRICS;
		char track[LEN_TEXT];
		char artist[LEN_TEXT];
		json_get_string(&s_doc, root, "track", track, sizeof(track));
		json_get_string(&s_doc, root, "artist", artist, sizeof(artist));
		if (track[0] != '\0' &&
		    (strcmp(track, state->media_title) != 0 ||
		     strcmp(artist, state->media_artist) != 0)) {
			return true; /* réponse d'une piste précédente */
		}
		json_get_string(&s_doc, root, "status", state->lyrics_status,
		                sizeof(state->lyrics_status));
		state->lyrics_count = 0;
		const JsonToken *lines = json_get(&s_doc, root, "lines");
		if (lines != NULL && lines->type == JSON_ARRAY) {
			const int count = json_size(lines);
			for (int i = 0; i < count && state->lyrics_count < MAX_LYRIC_LINES; i++) {
				const JsonToken *line = json_at(&s_doc, lines, i);
				if (line == NULL || line->type != JSON_OBJECT) continue;
				const int time_ms = json_get_int(&s_doc, line, "t", -1);
				if (time_ms < 0) continue;
				LyricLine *dest = &state->lyrics[state->lyrics_count];
				if (!json_get_string(&s_doc, line, "text", dest->text,
				                     sizeof(dest->text)) || dest->text[0] == '\0') continue;
				dest->time_ms = (u32)time_ms;
				state->lyrics_count++;
			}
		}
		return true;
	}

	if (strcmp(type, "action.result") == 0) {
		out->kind = MSG_ACTION_RESULT;
		out->action_id = json_get_int(&s_doc, root, "id", -1);
		out->action_ok = json_get_bool(&s_doc, root, "ok", false);
		json_get_string(&s_doc, root, "message", out->message,
		                sizeof(out->message));
		json_get_string(&s_doc, root, "open_page", out->open_page,
		                sizeof(out->open_page));
		out->open_settings = json_get_bool(&s_doc, root, "open_settings", false);
		out->open_modal = json_get_bool(&s_doc, root, "open_modal", false);
		out->toggle_frame = json_get_bool(&s_doc, root, "toggle_frame", false);
		return true;
	}

	if (strcmp(type, "pong") == 0) {
		out->kind = MSG_PONG;
		out->ping_id = json_get_int(&s_doc, root, "id", -1);
		return true;
	}

	/* Type inconnu : on l'ignore sans considérer le message comme corrompu. */
	out->kind = MSG_UNKNOWN;
	return true;
}

bool protocol_decode_discovery(const char *json, size_t length,
                               AgentAnnouncement *out)
{
	if (out == NULL) {
		return false;
	}
	memset(out, 0, sizeof(*out));

	if (!json_parse(&s_doc, json, length)) {
		return false;
	}
	const JsonToken *root = json_root(&s_doc);
	if (root == NULL || root->type != JSON_OBJECT) {
		return false;
	}

	char type[32];
	if (!json_get_string(&s_doc, root, "type", type, sizeof(type)) ||
	    strcmp(type, "deck3ds.agent") != 0) {
		return false;
	}
	if (json_get_int(&s_doc, root, "protocol", -1) != PROTOCOL_VERSION) {
		return false;
	}

	json_get_string(&s_doc, root, "name", out->name, sizeof(out->name));
	json_get_string(&s_doc, root, "platform", out->platform,
	                sizeof(out->platform));
	out->port = json_get_int(&s_doc, root, "port", 0);
	out->pairing_required =
	    json_get_bool(&s_doc, root, "pairing_required", false);

	return out->name[0] != '\0' && out->port > 0 && out->port < 65536;
}

int protocol_encode_hello(char *dest, size_t dest_size, const char *device,
                          const char *token, const char *pair_code,
                          const char *language)
{
	char safe_device[32];
	char safe_token[64];
	char safe_pair_code[16];
	char safe_language[8];
	escape_json(device, safe_device, sizeof(safe_device));
	escape_json(token, safe_token, sizeof(safe_token));
	escape_json(pair_code, safe_pair_code, sizeof(safe_pair_code));
	escape_json(language, safe_language, sizeof(safe_language));

	/*
	 * La langue est transmise afin que les notifications renvoyées par
	 * l'ordinateur soient rédigées dans la langue choisie sur la console.
	 */
	if (safe_pair_code[0] != '\0') {
		return snprintf(dest, dest_size,
		                "{\"type\":\"hello\",\"protocol\":%d,\"device\":\"%s\""
		                ",\"pair_code\":\"%s\",\"language\":\"%s\"}",
		                PROTOCOL_VERSION, safe_device, safe_pair_code,
		                safe_language);
	}

	if (safe_token[0] == '\0') {
		return snprintf(dest, dest_size,
		                "{\"type\":\"hello\",\"protocol\":%d,\"device\":\"%s\""
		                ",\"language\":\"%s\"}",
		                PROTOCOL_VERSION, safe_device, safe_language);
	}

	return snprintf(dest, dest_size,
	                "{\"type\":\"hello\",\"protocol\":%d,\"device\":\"%s\""
	                ",\"token\":\"%s\",\"language\":\"%s\"}",
	                PROTOCOL_VERSION, safe_device, safe_token, safe_language);
}

int protocol_encode_button(char *dest, size_t dest_size, int id,
                           const char *page, const char *button, bool hold)
{
	char safe_page[LEN_ID * 2];
	char safe_button[LEN_ID * 2];
	escape_json(page, safe_page, sizeof(safe_page));
	escape_json(button, safe_button, sizeof(safe_button));

	return snprintf(dest, dest_size,
	                "{\"type\":\"button.press\",\"id\":%d,\"page\":\"%s\","
	                "\"button\":\"%s\",\"hold\":%s}",
	                id, safe_page, safe_button, hold ? "true" : "false");
}

int protocol_encode_config_request(char *dest, size_t dest_size, int id)
{
	return snprintf(dest, dest_size,
	                "{\"type\":\"config.request\",\"id\":%d}", id);
}

int protocol_encode_ping(char *dest, size_t dest_size, int id)
{
	return snprintf(dest, dest_size, "{\"type\":\"ping\",\"id\":%d}", id);
}

int protocol_encode_value(char *dest, size_t dest_size, int id,
                          const char *target, int value)
{
	char safe_target[32];
	escape_json(target, safe_target, sizeof(safe_target));

	return snprintf(dest, dest_size,
	                "{\"type\":\"value.set\",\"id\":%d,\"target\":\"%s\""
	                ",\"value\":%d}",
	                id, safe_target, value);
}
