/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file ui_top_media.c
 * @brief Studio audio de l'ecran superieur.
 *
 * Les vues media, audio et cadre partagent ici couleurs, identites de lecteur,
 * progression et egaliseur. Ce regroupement garde `ui_top.c` centre sur la
 * navigation generale et evite trois implementations visuelles divergentes.
 */

#include "ui_top_media.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "artwork.h"
#include "draw.h"
#include "i18n.h"
#include "icons.h"
#include "text.h"
#include "theme.h"

#define TOP_HEADER_H 30.0f
#define AUDIO_DOCK_H 46.0f
#define TOP_PAD 12.0f

typedef enum {
	MEDIA_BRAND_GENERIC = 0,
	MEDIA_BRAND_SPOTIFY,
	MEDIA_BRAND_APPLE_MUSIC,
} MediaBrand;

static float clamp01(float value)
{
	if (value < 0.0f) {
		return 0.0f;
	}
	if (value > 1.0f) {
		return 1.0f;
	}
	return value;
}

static float ease_out_cubic(float value)
{
	const float inverse = 1.0f - clamp01(value);
	return 1.0f - inverse * inverse * inverse;
}

static char ascii_lower(char value)
{
	if (value >= 'A' && value <= 'Z') {
		return (char)(value + ('a' - 'A'));
	}
	return value;
}

static bool contains_ascii_ci(const char *text, const char *needle)
{
	if (text == NULL || needle == NULL || needle[0] == '\0') {
		return false;
	}

	for (const char *start = text; *start != '\0'; start++) {
		const char *left = start;
		const char *right = needle;
		while (*left != '\0' && *right != '\0' &&
		       ascii_lower(*left) == ascii_lower(*right)) {
			left++;
			right++;
		}
		if (*right == '\0') {
			return true;
		}
	}
	return false;
}

static MediaBrand detect_media_brand(const App *app)
{
	if (contains_ascii_ci(app->state.media_app, "spotify")) {
		return MEDIA_BRAND_SPOTIFY;
	}
	if (contains_ascii_ci(app->state.media_app, "apple") ||
	    contains_ascii_ci(app->state.media_app, "music")) {
		return MEDIA_BRAND_APPLE_MUSIC;
	}
	return MEDIA_BRAND_GENERIC;
}

static u32 media_accent(const App *app)
{
	if (app->state.media_accent_known) {
		return theme_mix(app->state.media_accent, COL_WHITE, 0.14f);
	}
	if (detect_media_brand(app) == MEDIA_BRAND_APPLE_MUSIC) {
		return C2D_Color32(0xFA, 0x3D, 0x58, 0xFF);
	}
	if (detect_media_brand(app) == MEDIA_BRAND_SPOTIFY) {
		return C2D_Color32(0x1E, 0xD7, 0x60, 0xFF);
	}
	return COL_ACCENT;
}

static void draw_spotify_wave(float cx, float cy, float size, float thickness,
	                              float z, u32 color)
{
	/* Quatre points forment une courbe stable, plus propre qu'un arc circulaire. */
	const float x0 = cx - size * 0.34f;
	const float x1 = cx - size * 0.12f;
	const float x2 = cx + size * 0.12f;
	const float x3 = cx + size * 0.34f;
	draw_line(x0, cy + size * 0.04f, x1, cy - size * 0.04f, thickness, z,
	          color);
	draw_line(x1, cy - size * 0.04f, x2, cy - size * 0.02f, thickness, z,
	          color);
	draw_line(x2, cy - size * 0.02f, x3, cy + size * 0.08f, thickness, z,
	          color);
}

