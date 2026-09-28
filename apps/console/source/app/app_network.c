/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file app_network.c
 * @brief Connexion, handshake, heartbeat et traitement des messages.
 *
 * Toute la liaison reste incrementale : aucun appel ne doit retenir la boucle
 * de rendu. Les decisions d'interface sont exprimees par les drapeaux de `App`
 * et traitees ensuite par `main.c`.
 */

#include "app_network.h"

#include <3ds.h>
#include <stdio.h>
#include <string.h>

#include "app_feedback.h"
#include "artwork.h"
#include "i18n.h"
#include "protocol.h"
#include "sound.h"
#include "monotonic.h"
#include "network_policy.h"

static char s_rx_message[NET_MAX_MESSAGE + 1];

static void schedule_reconnect(App *app)
{
	app->reconnect_in = (float)network_retry_delay(app->reconnect_attempt);
	app->reconnect_at = monotonic_seconds() + app->reconnect_in;
	if (app->reconnect_attempt < 4) {
		app->reconnect_attempt++;
	}
}

static void remember_network_error(App *app)
{
	snprintf(app->link_error_detail, sizeof(app->link_error_detail), "%s",
	         net_last_error());

	const char *friendly = tr(STR_NETWORK_UNAVAILABLE);
	switch (net_last_error_kind()) {
	case NET_ERROR_UNREACHABLE:
		friendly = tr(STR_AGENT_UNAVAILABLE);
		break;
	case NET_ERROR_LOST:
		friendly = tr(STR_CONNECTION_LOST);
		break;
	case NET_ERROR_NONE:
	case NET_ERROR_UNAVAILABLE:
	case NET_ERROR_ENDPOINT:
	case NET_ERROR_PROTOCOL:
		break;
	}
	snprintf(app->link_error, sizeof(app->link_error), "%s", friendly);
}

static const char *detect_device_model(void)
{
	static const char *s_device_model = NULL;
	if (s_device_model != NULL) {
		return s_device_model;
	}

	u8 model = 0;
	if (R_SUCCEEDED(cfguInit())) {
		const Result res = CFGU_GetSystemModel(&model);
		cfguExit();
		if (R_SUCCEEDED(res)) {
			switch (model) {
			case CFG_MODEL_3DS:
				s_device_model = "3ds";
				return s_device_model;
			case CFG_MODEL_3DSXL:
				s_device_model = "3ds_xl";
				return s_device_model;
			case CFG_MODEL_N3DS:
				s_device_model = "new_3ds";
				return s_device_model;
			case CFG_MODEL_2DS:
				s_device_model = "2ds";
				return s_device_model;
			case CFG_MODEL_N3DSXL:
				s_device_model = "new_3ds_xl";
				return s_device_model;
			case CFG_MODEL_N2DSXL:
				s_device_model = "new_2ds_xl";
				return s_device_model;
			default:
				break;
			}
		}
	}

	s_device_model = "3ds";
	return s_device_model;
}

static void send_hello(App *app)
{
	char payload[192];
	const int written = protocol_encode_hello(
	    payload, sizeof(payload), detect_device_model(), app->settings.token,
	    app->pair_code, i18n_language() == LANG_FR ? "fr" : "en");
	if (written > 0 && (size_t)written < sizeof(payload) &&
	    net_send(payload, (size_t)written)) {
		app->hello_sent = true;
		app->hello_deadline = monotonic_seconds() + HELLO_TIMEOUT_SECONDS;
	}
}

void app_force_reconnect(App *app)
{
	net_disconnect();
	app->link = LINK_OFFLINE;
	app->hello_sent = false;
	app->handshake_ok = false;
	app->config_received = false;
	app->pending_ping_id = -1;
	app->reconnect_attempt = 0;
	app->reconnect_in = 0.0f;
	app->reconnect_at = monotonic_seconds();
}

static void handle_config(App *app)
{
	const bool first_config = !app->config_received;
	const bool layout_changed = app->config.page_count != app->last_page_count;
	app->config_received = true;
	app->last_page_count = app->config.page_count;
	if (app->current_page >= app->config.page_count) {
		app->current_page = 0;
	}
	if (first_config || layout_changed) {
		app->page_fade = 0.0f;
		app->enter_anim = 0.0f;
	}
}

static void handle_notification(App *app, const IncomingMessage *message)
{
	if (!message->has_notification) {
		return;
	}
	char text[LEN_TEXT];
	if (message->notification_app[0] != '\0') {
		snprintf(text, sizeof(text), "%.16s : %.40s", message->notification_app,
		         message->notification_title);
	} else {
		snprintf(text, sizeof(text), "%s", message->notification_title);
	}
	app_notify(app, text, false);
	app->toast.icon = message->notification_icon;
	sound_play(SOUND_CONNECT);
	app->alert_glow = 1.0f;
}

static void handle_action_result(App *app, const IncomingMessage *message)
{
	app_feedback_finish(app, message->action_id, message->action_ok);
	app->settings_requested |= message->open_settings;
	app->modal_requested |= message->open_modal;
	app->frame_requested |= message->toggle_frame;

	if (message->open_page[0] != '\0') {
		const int index = model_find_page(&app->config, message->open_page);
		if (index >= 0) {
			app_goto_page(app, index);
		}
	}
	if (message->message[0] != '\0') {
		app_notify(app, message->message, !message->action_ok);
	} else if (!message->action_ok) {
		app_notify(app, tr(STR_ACTION_REFUSED), true);
	}
}

