/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "icons.h"

#include <citro2d.h>
#include <math.h>
#include <stdio.h>

#include "draw.h"
#include "stereo.h"

enum {
#define ICON_ASSET(id, name) ASSET_##id,
#include "icon_assets.def"
#undef ICON_ASSET
	ASSET_COUNT
};

static const int s_asset_index[ICON_COUNT] = {
	[ICON_NONE] = -1,
#define ICON_ASSET(id, name) [ICON_##id] = ASSET_##id,
#include "icon_assets.def"
#undef ICON_ASSET
};

static const int s_sizes[] = {
#define ICON_SIZE(pixels) pixels,
#include "icon_sizes.def"
#undef ICON_SIZE
};
#define ICON_SHEET_COUNT (sizeof(s_sizes) / sizeof(s_sizes[0]))
static C2D_SpriteSheet s_sheets[ICON_SHEET_COUNT];

void icons_init(void)
{
	for (size_t i = 0; i < ICON_SHEET_COUNT; ++i) {
		char path[48];
		snprintf(path, sizeof(path), "romfs:/icons/icons-%d.t3x", s_sizes[i]);
		s_sheets[i] = C2D_SpriteSheetLoad(path);
		if (s_sheets[i] && C2D_SpriteSheetCount(s_sheets[i]) != ASSET_COUNT) {
			C2D_SpriteSheetFree(s_sheets[i]);
			s_sheets[i] = NULL;
		} else if (s_sheets[i]) {
			const C2D_Image image = C2D_SpriteSheetGetImage(s_sheets[i], 0);
			C3D_TexSetFilter(image.tex, GPU_LINEAR, GPU_LINEAR);
		}
	}
}

void icons_exit(void)
{
	for (size_t i = 0; i < ICON_SHEET_COUNT; ++i) {
		if (s_sheets[i]) C2D_SpriteSheetFree(s_sheets[i]);
		s_sheets[i] = NULL;
	}
}

static bool draw_asset(IconId icon, float cx, float cy, float size, float z,
                       u32 color)
{
	if (icon <= ICON_NONE || icon >= ICON_COUNT || size <= 0.0f) return false;
	size_t best = 0;
	float distance = INFINITY;
	for (size_t i = 0; i < ICON_SHEET_COUNT; ++i) {
		if (!s_sheets[i]) continue;
		const float candidate = fabsf(size - (float)s_sizes[i]);
		/* Break exact ties toward the larger source: preserve fine strokes. */
		if (candidate <= distance) { distance = candidate; best = i; }
	}
	if (!s_sheets[best]) return false;
	const C2D_Image image = C2D_SpriteSheetGetImage(s_sheets[best],
	                                             s_asset_index[icon]);
	if (!image.tex || !image.subtex) return false;
	/* Pixel aligned geometry plus closely spaced native atlases keep glyphs
	 * crisp; light linear filtering avoids harsh stair steps when resized. */
	C2D_ImageTint tint;
	C2D_PlainImageTint(&tint, color, 1.0f);
	const float draw_size = fmaxf(1.0f, roundf(size));
	const float scale = draw_size / (float)s_sizes[best];
	return C2D_DrawImageAt(image,
	                       roundf(cx - draw_size * 0.5f + stereo_offset(z * STEREO_FROM_Z)),
	                       roundf(cy - draw_size * 0.5f), z, &tint, scale, scale);
}

/*
 * Chaque icône est construite à partir de rectangles, cercles, triangles et
 * lignes. Les coordonnées sont exprimées en fraction de `size` pour rester
 * proportionnelles quelle que soit la taille demandée.
 */