/** Marques dessinees en vecteurs, sans texture supplementaire. */
static void draw_media_brand_mark(MediaBrand brand, float cx, float cy,
	                                  float size, float z)
{
	if (brand == MEDIA_BRAND_SPOTIFY) {
		const u32 green = C2D_Color32(0x1E, 0xD7, 0x60, 0xFF);
		const u32 ink = C2D_Color32(0x07, 0x13, 0x0B, 0xFF);
		draw_circle(cx, cy, size * 0.5f, z, green);
		draw_spotify_wave(cx, cy - size * 0.17f, size, size * 0.075f,
		                  z + 0.01f, ink);
		draw_spotify_wave(cx, cy + size * 0.02f, size * 0.88f,
		                  size * 0.065f, z + 0.01f, ink);
		draw_spotify_wave(cx, cy + size * 0.20f, size * 0.72f,
		                  size * 0.055f, z + 0.01f, ink);
		return;
	}

	if (brand == MEDIA_BRAND_APPLE_MUSIC) {
		const u32 pink = C2D_Color32(0xFA, 0x2D, 0x55, 0xFF);
		const u32 coral = C2D_Color32(0xFF, 0x6B, 0x61, 0xFF);
		draw_round_rect_vgrad(cx - size * 0.5f, cy - size * 0.5f, size, size,
		                      size * 0.24f, z, coral, pink);
		const float note = size * 0.085f;
		draw_circle(cx - size * 0.13f, cy + size * 0.20f, note, z + 0.01f,
		            COL_WHITE);
		draw_circle(cx + size * 0.22f, cy + size * 0.10f, note, z + 0.01f,
		            COL_WHITE);
		draw_line(cx - size * 0.05f, cy + size * 0.18f,
		          cx - size * 0.05f, cy - size * 0.25f, size * 0.065f,
		          z + 0.01f, COL_WHITE);
		draw_line(cx + size * 0.30f, cy + size * 0.08f,
		          cx + size * 0.30f, cy - size * 0.34f, size * 0.065f,
		          z + 0.01f, COL_WHITE);
		draw_line(cx - size * 0.05f, cy - size * 0.25f,
		          cx + size * 0.30f, cy - size * 0.34f, size * 0.085f,
		          z + 0.01f, COL_WHITE);
		return;
	}

	draw_circle(cx, cy, size * 0.5f, z, theme_alpha(COL_SURFACE_HI, 0xEE));
	icons_draw(ICON_MUSIC, cx, cy, size * 0.58f, z + 0.01f, COL_ACCENT);
}

static void draw_media_brand_badge(const App *app, float x, float y,
	                                   float max_width, float z)
{
	const char *label = app->state.media_app[0] != '\0'
	                        ? app->state.media_app
	                        : tr(STR_MUSIC);
	float width = text_width(label, TEXT_MICRO) + 29.0f;
	if (width > max_width) {
		width = max_width;
	}

	draw_round_rect(x, y, width, 18.0f, 9.0f, z,
	                theme_alpha(COL_BG, 0xA6));
	draw_media_brand_mark(detect_media_brand(app), x + 10.0f, y + 9.0f, 14.0f,
	                      z + 0.01f);
	text_draw_clipped(x + 20.0f, y + 2.5f, z + 0.01f, TEXT_MICRO,
	                  COL_TEXT_DIM, ALIGN_LEFT, width - 25.0f, label);
}

static void draw_luminous_progress(float x, float y, float w, float h,
	                                   float ratio, float z, u32 color)
{
	ratio = clamp01(ratio);
	draw_progress(x, y, w, h, ratio, z,
	              theme_alpha(COL_SURFACE_HI, 0xE6), color);
	if (ratio > 0.002f) {
		const float cx = x + h * 0.5f + (w - h) * ratio;
		draw_circle(cx, y + h * 0.5f, h * 1.05f, z,
		            theme_alpha(color, 0x32));
		draw_circle(cx, y + h * 0.5f, h * 0.54f, z + 0.01f,
		            theme_mix(color, COL_WHITE, 0.32f));
	}
}

static int display_position(const App *app)
{
	int position = (int)floorf(app->top_visual.media_position_display);
	if (position < 0) {
		position = 0;
	}
	if (app->state.media_duration > 0 && position > app->state.media_duration) {
		position = app->state.media_duration;
	}
	return position;
}

static void format_media_time(int seconds, char *dest, size_t size)
{
	if (seconds < 0) {
		seconds = 0;
	}
	snprintf(dest, size, "%u:%02u", (unsigned)(seconds / 60) % 100u,
	         (unsigned)seconds % 60u);
}

