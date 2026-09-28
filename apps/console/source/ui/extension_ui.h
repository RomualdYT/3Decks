/* 3Decks — GPL-3.0. Declarative extension UI; no third-party code runs here. */
#pragma once

#include "app.h"
void extension_dashboard_draw(const App *app);
const ExtensionButtonState *extension_button_state(const PcState *state,
                                                   const char *page,
                                                   const char *button);