static void icon_mic(float cx, float cy, float s, float z, u32 c, bool crossed)
{
	const float body_w = s * 0.30f;
	const float body_h = s * 0.46f;
	const float top = cy - s * 0.42f;

	/* Capsule du micro. */
	draw_round_rect(cx - body_w * 0.5f, top, body_w, body_h, body_w * 0.5f, z, c);

	/* Arceau de maintien, en segments droits : plus net qu'un arc à cette taille. */
	const float arc_y = cy + s * 0.06f;
	const float arc_w = s * 0.44f;
	const float thick = s * 0.075f;
	draw_line(cx - arc_w * 0.5f, arc_y - s * 0.06f, cx - arc_w * 0.5f,
	          arc_y + s * 0.04f, thick, z, c);
	draw_line(cx + arc_w * 0.5f, arc_y - s * 0.06f, cx + arc_w * 0.5f,
	          arc_y + s * 0.04f, thick, z, c);
	draw_line(cx - arc_w * 0.5f, arc_y + s * 0.04f, cx + arc_w * 0.5f,
	          arc_y + s * 0.04f, thick, z, c);

	/* Pied. */
	draw_line(cx, arc_y + s * 0.04f, cx, cy + s * 0.34f, thick, z, c);
	draw_line(cx - s * 0.17f, cy + s * 0.36f, cx + s * 0.17f, cy + s * 0.36f,
	          thick, z, c);

	if (crossed) {
		draw_line(cx - s * 0.42f, cy - s * 0.42f, cx + s * 0.42f, cy + s * 0.42f,
		          s * 0.10f, z, c);
	}
}

/** Dessine le pavillon d'un haut-parleur. */
static void speaker_body(float cx, float cy, float s, float z, u32 c)
{
	const float left = cx - s * 0.34f;
	draw_rect(left, cy - s * 0.12f, s * 0.16f, s * 0.24f, z, c);
	/* Cône : triangle pointant vers la gauche. */
	draw_triangle(left + s * 0.16f, cy - s * 0.12f, left + s * 0.16f,
	              cy + s * 0.12f, left + s * 0.40f, cy + s * 0.34f, z, c);
	draw_triangle(left + s * 0.16f, cy - s * 0.12f, left + s * 0.40f,
	              cy - s * 0.34f, left + s * 0.40f, cy + s * 0.34f, z, c);
}

static void icon_volume(float cx, float cy, float s, float z, u32 c, int level)
{
	speaker_body(cx, cy, s, z, c);

	const float thick = s * 0.075f;

	if (level < 0) {
		/* Croix : son coupé. */
		const float x0 = cx + s * 0.14f;
		draw_line(x0, cy - s * 0.16f, x0 + s * 0.28f, cy + s * 0.16f, thick, z, c);
		draw_line(x0, cy + s * 0.16f, x0 + s * 0.28f, cy - s * 0.16f, thick, z, c);
		return;
	}

	/* Ondes sonores, approximées par des arcs verticaux légèrement inclinés. */
	const float base_x = cx + s * 0.12f;
	const int waves = (level == 0) ? 1 : 2;
	for (int i = 0; i < waves; i++) {
		const float x = base_x + (float)i * s * 0.14f;
		const float h = s * (0.12f + (float)i * 0.09f);
		draw_line(x, cy - h, x + s * 0.04f, cy, thick, z, c);
		draw_line(x + s * 0.04f, cy, x, cy + h, thick, z, c);
	}

	if (level > 0) {
		/* Signe plus pour "augmenter". */
		return;
	}
}

static void icon_volume_updown(float cx, float cy, float s, float z, u32 c,
                               bool up)
{
	speaker_body(cx - s * 0.06f, cy, s, z, c);

	const float thick = s * 0.085f;
	const float px = cx + s * 0.22f;
	draw_line(px - s * 0.11f, cy, px + s * 0.11f, cy, thick, z, c);
	if (up) {
		draw_line(px, cy - s * 0.11f, px, cy + s * 0.11f, thick, z, c);
	}
}

static void icon_play(float cx, float cy, float s, float z, u32 c)
{
	/*
	 * Triangle plein, sans fioriture. Les tentatives d'adoucissement des
	 * sommets rendaient la forme moins nette : à cette taille, la simplicité
	 * donne un résultat plus propre.
	 */
	const float h = s * 0.40f;
	draw_triangle(cx - s * 0.20f, cy - h, cx - s * 0.20f, cy + h, cx + s * 0.32f,
	              cy, z, c);
}