static void draw_equalizer(const App *app, float x, float y, float w, float h,
	                           u32 color)
{
	const float gap = h < 24.0f ? 2.2f : 3.0f;
	const float bar_w =
	    (w - gap * (float)(AUDIO_VISUALIZER_BARS - 1)) /
	    (float)AUDIO_VISUALIZER_BARS;

	draw_round_rect(x, y + h - 2.0f, w, 2.0f, 1.0f, Z_CONTENT,
	                theme_alpha(color, 0x20));
	for (int i = 0; i < AUDIO_VISUALIZER_BARS; i++) {
		const float amount = clamp01(app->top_visual.equalizer[i]);
		float bar_h = h * amount;
		if (bar_h < 2.0f) {
			bar_h = 2.0f;
		}
		const float bx = x + (float)i * (bar_w + gap);
		const float by = y + h - bar_h;
		draw_round_rect_vgrad(bx, by, bar_w, bar_h, bar_w * 0.46f, Z_OVERLAY,
		                      theme_mix(color, COL_WHITE, 0.38f),
		                      theme_alpha(color, 0xD8));
	}
}

static void draw_artwork(float x, float y, float size, float reveal, u32 accent,
	                         float z)
{
	const u8 alpha = (u8)(0x38 + reveal * 0xC7);
	draw_round_rect(x - 5.0f, y - 5.0f, size + 10.0f, size + 10.0f, 12.0f,
	                z - 0.10f, theme_alpha(accent, 0x20));
	draw_shadow(x, y, size, size, 9.0f, z - 0.10f);

	if (artwork_available()) {
		artwork_draw(x, y, size, z, alpha);
		draw_round_rect_outline(x, y, size, size, 6.0f, 1.0f, z + 0.10f,
		                        theme_alpha(COL_WHITE, (u8)(reveal * 0x3D)));
	} else {
		draw_round_rect_vgrad(x, y, size, size, 9.0f, z,
		                      theme_alpha(accent, 0x3D),
		                      theme_alpha(accent, 0x12));
		draw_round_rect_outline(x, y, size, size, 9.0f, 1.2f, z + 0.10f,
		                        theme_alpha(accent, 0x65));
		icons_draw(ICON_MUSIC, x + size * 0.5f, y + size * 0.5f, size * 0.44f,
		           z + 0.10f, theme_alpha(accent, alpha));
	}
}

static void draw_empty_media(float centre_y)
{
	draw_circle(SCREEN_TOP_W * 0.5f, centre_y - 15.0f, 32.0f, Z_CONTENT,
	            theme_alpha(COL_ACCENT, 0x14));
	icons_draw(ICON_MUSIC, SCREEN_TOP_W * 0.5f, centre_y - 15.0f, 37.0f,
	           Z_OVERLAY, COL_TEXT_FAINT);
	text_draw(SCREEN_TOP_W * 0.5f, centre_y + 28.0f, Z_CONTENT, TEXT_SMALL,
	          COL_TEXT_FAINT, ALIGN_CENTER, tr(STR_NOTHING_PLAYING));
}

void ui_top_media_draw(const App *app)
{
	const u32 accent = media_accent(app);
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, accent, 0.14f),
	                theme_mix(COL_BG, accent, 0.035f));

	if (!app->state.media_present) {
		draw_empty_media(132.0f);
		return;
	}

	const float reveal = ease_out_cubic(app->top_visual.media_reveal);
	const float slide = (1.0f - reveal) * 7.0f;
	const u8 alpha = (u8)(0x38 + reveal * 0xC7);
	const float art = 174.0f;
	const float art_x = 18.0f - slide;
	const float art_y = 48.0f;
	draw_artwork(art_x, art_y, art, reveal, accent, Z_CARD);

	const float text_x = 211.0f + slide;
	const float text_w = SCREEN_TOP_W - 16.0f - text_x;
	draw_media_brand_badge(app, text_x, 49.0f, text_w, Z_CONTENT);
	text_draw_clipped(text_x, 74.0f, Z_CONTENT, TEXT_TITLE,
	                  theme_alpha(COL_TEXT, alpha), ALIGN_LEFT, text_w,
	                  app->state.media_title);
	if (app->state.media_artist[0] != '\0') {
		text_draw_clipped(text_x, 101.0f, Z_CONTENT, TEXT_BODY,
		                  theme_alpha(theme_mix(COL_TEXT_DIM, accent, 0.38f), alpha),
		                  ALIGN_LEFT, text_w, app->state.media_artist);
	}
	if (app->state.media_album[0] != '\0') {
		text_draw_clipped(text_x, 121.0f, Z_CONTENT, TEXT_SMALL,
		                  theme_alpha(COL_TEXT_FAINT, alpha), ALIGN_LEFT, text_w,
		                  app->state.media_album);
	}

	draw_equalizer(app, text_x, 151.0f, text_w, 33.0f,
	               app->state.muted ? COL_ERR : accent);

	if (app->state.media_duration > 0) {
		const int position = display_position(app);
		char elapsed[16];
		char total[16];
		format_media_time(position, elapsed, sizeof(elapsed));
		format_media_time(app->state.media_duration, total, sizeof(total));

		draw_luminous_progress(
		    text_x, 199.0f, text_w, 5.0f,
		    (float)position / (float)app->state.media_duration, Z_CONTENT,
		    accent);
		/* Une ligne dediee et une taille superieure rendent les secondes nettes. */
		text_draw(text_x, 208.0f, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM,
		          ALIGN_LEFT, elapsed);
		text_draw(text_x + text_w, 208.0f, Z_CONTENT, TEXT_SMALL,
		          COL_TEXT_FAINT, ALIGN_RIGHT, total);
	}
}

