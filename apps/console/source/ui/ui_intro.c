#include "ui_intro.h"
#include "ui_companion.h"
#include "draw.h"
#include "text.h"
#include "theme.h"
#include <math.h>

#define INTRO_DURATION 1.2f

void ui_intro_begin(UiIntro *intro, bool enabled)
{
	*intro = (UiIntro){ .active = enabled };
}

void ui_intro_update(UiIntro *intro, float dt, bool skip)
{
	if (!intro->active) return;
	if (isfinite(dt) && dt > 0) intro->elapsed += dt;
	if (skip || intro->elapsed >= INTRO_DURATION) intro->active = false;
}

void ui_intro_draw_top(const UiIntro *intro)
{
	const float t = intro->elapsed;
	draw_rect_vgrad(0, 0, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, COL_ACCENT, .045f), COL_BG);
	/* Reuse the closed-eye idle frame, without the sleeping pose's Z. */
	const DeckyMood mood = t < .4f ? DECKY_IDLE : DECKY_WAVE;
	const float frame = t < .22f ? 4.5f : (t < .4f ? 0 : t - .4f);
	const float rise = t < .22f ? floorf(6 * (1 - t / .22f)) : 0;
	ui_companion_draw(mood, frame, 140, 44 + rise, 3);
	/* Antenna lights wake after the eyes open. */
	if (t < .3f) {
		draw_rect(179, 50 + rise, 6, 6, Z_CONTENT, COL_TEXT_DIM);
		draw_rect(218, 50 + rise, 6, 6, Z_CONTENT, COL_TEXT_DIM);
	}
	text_draw(200, 180, Z_CONTENT, TEXT_LARGE, COL_TEXT, ALIGN_CENTER, "3Decks");
}

void ui_intro_draw_bottom(void)
{
	/* No fake progress bar: discovery and pairing continue underneath. */
	text_draw(160, 112, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM, ALIGN_CENTER, "3Decks");
}