static void icon_pause(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.15f;
	const float h = s * 0.72f;
	draw_round_rect(cx - s * 0.26f, cy - h * 0.5f, w, h, w * 0.28f, z, c);
	draw_round_rect(cx + s * 0.11f, cy - h * 0.5f, w, h, w * 0.28f, z, c);
}

static void icon_skip(float cx, float cy, float s, float z, u32 c, bool forward)
{
	/* Deux triangles et une barre : lecture immédiate, tracé net. */
	const float h = s * 0.34f;
	const float dir = forward ? 1.0f : -1.0f;
	const float x0 = cx - dir * s * 0.30f;

	draw_triangle(x0, cy - h, x0, cy + h, x0 + dir * s * 0.26f, cy, z, c);
	draw_triangle(x0 + dir * s * 0.22f, cy - h, x0 + dir * s * 0.22f, cy + h,
	              x0 + dir * s * 0.48f, cy, z, c);
	draw_rect(cx + dir * s * 0.26f - (forward ? 0.0f : s * 0.09f),
	          cy - h, s * 0.09f, h * 2.0f, z, c);
}

static void icon_app(float cx, float cy, float s, float z, u32 c)
{
	/* Quatre tuiles carrées, légèrement adoucies. */
	const float g = s * 0.06f;
	const float side = s * 0.31f;
	const float r = side * 0.26f;
	draw_round_rect(cx - side - g * 0.5f, cy - side - g * 0.5f, side, side, r, z, c);
	draw_round_rect(cx + g * 0.5f, cy - side - g * 0.5f, side, side, r, z, c);
	draw_round_rect(cx - side - g * 0.5f, cy + g * 0.5f, side, side, r, z, c);
	draw_round_rect(cx + g * 0.5f, cy + g * 0.5f, side, side, r, z, c);
}

static void icon_browser(float cx, float cy, float s, float z, u32 c)
{
	const float r = s * 0.40f;
	draw_ring(cx, cy, r, s * 0.075f, z, c);
	/* Méridien et parallèle pour évoquer un globe. */
	draw_ellipse_ring(cx, cy, r * 0.44f, r, s * 0.065f, z, c);
	draw_line(cx - r, cy, cx + r, cy, s * 0.065f, z, c);
}

static void icon_terminal(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.80f;
	const float h = s * 0.64f;
	draw_round_rect_outline(cx - w * 0.5f, cy - h * 0.5f, w, h, s * 0.10f,
	                        s * 0.075f, z, c);
	/* Chevron et curseur. */
	const float thick = s * 0.065f;
	const float bx = cx - w * 0.22f;
	draw_line(bx, cy - s * 0.10f, bx + s * 0.10f, cy, thick, z, c);
	draw_line(bx + s * 0.10f, cy, bx, cy + s * 0.10f, thick, z, c);
	draw_line(bx + s * 0.18f, cy + s * 0.10f, bx + s * 0.40f, cy + s * 0.10f,
	          thick, z, c);
}

static void icon_folder(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.80f;
	const float h = s * 0.60f;
	const float x = cx - w * 0.5f;
	const float y = cy - h * 0.5f;
	/* Onglet. */
	draw_round_rect(x, y, w * 0.42f, h * 0.22f, s * 0.05f, z, c);
	draw_round_rect(x, y + h * 0.12f, w, h * 0.88f, s * 0.08f, z, c);
}

static void icon_music(float cx, float cy, float s, float z, u32 c)
{
	/* Deux notes reliées par une hampe. Formes pleines, contours francs. */
	const float thick = s * 0.085f;
	const float head_r = s * 0.13f;

	draw_circle(cx - s * 0.16f, cy + s * 0.24f, head_r, z, c);
	draw_circle(cx + s * 0.22f, cy + s * 0.16f, head_r, z, c);
	draw_rect(cx - s * 0.16f + head_r - thick, cy - s * 0.34f, thick,
	          s * 0.58f, z, c);
	draw_rect(cx + s * 0.22f + head_r - thick, cy - s * 0.42f, thick,
	          s * 0.58f, z, c);
	/* Hampe reliant les deux notes. */
	draw_line(cx - s * 0.16f + head_r - thick * 0.5f, cy - s * 0.34f,
	          cx + s * 0.22f + head_r - thick * 0.5f, cy - s * 0.42f,
	          thick * 1.1f, z, c);
}