static void draw_audio_module(float x, float y, float w, IconId icon,
	                              const char *label, int value, bool known,
	                              u32 color, float emphasis)
{
	const float h = 34.0f;
	const u32 surface = theme_mix(COL_SURFACE, color,
	                              0.06f + clamp01(emphasis) * 0.14f);
	draw_round_rect(x, y, w, h, 9.0f, Z_CARD, surface);
	draw_round_rect_outline(
	    x, y, w, h, 9.0f, 1.0f, Z_CONTENT,
	    theme_alpha(color, (u8)(0x35 + clamp01(emphasis) * 0x63)));
	icons_draw(icon, x + 14.0f, y + 17.0f, 16.0f, Z_CONTENT, color);
	text_draw_clipped(x + 27.0f, y + 3.0f, Z_CONTENT, TEXT_MICRO,
	                  COL_TEXT_DIM, ALIGN_LEFT, w - 64.0f, label);

	char value_text[8];
	if (known) {
		snprintf(value_text, sizeof(value_text), "%u%%",
		         (unsigned)value % 101u);
	} else {
		snprintf(value_text, sizeof(value_text), "--");
	}
	text_draw(x + w - 9.0f, y + 2.0f, Z_CONTENT,
	          emphasis > 0.05f ? TEXT_SMALL : TEXT_MICRO,
	          emphasis > 0.05f ? COL_TEXT : COL_TEXT_DIM, ALIGN_RIGHT,
	          value_text);

	const float track_x = x + 27.0f;
	const float track_w = w - 38.0f;
	if (known) {
		draw_luminous_progress(track_x, y + 25.0f, track_w, 4.0f,
		                         (float)value / 100.0f, Z_CONTENT, color);
	} else {
		draw_round_rect(track_x, y + 25.0f, track_w, 4.0f, 2.0f, Z_CONTENT,
		                COL_SURFACE_HI);
	}
}

static void draw_microphone_capsule(const App *app, float x, float y, float w)
{
	const bool known = app->state.mic_known;
	const bool muted = known && app->state.mic_muted;
	const u32 color = !known ? COL_TEXT_FAINT : (muted ? COL_ERR : COL_OK);
	const char *label = !known ? "--" : (muted ? tr(STR_MUTED) : tr(STR_LIVE));

	draw_round_rect(x, y, w, 34.0f, 17.0f, Z_CARD,
	                theme_mix(COL_SURFACE, color, known ? 0.10f : 0.03f));
	draw_round_rect_outline(x, y, w, 34.0f, 17.0f, 1.0f, Z_CONTENT,
	                        theme_alpha(color, known ? 0x58 : 0x2A));
	icons_draw(muted ? ICON_MIC_OFF : ICON_MIC, x + 17.0f, y + 17.0f, 17.0f,
	           Z_CONTENT, color);
	draw_circle(x + 32.0f, y + 17.0f, 2.5f, Z_CONTENT, color);
	text_draw_clipped(x + 40.0f, y + 10.0f, Z_CONTENT, TEXT_MICRO, color,
	                  ALIGN_LEFT, w - 47.0f, label);
}

