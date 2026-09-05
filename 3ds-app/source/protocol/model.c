/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "model.h"

#include <string.h>

void model_config_clear(Config *config)
{
	memset(config, 0, sizeof(*config));
	config->revision = -1;
	config->page_count = 0;
}

void model_state_clear(PcState *state)
{
	memset(state, 0, sizeof(*state));
	state->volume = -1;
	state->app_volume = -1;
	state->cpu = -1;
	state->memory = -1;
	state->memory_used_mb = -1;
	state->memory_total_mb = -1;
	state->disk = -1;
	state->disk_free_mb = -1;
	state->disk_total_mb = -1;
	state->network_down_kbps = -1;
	state->network_up_kbps = -1;
	state->top_process_cpu = -1;
	state->gpu = -1;
	state->temperature = -1;
	state->mic_known = false;
	state->media_present = false;
	state->media_art = 0;
	state->media_accent_known = false;
	state->media_position = -1;
	state->media_duration = -1;
}

/* Table nom -> icône, alignée sur la liste documentée dans PROTOCOL.md. */
static const struct {
	const char *name;
	IconId id;
} kIconNames[] = {
    {"mic", ICON_MIC},
    {"mic-off", ICON_MIC_OFF},
    {"volume-up", ICON_VOLUME_UP},
    {"volume-down", ICON_VOLUME_DOWN},
    {"volume-mute", ICON_VOLUME_MUTE},
    {"play", ICON_PLAY},
    {"pause", ICON_PAUSE},
    {"next", ICON_NEXT},
    {"previous", ICON_PREVIOUS},
    {"app", ICON_APP},
    {"browser", ICON_BROWSER},
    {"terminal", ICON_TERMINAL},
    {"folder", ICON_FOLDER},
    {"music", ICON_MUSIC},
    {"chat", ICON_CHAT},
    {"video", ICON_VIDEO},
    {"record", ICON_RECORD},
    {"lock", ICON_LOCK},
    {"page", ICON_PAGE},
    {"power", ICON_POWER},
    {"gear", ICON_GEAR},
    {"star", ICON_STAR},
};

IconId model_icon_from_name(const char *name)
{
	if (name == NULL || name[0] == '\0') {
		return ICON_NONE;
	}

	const size_t count = sizeof(kIconNames) / sizeof(kIconNames[0]);
	for (size_t i = 0; i < count; i++) {
		if (strcmp(name, kIconNames[i].name) == 0) {
			return kIconNames[i].id;
		}
	}
	return ICON_APP; /* icône générique plutôt qu'un bouton vide */
}

DashboardMode model_dashboard_from_name(const char *name)
{
	if (name == NULL || name[0] == '\0') {
		return DASH_AUTO;
	}
	if (strcmp(name, "media") == 0) {
		return DASH_MEDIA;
	}
	if (strcmp(name, "system") == 0) {
		return DASH_SYSTEM;
	}
	if (strcmp(name, "apps") == 0) {
		return DASH_APPS;
	}
	if (strcmp(name, "audio") == 0) {
		return DASH_AUDIO;
	}
	if (strcmp(name, "frame") == 0) {
		return DASH_FRAME;
	}
	if (strcmp(name, "notifications") == 0) {
		return DASH_NOTIFICATIONS;
	}
	if (strcmp(name, "extension") == 0) {
		return DASH_EXTENSION;
	}
	return DASH_AUTO;
}

const Page *model_page_at(const Config *config, int index)
{
	if (index < 0 || index >= config->page_count) {
		return NULL;
	}
	if (!config->pages[index].used) {
		return NULL;
	}
	return &config->pages[index];
}

int model_find_page(const Config *config, const char *id)
{
	if (id == NULL || id[0] == '\0') {
		return -1;
	}
	for (int i = 0; i < config->page_count; i++) {
		if (config->pages[i].used &&
		    strcmp(config->pages[i].id, id) == 0) {
			return i;
		}
	}
	return -1;
}

bool model_toggle_active(const PcState *state, const char *key)
{
	if (key == NULL || key[0] == '\0') {
		return false;
	}
	if (strcmp(key, "mic_muted") == 0) {
		return state->mic_muted;
	}
	if (strcmp(key, "muted") == 0) {
		return state->muted;
	}
	if (strcmp(key, "playing") == 0) {
		return state->media_playing;
	}
	if (strcmp(key, "media_present") == 0) {
		return state->media_present;
	}
	return false;
}