static void icon_chat(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.78f;
	const float h = s * 0.56f;
	draw_round_rect(cx - w * 0.5f, cy - h * 0.62f, w, h, s * 0.14f, z, c);
	/* Pointe de la bulle. */
	draw_triangle(cx - s * 0.20f, cy + h * 0.36f, cx - s * 0.02f, cy + h * 0.36f,
	              cx - s * 0.22f, cy + s * 0.40f, z, c);
}

static void icon_video(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.54f;
	const float h = s * 0.44f;
	draw_round_rect(cx - s * 0.36f, cy - h * 0.5f, w, h, s * 0.08f, z, c);
	/* Objectif latéral. */
	draw_triangle(cx + s * 0.20f, cy, cx + s * 0.40f, cy - h * 0.44f,
	              cx + s * 0.40f, cy + h * 0.44f, z, c);
}

static void icon_record(float cx, float cy, float s, float z, u32 c)
{
	draw_ring(cx, cy, s * 0.38f, s * 0.075f, z, c);
	draw_circle(cx, cy, s * 0.19f, z, c);
}

static void icon_bell(float cx, float cy, float s, float z, u32 c)
{
	const float thick = s * 0.07f;
	draw_arc(cx, cy - s * 0.10f, s * 0.25f, thick, 0.75f, 0.5f, z, c);
	draw_line(cx - s * 0.25f, cy - s * 0.10f, cx - s * 0.32f, cy + s * 0.24f, thick, z, c);
	draw_line(cx + s * 0.25f, cy - s * 0.10f, cx + s * 0.32f, cy + s * 0.24f, thick, z, c);
	draw_line(cx - s * 0.32f, cy + s * 0.24f, cx + s * 0.32f, cy + s * 0.24f, thick, z, c);
	draw_circle(cx, cy + s * 0.37f, s * 0.07f, z, c);
}

static void icon_status(float cx, float cy, float s, float z, u32 c)
{
	draw_ring(cx, cy, s * 0.36f, s * 0.07f, z, c);
	draw_line(cx, cy, cx + s * 0.20f, cy - s * 0.20f, s * 0.07f, z, c);
	draw_circle(cx, cy, s * 0.06f, z, c);
}

static void icon_artwork(float cx, float cy, float s, float z, u32 c)
{
	draw_round_rect_outline(cx - s * 0.36f, cy - s * 0.36f, s * 0.72f, s * 0.72f,
	                        s * 0.06f, s * 0.065f, z, c);
	draw_circle(cx - s * 0.15f, cy - s * 0.15f, s * 0.065f, z, c);
	draw_line(cx - s * 0.30f, cy + s * 0.26f, cx + s * 0.07f, cy - s * 0.07f, s * 0.06f, z, c);
	draw_line(cx + s * 0.07f, cy - s * 0.07f, cx + s * 0.30f, cy + s * 0.17f, s * 0.06f, z, c);
}

static void icon_lock(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.62f;
	const float h = s * 0.44f;
	draw_round_rect(cx - w * 0.5f, cy - s * 0.02f, w, h, s * 0.09f, z, c);
	/* Anse. */
	const float thick = s * 0.085f;
	const float ax = s * 0.19f;
	draw_line(cx - ax, cy - s * 0.02f, cx - ax, cy - s * 0.22f, thick, z, c);
	draw_line(cx + ax, cy - s * 0.02f, cx + ax, cy - s * 0.22f, thick, z, c);
	draw_line(cx - ax, cy - s * 0.22f, cx + ax, cy - s * 0.22f, thick, z, c);
}

