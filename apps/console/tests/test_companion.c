/** Native integration policy and scaled drawing, without a graphics context. */
#include "ui_companion.h"
#include "ui_intro.h"
#include <math.h>
#include "draw.h"
#include "text.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned rectangles;
void draw_rect(float x, float y, float w, float h, float z, u32 color)
{
    (void)z; (void)color;
    assert(x >= 0 && y >= 0 && x + w <= 400 && y + h <= 240);
    rectangles++;
}
void draw_rect_vgrad(float x, float y, float w, float h, float z, u32 a, u32 b)
{ (void)b; draw_rect(x,y,w,h,z,a); }
float text_draw(float x, float y, float z, float scale, u32 color, TextAlign align, const char *text)
{ (void)x; (void)y; (void)z; (void)scale; (void)color; (void)align; (void)text; return 0; }

int main(void)
{
    UiIntro intro;
    ui_intro_begin(&intro, false);
    ui_intro_update(&intro, .1f, false);
    assert(!intro.active && intro.elapsed == 0);
    ui_intro_begin(&intro, true);
    ui_intro_update(&intro, NAN, false);
    ui_intro_update(&intro, -1, false);
    assert(intro.active && intro.elapsed == 0);
    for (int frame = 0; frame < 72; frame++) {
        ui_intro_draw_top(&intro);
        ui_intro_draw_bottom();
        ui_intro_update(&intro, 1.0f / 60, false);
    }
    ui_intro_update(&intro, .01f, false);
    assert(!intro.active);
    ui_intro_update(&intro, 10, false);
    assert(!intro.active); /* No replay on reconnect/resume. */
    ui_intro_begin(&intro, true);
    ui_intro_update(&intro, .01f, true);
    assert(!intro.active);
    static App app;
    app.config_received = true;
    app.frame_mode = app.frame_from_idle = true;
    app.settings.companion = COMPANION_OFF;
    assert(!ui_companion_standby(&app));
    app.settings.companion = COMPANION_DISCREET;
    assert(ui_companion_standby(&app));
    strcpy(app.state.media_title, "Music");
    assert(!ui_companion_standby(&app));
    app.settings.companion = COMPANION_STANDBY;
    assert(ui_companion_standby(&app));
    app.frame_from_idle = false;
    assert(!ui_companion_standby(&app));
    app.frame_from_idle = true;
    app.config_received = false;
    assert(!ui_companion_standby(&app));
    for (int mood = 0; mood < DECKY_MOOD_COUNT; mood++)
        ui_companion_draw((DeckyMood)mood, .75f, 140, 56, 3);
    const unsigned before = rectangles;
    ui_companion_draw(DECKY_IDLE, 0, 0, 0, 0);
    assert(rectangles == before);
    ui_companion_standby_draw(&app);
    app.link = LINK_ONLINE; app.state.media_playing = true;
    ui_companion_standby_draw(&app);
    puts("companion: off/discreet/idle policy, manual artwork and connection protection, drawing bounds passed");
}