static void draw_audio_dock(const App *app)
{
	const float y = SCREEN_H - AUDIO_DOCK_H;
	draw_rect(0.0f, y, SCREEN_TOP_W, AUDIO_DOCK_H, Z_CARD,
	          theme_alpha(COL_BG_ALT, 0xF4));
	draw_rect(0.0f, y, SCREEN_TOP_W, 1.0f, Z_CARD,
	          theme_alpha(COL_BORDER, 0xA0));

	const float module_y = y + 6.0f;
	const float gap = 6.0f;
	const float mic_w = 106.0f;
	const float mic_x = SCREEN_TOP_W - 8.0f - mic_w;
	const bool has_app_volume = app->state.app_volume >= 0;
	const u32 system_color = app->state.muted ? COL_ERR : COL_ACCENT;
	const u32 music_color = media_accent(app);

	if (has_app_volume) {
		const float module_w = (mic_x - 8.0f - gap * 2.0f) * 0.5f;
		draw_audio_module(
		    8.0f, module_y, module_w,
		    app->state.muted ? ICON_VOLUME_MUTE : ICON_VOLUME_UP,
		    tr(STR_SYSTEM_AUDIO), app->state.volume, app->state.volume >= 0,
		    system_color, app->top_visual.system_volume_emphasis);
		draw_audio_module(8.0f + module_w + gap, module_y, module_w, ICON_MUSIC,
		                  tr(STR_MUSIC), app->state.app_volume, true, music_color,
		                  app->top_visual.music_volume_emphasis);
	} else {
		draw_audio_module(
		    8.0f, module_y, mic_x - 8.0f - gap,
		    app->state.muted ? ICON_VOLUME_MUTE : ICON_VOLUME_UP,
		    tr(STR_SYSTEM_AUDIO), app->state.volume, app->state.volume >= 0,
		    system_color, app->top_visual.system_volume_emphasis);
	}
	draw_microphone_capsule(app, mic_x, module_y, mic_w);
}

void ui_top_audio_draw(const App *app)
{
	const float top = TOP_HEADER_H + 6.0f;
	const float height = SCREEN_H - AUDIO_DOCK_H - top - 8.0f;
	const float card_w = SCREEN_TOP_W - TOP_PAD * 2.0f;
	const u32 accent = app->state.muted ? COL_ERR : media_accent(app);

	draw_shadow(TOP_PAD, top, card_w, height, 10.0f, Z_BG);
	draw_round_rect_vgrad(TOP_PAD, top, card_w, height, 10.0f, Z_CARD,
	                      theme_mix(COL_SURFACE, accent, 0.08f),
	                      theme_mix(COL_SURFACE_LO, accent, 0.02f));

	const bool has_output = app->state.audio_output[0] != '\0';
	draw_round_rect(TOP_PAD + 12.0f, top + 9.0f, card_w - 24.0f, 34.0f,
	                10.0f, Z_CONTENT, theme_alpha(COL_BG, 0x88));
	draw_round_rect_outline(TOP_PAD + 12.0f, top + 9.0f, card_w - 24.0f,
	                        34.0f, 10.0f, 1.0f, Z_OVERLAY,
	                        theme_alpha(accent, 0x42));
	icons_draw(app->state.muted ? ICON_VOLUME_MUTE : ICON_VOLUME_UP,
	           TOP_PAD + 29.0f, top + 26.0f, 18.0f, Z_OVERLAY, accent);
	text_draw(TOP_PAD + 43.0f, top + 11.0f, Z_OVERLAY, TEXT_MICRO,
	          COL_TEXT_FAINT, ALIGN_LEFT, tr(STR_AUDIO_OUTPUT));
	text_draw_clipped(TOP_PAD + 43.0f, top + 24.0f, Z_OVERLAY, TEXT_SMALL,
	                  has_output ? COL_TEXT : COL_TEXT_FAINT, ALIGN_LEFT,
	                  card_w - 76.0f,
	                  has_output ? app->state.audio_output
	                             : tr(STR_OUTPUT_UNKNOWN));

	if (app->state.audio_output_count > 1) {
		float chip_x = TOP_PAD + 16.0f;
		const float chip_y = top + 48.0f;
		const float limit = TOP_PAD + card_w - 12.0f;
		for (int i = 0; i < app->state.audio_output_count; i++) {
			const char *name = app->state.audio_outputs[i];
			if (name[0] == '\0') {
				continue;
			}
			const bool current =
			    has_output && strcmp(name, app->state.audio_output) == 0;
			const float chip_w = text_width(name, TEXT_MICRO) + 14.0f;
			if (chip_x + chip_w > limit) {
				break;
			}
			draw_round_rect(chip_x, chip_y, chip_w, 15.0f, 7.5f, Z_CONTENT,
			                current ? theme_alpha(accent, 0x40)
			                        : theme_alpha(COL_SURFACE_HI, 0xAA));
			text_draw(chip_x + 7.0f, chip_y + 2.0f, Z_OVERLAY, TEXT_MICRO,
			          current ? accent : COL_TEXT_FAINT, ALIGN_LEFT, name);
			chip_x += chip_w + 5.0f;
		}
	}

	const float eq_y = top + 69.0f;
	const float eq_h = height - 81.0f;
	if (eq_h > 12.0f) {
		draw_equalizer(app, TOP_PAD + 16.0f, eq_y, card_w - 32.0f, eq_h,
		               accent);
	}
	draw_audio_dock(app);
}

