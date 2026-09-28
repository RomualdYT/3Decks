#include "text_layout.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned measurements;
static float measure(const char *text, float scale)
{
    measurements++;
    size_t glyphs = 0;
    for (const unsigned char *p = (const unsigned char *)text; *p; p++)
        if ((*p & 0xc0) != 0x80) glyphs++;
    return glyphs * scale;
}
int main(void)
{
    char out[128], first[128];
    text_layout_reset();
    text_layout_clip(out, "Fenêtres disponibles", 1, 12, measure);
    assert(!strcmp(out, "Fenêtres ..."));
    strcpy(first, out);
    unsigned cold = measurements;
    for (int i = 0; i < 10000; i++) {
        text_layout_clip(out, "Fenêtres disponibles", 1, 12, measure);
        assert(!strcmp(out, first));
    }
    assert(measurements == cold);
    printf("text layout: cold=%u measurements, 10000 repeated clips=0 additional measurements\n", cold);
    text_layout_clip(out, "ééééé", 1, 4, measure);
    assert(!strcmp(out, "é..."));
    text_layout_clip(out, "long label", 1, 2, measure); assert(!*out);
    text_layout_clip(out, "abc", 1, 3, measure); assert(!strcmp(out, "abc"));
    text_layout_clip(out, "abc", 2, 3, measure); assert(!*out);
    for (int i = 0; i < 200; i++) {
        char label[64]; snprintf(label, sizeof(label), "Label %d with extra text", i);
        text_layout_clip(out, label, 1, 12, measure);
        assert(strlen(out) <= 12);
    }
    text_layout_clip(out, "Fenêtres disponibles", 1, 12, measure); assert(!strcmp(out, first));
    text_layout_reset();
    unsigned before = measurements;
    text_layout_clip(out, "Fenêtres disponibles", 1, 12, measure); assert(measurements > before);
    char long_label[1024]; memset(long_label, 'x', sizeof(long_label)-1); long_label[1023] = 0;
    text_layout_clip(out, long_label, 1, 200, measure); assert(strlen(out) == 127);
    puts("text layout: UTF-8, scale/width keys, narrow spaces, eviction and reset passed");
}
