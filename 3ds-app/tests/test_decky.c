#include "decky.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdint.h>

typedef struct { unsigned count; uint64_t hash; } Capture;
static void capture(void *context, int x, int y, int w, int h, uint32_t rgb)
{
    Capture *frame = context;
    assert(x >= 0 && y >= 0 && w > 0 && h > 0);
    assert(x + w <= 40 && y + h <= 40);
    assert(rgb <= 0xffffff);
    frame->count++;
    frame->hash = frame->hash * 31 + rgb + x * 3 + y * 7 + w * 11 + h * 13;
}
static uint64_t frame(DeckyMood mood, float time)
{
    Capture result = {0};
    decky_draw(mood, time, capture, &result);
    assert(result.count > 35 && result.count < 100);
    return result.hash;
}
int main(void)
{
    uint64_t moods[DECKY_MOOD_COUNT];
    for (int mood = 0; mood < DECKY_MOOD_COUNT; mood++) {
        moods[mood] = frame((DeckyMood)mood, 0);
        for (int tick = 0; tick < 240; tick++) frame((DeckyMood)mood, tick / 4.0f);
        for (int previous = 0; previous < mood; previous++) assert(moods[mood] != moods[previous]);
    }
    assert(frame(DECKY_IDLE, NAN) == frame(DECKY_IDLE, 0));
    assert(frame(DECKY_IDLE, INFINITY) == frame(DECKY_IDLE, 0));
    assert(frame(DECKY_IDLE, -1) == frame(DECKY_IDLE, 0));
    assert(frame(DECKY_WAVE, .1f) == frame(DECKY_WAVE, .2f));
    assert(frame(DECKY_WAVE, 0) != frame(DECKY_WAVE, .5f));
    decky_draw(DECKY_IDLE, 0, NULL, NULL);
    puts("Decky: six distinct moods, bounded geometry, deterministic animation and invalid time passed");
}