void ui_top_frame_draw(const App *app)
{
	const u32 accent = media_accent(app);
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, accent, 0.16f),
	                theme_mix(COL_BG, accent, 0.04f));

	if (!app->state.media_present) {
		draw_empty_media(SCREEN_H * 0.48f);
		text_draw(SCREEN_TOP_W * 0.5f, SCREEN_H - 24.0f, Z_CONTENT, TEXT_BODY,
		          COL_TEXT_FAINT, ALIGN_CENTER,
		          app->state.time[0] != '\0' ? app->state.time
		                                     : app->local_time);
		return;
	}

	const float reveal = ease_out_cubic(app->top_visual.media_reveal);
	const float slide = (1.0f - reveal) * 7.0f;
	const u8 alpha = (u8)(0x38 + reveal * 0xC7);
	const float art = SCREEN_H - 34.0f;
	const float art_x = 18.0f - slide;
	const float art_y = 17.0f;
	draw_artwork(art_x, art_y, art, reveal, accent, Z_CARD);

	const float text_x = 18.0f + art + 18.0f + slide;
	const float text_w = SCREEN_TOP_W - 16.0f - text_x;
	if (!app->frame_from_idle) {
		text_draw(SCREEN_TOP_W - 16.0f, art_y, Z_CONTENT, TEXT_SMALL,
		          theme_alpha(COL_TEXT, 0xAA), ALIGN_RIGHT,
		          app->state.time[0] != '\0' ? app->state.time
		                                     : app->local_time);
	}
	draw_media_brand_badge(app, text_x, art_y + 18.0f, text_w, Z_CONTENT);
	text_draw_clipped(text_x, art_y + 43.0f, Z_CONTENT, TEXT_TITLE,
	                  theme_alpha(COL_TEXT, alpha), ALIGN_LEFT, text_w,
	                  app->state.media_title);
	if (app->state.media_artist[0] != '\0') {
		text_draw_clipped(text_x, art_y + 69.0f, Z_CONTENT, TEXT_BODY,
		                  theme_alpha(theme_mix(COL_TEXT_DIM, accent, 0.45f), alpha),
		                  ALIGN_LEFT, text_w, app->state.media_artist);
	}
	if (app->state.media_album[0] != '\0') {
		text_draw_clipped(text_x, art_y + 89.0f, Z_CONTENT, TEXT_SMALL,
		                  theme_alpha(COL_TEXT_FAINT, alpha), ALIGN_LEFT, text_w,
		                  app->state.media_album);
	}
	draw_equalizer(app, text_x, art_y + 116.0f, text_w, 34.0f,
	               app->state.muted ? COL_ERR : accent);

	if (app->state.media_duration > 0) {
		const int position = display_position(app);
		char elapsed[16];
		char total[16];
		format_media_time(position, elapsed, sizeof(elapsed));
		format_media_time(app->state.media_duration, total, sizeof(total));
		const float bar_y = art_y + art - 26.0f;
		draw_luminous_progress(
		    text_x, bar_y, text_w, 5.0f,
		    (float)position / (float)app->state.media_duration, Z_CONTENT,
		    accent);
		text_draw(text_x, bar_y + 8.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_LEFT, elapsed);
		text_draw(text_x + text_w, bar_y + 8.0f, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_RIGHT, total);
	}
}
