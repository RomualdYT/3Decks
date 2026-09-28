/** Decky's portable pixel artwork. Coordinates are integer pixels in a 40x40 tile. */
#pragma once
#include <stdint.h>

typedef enum {
	DECKY_IDLE, DECKY_WAVE, DECKY_SEARCH, DECKY_MUSIC,
	DECKY_SLEEP, DECKY_CONFUSED, DECKY_MOOD_COUNT
} DeckyMood;

/** RGB color, not platform-specific packed ABGR. No allocation or global state. */
typedef void (*DeckyPixelRect)(void *context, int x, int y, int w, int h, uint32_t rgb);
void decky_draw(DeckyMood mood, float seconds, DeckyPixelRect paint, void *context);