static void icon_page(float cx, float cy, float s, float z, u32 c)
{
	const float w = s * 0.60f;
	const float h = s * 0.76f;
	draw_round_rect_outline(cx - w * 0.5f, cy - h * 0.5f, w, h, s * 0.07f,
	                        s * 0.07f, z, c);
	const float thick = s * 0.06f;
	for (int i = 0; i < 3; i++) {
		const float y = cy - s * 0.16f + (float)i * s * 0.16f;
		draw_rect(cx - w * 0.26f, y, w * 0.52f, thick, z, c);
	}
}

static void icon_power(float cx, float cy, float s, float z, u32 c)
{
	draw_arc(cx, cy, s * 0.34f, s * 0.085f, 0.45f, 0.55f, z, c);
	draw_rect(cx - s * 0.04f, cy - s * 0.44f, s * 0.08f, s * 0.28f, z, c);
}

static void icon_gear(float cx, float cy, float s, float z, u32 c)
{
	draw_ring(cx, cy, s * 0.26f, s * 0.10f, z, c);
	/* Dents réparties autour du moyeu. */
	const int teeth = 8;
	for (int i = 0; i < teeth; i++) {
		const float a = (float)i * (6.28318f / (float)teeth);
		draw_spoke(cx, cy, a, s * 0.30f, s * 0.42f, s * 0.11f, z, c);
	}
}

static void icon_star(float cx, float cy, float s, float z, u32 c)
{
	draw_star(cx, cy, s * 0.44f, s * 0.19f, z, c);
}

void icons_draw(IconId icon, float cx, float cy, float size, float depth,
                u32 color)
{
	if (draw_asset(icon, cx, cy, size, depth, color)) return;
	switch (icon) {
	case ICON_MIC:
		icon_mic(cx, cy, size, depth, color, false);
		break;
	case ICON_MIC_OFF:
		icon_mic(cx, cy, size, depth, color, true);
		break;
	case ICON_VOLUME_UP:
		icon_volume_updown(cx, cy, size, depth, color, true);
		break;
	case ICON_VOLUME_DOWN:
		icon_volume_updown(cx, cy, size, depth, color, false);
		break;
	case ICON_VOLUME_MUTE:
		icon_volume(cx, cy, size, depth, color, -1);
		break;
	case ICON_PLAY:
		icon_play(cx, cy, size, depth, color);
		break;
	case ICON_PAUSE:
		icon_pause(cx, cy, size, depth, color);
		break;
	case ICON_NEXT:
		icon_skip(cx, cy, size, depth, color, true);
		break;
	case ICON_PREVIOUS:
		icon_skip(cx, cy, size, depth, color, false);
		break;
	case ICON_APP:
		icon_app(cx, cy, size, depth, color);
		break;
	case ICON_BROWSER:
		icon_browser(cx, cy, size, depth, color);
		break;
	case ICON_TERMINAL:
		icon_terminal(cx, cy, size, depth, color);
		break;
	case ICON_FOLDER:
		icon_folder(cx, cy, size, depth, color);
		break;
	case ICON_MUSIC:
		icon_music(cx, cy, size, depth, color);
		break;
	case ICON_CHAT:
		icon_chat(cx, cy, size, depth, color);
		break;
	case ICON_VIDEO:
		icon_video(cx, cy, size, depth, color);
		break;
	case ICON_RECORD:
		icon_record(cx, cy, size, depth, color);
		break;
	case ICON_LOCK:
		icon_lock(cx, cy, size, depth, color);
		break;
	case ICON_PAGE:
		icon_page(cx, cy, size, depth, color);
		break;
	case ICON_POWER:
		icon_power(cx, cy, size, depth, color);
		break;
	case ICON_GEAR:
		icon_gear(cx, cy, size, depth, color);
		break;
	case ICON_STAR:
		icon_star(cx, cy, size, depth, color);
		break;
	case ICON_BELL:
		icon_bell(cx, cy, size, depth, color);
		break;
	case ICON_STATUS:
		icon_status(cx, cy, size, depth, color);
		break;
	case ICON_ARTWORK:
		icon_artwork(cx, cy, size, depth, color);
		break;
	case ICON_NONE:
	case ICON_COUNT:
	default:
		break;
	}
}
