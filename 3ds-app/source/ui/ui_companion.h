#pragma once
#include "app.h"
#include "decky.h"

/** Companion preference: hidden, discreet, or dedicated idle screen. */
enum { COMPANION_OFF, COMPANION_DISCREET, COMPANION_STANDBY };
void ui_companion_draw(DeckyMood mood, float seconds, float x, float y, int scale);
bool ui_companion_standby(const App *app);
void ui_companion_standby_draw(const App *app);
