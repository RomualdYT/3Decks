#pragma once

#include <stdbool.h>

/* Call after C2D_Init and before C2D_Fini, respectively. */
void brand_icons_init(void);
void brand_icons_exit(void);

/* Native 16 px mark, centered and pixel-aligned after stereo positioning.
 * Returns false when the asset is unavailable so callers can use a fallback. */
bool brand_icons_draw_spotify(float cx, float cy, float z);