static void handle_hello_error(App *app, const IncomingMessage *message)
{
	if (message->pairing_required) {
		app->pairing_requested = true;
		app_notify(app, tr(STR_PAIRING_REQUIRED), false);
	} else {
		app_notify(app,
		           message->reason[0] != '\0' ? message->reason : tr(STR_OFFLINE),
		           true);
	}
	net_disconnect();
	app->link = LINK_OFFLINE;
	app->hello_sent = false;
	app->handshake_ok = false;
	app->reconnect_in = message->pairing_required ? 30.0f : 2.0f;
	app->reconnect_at = monotonic_seconds() + app->reconnect_in;
}

static void handle_hello_ok(App *app, const IncomingMessage *message)
{
	const bool was_online = app->handshake_ok;
	app->handshake_ok = true;
	app->link = LINK_ONLINE;
	app->reconnect_attempt = 0;
	app->link_error[0] = '\0';
	app->link_error_detail[0] = '\0';
	app->next_ping_at = monotonic_seconds() + HEARTBEAT_INTERVAL_SECONDS;
	app->pending_ping_id = -1;
	if (!was_online) {
		sound_play(SOUND_CONNECT);
	}
	if (message->paired_token[0] != '\0') {
		snprintf(app->settings.token, sizeof(app->settings.token), "%s",
		         message->paired_token);
		app->pair_code[0] = '\0';
		app_save_settings(app);
		app_notify(app, tr(STR_PAIRING_SAVED), false);
	}
}

static void handle_message(App *app, const IncomingMessage *message)
{
	switch (message->kind) {
	case MSG_CONFIG_SNAPSHOT:
		handle_config(app);
		break;
	case MSG_STATE_UPDATE:
		handle_notification(app, message);
		break;
	case MSG_ACTION_RESULT:
		handle_action_result(app, message);
		break;
	case MSG_HELLO_ERROR:
		handle_hello_error(app, message);
		break;
	case MSG_HELLO_OK:
		handle_hello_ok(app, message);
		break;
	case MSG_PONG:
		if (message->ping_id == app->pending_ping_id) {
			app->pending_ping_id = -1;
		}
		break;
	case MSG_UNKNOWN:
	default:
		break;
	}
}

static void check_heartbeat(App *app)
{
	if ((!app->handshake_ok && app->hello_sent &&
	     deadline_reached(monotonic_seconds(), app->hello_deadline)) ||
	    (app->handshake_ok &&
	     monotonic_seconds() - app->last_rx_at >= HEARTBEAT_TIMEOUT_SECONDS)) {
		snprintf(app->link_error_detail, sizeof(app->link_error_detail),
		         "%s",
		         app->handshake_ok ? "heartbeat timeout" : "hello timeout");
		snprintf(app->link_error, sizeof(app->link_error), "%s",
		         tr(STR_CONNECTION_STALE));
		net_disconnect();
		app->link = LINK_OFFLINE;
		app->hello_sent = false;
		app->handshake_ok = false;
		app->config_received = false;
		app->pending_ping_id = -1;
		schedule_reconnect(app);
		return;
	}

	if (app->handshake_ok && monotonic_seconds() >= app->next_ping_at) {
		char payload[64];
		const int ping_id = app->next_request_id++;
		const int written = protocol_encode_ping(payload, sizeof(payload), ping_id);
		if (written > 0 && (size_t)written < sizeof(payload) &&
		    net_send(payload, (size_t)written)) {
			app->pending_ping_id = ping_id;
		}
		app->next_ping_at = monotonic_seconds() + HEARTBEAT_INTERVAL_SECONDS;
	}
}

void app_pump_network(App *app)
{
	net_poll();
	const NetState state = net_state();
	switch (state) {
	case NET_IDLE:
		if (app->link != LINK_OFFLINE || app->hello_sent || app->handshake_ok) {
			app->link = LINK_OFFLINE;
			app->hello_sent = false;
			app->handshake_ok = false;
			app->config_received = false;
			app->pending_ping_id = -1;
			remember_network_error(app);
			schedule_reconnect(app);
		}
		break;
	case NET_CONNECTING:
		app->link = LINK_CONNECTING;
		break;
	case NET_CONNECTED:
		if (!app->hello_sent) {
			send_hello(app);
		}
		app->link = app->handshake_ok ? LINK_ONLINE : LINK_CONNECTING;
		break;
	}

	if (state != NET_CONNECTED) {
		return;
	}
	for (int budget = 0; budget < 8; budget++) {
		size_t length = 0;
		if (!net_receive(s_rx_message, sizeof(s_rx_message), &length)) {
			break;
		}
		if (artwork_consume(s_rx_message, length)) {
			app->last_rx_at = monotonic_seconds();
			continue;
		}

		IncomingMessage message;
		if (!protocol_decode(s_rx_message, length, &message, &app->config,
		                     &app->state)) {
			continue;
		}
		app->last_rx_at = monotonic_seconds();
		handle_message(app, &message);
		if (net_state() != NET_CONNECTED) break;
	}
	if (net_state() == NET_CONNECTED) check_heartbeat(app);
}

void app_network_update(App *app)
{
	if (net_state() != NET_IDLE) {
		return;
	}
	app->reconnect_in = (float)(app->reconnect_at - monotonic_seconds());
	if (app->reconnect_in > 0.0f) {
		return;
	}
	if (app->settings.host[0] == '\0') {
		app->reconnect_in = 1.0f;
		app->reconnect_at = monotonic_seconds() + 1.0;
		return;
	}

	app->hello_sent = false;
	app->handshake_ok = false;
	if (net_connect(app->settings.host, app->settings.port)) {
		app->link = LINK_CONNECTING;
	} else {
		remember_network_error(app);
		schedule_reconnect(app);
	}
}
