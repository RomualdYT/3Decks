#include "text_layout.h"
#include <math.h>
#include <stdbool.h>
#include <string.h>

#define WIDTH_ENTRIES 64
#define CLIP_ENTRIES 32
typedef struct { char text[128]; float scale, width; bool used; } WidthEntry;
typedef struct {
    char text[256], clipped[128];
    float scale, max_width;
    bool used;
} ClipEntry;
static WidthEntry widths[WIDTH_ENTRIES];
static ClipEntry clips[CLIP_ENTRIES];
static unsigned next_width, next_clip;

void text_layout_reset(void)
{
    memset(widths, 0, sizeof(widths));
    memset(clips, 0, sizeof(clips));
    next_width = next_clip = 0;
}

float text_layout_width(const char *text, float scale, TextMeasure measure)
{
    if (!text || !*text || !isfinite(scale) || scale <= 0) return 0;
    const size_t length = strlen(text);
    if (length >= sizeof(widths[0].text)) return measure(text, scale);
    for (unsigned i = 0; i < WIDTH_ENTRIES; i++) {
        const WidthEntry *entry = &widths[i];
        if (entry->used && entry->scale == scale && !strcmp(entry->text, text))
            return entry->width;
    }
    const float width = measure(text, scale);
    WidthEntry *entry = &widths[next_width++ % WIDTH_ENTRIES];
    memcpy(entry->text, text, length + 1);
    entry->scale = scale;
    entry->width = width;
    entry->used = true;
    return width;
}

void text_layout_clip(char out[128], const char *text, float scale,
                      float max_width, TextMeasure measure)
{
    out[0] = '\0';
    if (!text || !*text || !isfinite(max_width) || max_width <= 0 ||
        !isfinite(scale) || scale <= 0) return;
    const size_t length = strlen(text);
    const bool cacheable = length < sizeof(clips[0].text);
    if (cacheable) {
        for (unsigned i = 0; i < CLIP_ENTRIES; i++) {
            const ClipEntry *entry = &clips[i];
            if (entry->used && entry->scale == scale &&
                entry->max_width == max_width && !strcmp(entry->text, text)) {
                strcpy(out, entry->clipped);
                return;
            }
        }
    }
    if (length < 128 && text_layout_width(text, scale, measure) <= max_width) {
        strcpy(out, text);
    } else if (text_layout_width("...", scale, measure) <= max_width) {
        /* Search character boundaries, not bytes: no partial UTF-8 glyph. */
        size_t boundaries[125], count = 1;
        boundaries[0] = 0;
        for (size_t i = 1; i <= length && i <= 124; i++)
            if (((unsigned char)text[i] & 0xc0) != 0x80) boundaries[count++] = i;
        size_t low = 0, high = count - 1;
        while (low < high) {
            const size_t mid = (low + high + 1) / 2;
            memcpy(out, text, boundaries[mid]);
            strcpy(out + boundaries[mid], "...");
            if (text_layout_width(out, scale, measure) <= max_width) low = mid;
            else high = mid - 1;
        }
        memcpy(out, text, boundaries[low]);
        strcpy(out + boundaries[low], "...");
    }
    if (cacheable) {
        ClipEntry *entry = &clips[next_clip++ % CLIP_ENTRIES];
        strcpy(entry->text, text);
        strcpy(entry->clipped, out);
        entry->scale = scale;
        entry->max_width = max_width;
        entry->used = true;
    }
}
