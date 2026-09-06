#pragma once
#include <stdbool.h>

/** Launch-only presentation; never owns input scanning or network updates. */
typedef struct { float elapsed; bool active; } UiIntro;
void ui_intro_begin(UiIntro *intro, bool enabled);
void ui_intro_update(UiIntro *intro, float dt, bool skip);
void ui_intro_draw_top(const UiIntro *intro);
void ui_intro_draw_bottom(void);
