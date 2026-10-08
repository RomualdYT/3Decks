#pragma once
#include <stddef.h>

typedef float (*TextMeasure)(const char *text, float scale);
/* Bounded cache: 64 widths + 32 clipped labels; no per-frame allocation.
 * Reset whenever the font changes. Text and scale are part of every key. */
void text_layout_reset(void);
float text_layout_width(const char *text, float scale, TextMeasure measure);
void text_layout_clip(char out[128], const char *text, float scale,
                      float max_width, TextMeasure measure);
