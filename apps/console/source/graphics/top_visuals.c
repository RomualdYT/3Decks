/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file top_visuals.c
 * @brief Etat temporel du studio audio, independant du dessin.
 *
 * Le rendu ne calcule pas son propre mouvement. Cette couche conserve les
 * enveloppes entre les frames et garantit ainsi des transitions identiques
 * dans la vue pochette, la page Audio et le mode cadre.
 */

#include "top_visuals.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static unsigned int media_visual_seed(const char *text)
{
	unsigned int hash = 2166136261u;
	if (text == NULL) {
		return hash;
	}
	while (*text != '\0') {
		hash ^= (unsigned char)*text++;
		hash *= 16777619u;
	}
	return hash;
}

static float clamp(float value, float low, float high)
{
	if (value < low) {
		return low;
	}
	if (value > high) {
		return high;
	}
	return value;
}

void top_visuals_init(TopVisualState *visual)
{
	visual->media_reveal = 1.0f;
	visual->last_volume = -1;
	visual->last_app_volume = -1;
	visual->last_media_position = -1;
}

void top_visuals_update(App *app, float dt)
{
	TopVisualState *visual = &app->top_visual;

	if (visual->media_art != app->state.media_art ||
	    strcmp(visual->media_title, app->state.media_title) != 0) {
		visual->media_art = app->state.media_art;
		snprintf(visual->media_title, sizeof(visual->media_title), "%s",
		         app->state.media_title);
		visual->media_seed = media_visual_seed(app->state.media_title);
		visual->media_reveal = 0.0f;
		visual->last_media_position = -1;
	}

	if (visual->media_reveal < 1.0f) {
		visual->media_reveal += dt * 4.2f;
		if (visual->media_reveal > 1.0f) {
			visual->media_reveal = 1.0f;
		}
	}

	/* Extrapole la position entre deux collectes, puis absorbe la derive. */
	if (app->state.media_position < 0 || app->state.media_duration <= 0) {
		visual->last_media_position = -1;
		visual->media_position_display = 0.0f;
	} else {
		if (visual->last_media_position != app->state.media_position) {
			const float measured = (float)app->state.media_position;
			if (visual->last_media_position < 0 ||
			    fabsf(measured - visual->media_position_display) > 2.5f) {
				visual->media_position_display = measured;
			} else {
				visual->media_position_display +=
				    (measured - visual->media_position_display) * 0.18f;
			}
			visual->last_media_position = app->state.media_position;
		}
		if (app->state.media_playing) {
			visual->media_position_display += dt;
		}
		if (visual->media_position_display > (float)app->state.media_duration) {
			visual->media_position_display = (float)app->state.media_duration;
		}
	}

	if (visual->last_volume != app->state.volume) {
		if (visual->last_volume >= 0 && app->state.volume >= 0) {
			visual->system_volume_emphasis = 1.0f;
		}
		visual->last_volume = app->state.volume;
	}
	if (visual->last_app_volume != app->state.app_volume) {
		if (visual->last_app_volume >= 0 && app->state.app_volume >= 0) {
			visual->music_volume_emphasis = 1.0f;
		}
		visual->last_app_volume = app->state.app_volume;
	}
	visual->system_volume_emphasis = clamp(
	    visual->system_volume_emphasis - dt * 0.72f, 0.0f, 1.0f);
	visual->music_volume_emphasis = clamp(
	    visual->music_volume_emphasis - dt * 0.72f, 0.0f, 1.0f);

	const int raw_level = app->state.app_volume >= 0 ? app->state.app_volume
	                                                 : app->state.volume;
	const float level = raw_level > 0 ? (float)raw_level / 100.0f : 0.0f;
	const float beat = 0.5f + 0.5f * sinf(
	    app->uptime * 5.1f + (float)(visual->media_seed & 31u) * 0.11f);
	static const float band_shape[AUDIO_VISUALIZER_BARS] = {
	    1.00f, 0.93f, 0.78f, 0.88f, 0.71f, 0.82f, 0.66f, 0.76f,
	    0.59f, 0.69f, 0.53f, 0.62f, 0.47f, 0.55f, 0.42f, 0.48f,
	};

	for (int i = 0; i < AUDIO_VISUALIZER_BARS; i++) {
		float target;
		if (app->state.muted || level <= 0.001f) {
			target = 0.025f;
		} else if (!app->state.media_playing) {
			target = 0.035f + level * band_shape[i] * 0.12f;
		} else {
			const float phase = (float)i * 1.37f +
			                    (float)((visual->media_seed >> (i % 8)) & 7u) *
			                        0.19f;
			const float wave =
			    0.5f + 0.5f * sinf(app->uptime * (3.35f + 0.13f * (i % 4)) +
			                      phase);
			target = 0.055f + level * band_shape[i] *
			                    (0.24f + wave * 0.50f + beat * 0.22f);
		}

		target = clamp(target, 0.02f, 1.0f);
		const float speed = target > visual->equalizer[i] ? 14.0f : 4.8f;
		visual->equalizer[i] +=
		    (target - visual->equalizer[i]) * clamp(dt * speed, 0.0f, 1.0f);
	}
}
