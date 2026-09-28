#include "ui_companion.h"
#include "draw.h"
#include "i18n.h"
#include "text.h"
#include "theme.h"
#include <math.h>

typedef struct { float x, y; int scale; } Placement;
static void paint(void *context, int x, int y, int w, int h, uint32_t rgb)
{
	const Placement *p = context;
	draw_rect(p->x + x * p->scale, p->y + y * p->scale,
	          w * p->scale, h * p->scale, Z_CONTENT,
	          C2D_Color32((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255, 255));
}

void ui_companion_draw(DeckyMood mood, float seconds, float x, float y, int scale)
{
	if (scale < 1 || scale > 4) return;
	Placement placement = { floorf(x), floorf(y), scale };
	decky_draw(mood, seconds, paint, &placement);
}

bool ui_companion_standby(const App *app)
{
	return app->config_received && app->frame_mode && app->frame_from_idle &&
	       app->settings.companion != COMPANION_OFF &&
	       (app->settings.companion == COMPANION_STANDBY ||
	        app->state.media_title[0] == '\0');
}

void ui_companion_standby_draw(const App *app)
{
	const bool music = app->link == LINK_ONLINE && app->state.media_playing;
	draw_rect_vgrad(0, 0, SCREEN_TOP_W, SCREEN_H, Z_BG,
	                theme_mix(COL_BG, COL_ACCENT, .06f), COL_BG);
	text_draw(20, 16, Z_CONTENT, TEXT_TITLE, COL_TEXT, ALIGN_LEFT, app->local_time);
	text_draw(SCREEN_TOP_W - 20, 20, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM,
	          ALIGN_RIGHT, app->local_date);
	ui_companion_draw(music ? DECKY_MUSIC : DECKY_SLEEP, app->uptime, 140, 56, 3);
	text_draw(200, 182, Z_CONTENT, TEXT_LARGE, COL_TEXT, ALIGN_CENTER, "Decky");
	text_draw(200, 207, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM, ALIGN_CENTER,
	          tr(music ? STR_DECKY_LISTENING : STR_DECKY_RESTING));
}
