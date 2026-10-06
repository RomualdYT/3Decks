/* Verify the renderer against Citro2D's normalized 30 px font contract.
 * In particular, loading a custom font must not enlarge the UI. */
#include "text.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

struct TestFont { int cell_height; bool nearest; };
static bool custom;
static float drawn_x, drawn_y, drawn_width, drawn_height;
static unsigned draws;
C2D_TextBuf C2D_TextBufNew(size_t glyphs) { (void)glyphs; return malloc(1); }
void C2D_TextBufDelete(C2D_TextBuf buf) { free(buf); }
void C2D_TextBufClear(C2D_TextBuf buf) { (void)buf; }
static unsigned missing_height;
static bool wrong_height;
static unsigned live_fonts;
C2D_Font C2D_FontLoad(const char *path)
{
    if (!custom) return NULL;
    unsigned height = 29;
    const char *native = strstr(path, "fonts/deck-");
    if (native) {
        assert(sscanf(native, "fonts/deck-%u.bcfnt", &height) == 1);
        if (height == missing_height) return NULL;
        if (wrong_height) height++;
    }
    C2D_Font font = calloc(1, sizeof(*font));
    assert(font);
    font->cell_height = height;
    live_fonts++;
    return font;
}
void C2D_FontFree(C2D_Font font) { live_fonts--; free(font); }
FINF_s *C2D_FontGetInfo(C2D_Font font)
{
    static TGLP_s glyphs;
    static FINF_s info = {&glyphs};
    glyphs.cellHeight = font->cell_height;
    return &info;
}
void C2D_FontSetFilter(C2D_Font font, int mag, int min)
{
    assert(mag == GPU_NEAREST && min == GPU_NEAREST);
    font->nearest = true;
}
const char *C2D_TextFontParse(C2D_Text *text, C2D_Font font,
                            C2D_TextBuf buf, const char *str)
{
    (void)buf;
    const float cell = font ? font->cell_height : 30;
    /* Native advances are normalized by the SDK during parsing. */
    text->font = font;
    text->width = strlen(str) * (cell * 0.5f) * (30.0f / cell);
    return str + strlen(str);
}
void C2D_TextOptimize(const C2D_Text *text) { (void)text; }
void C2D_TextGetDimensions(const C2D_Text *text, float sx, float sy,
                           float *width, float *height)
{
    *width = text->width * sx;
    *height = 30 * sy;
}
void C2D_DrawText(const C2D_Text *text, u32 flags, float x, float y,
                  float z, float sx, float sy, ...)
{
    (void)flags; (void)z;
    drawn_x = x; drawn_y = y;
    drawn_width = text->width * sx; drawn_height = 30 * sy;
    if (custom && text->font->nearest) {
        /* The atlas must be sampled 1:1, not merely at a rounded origin. */
        assert(fabsf(sx * 30 / text->font->cell_height - 1) < 0.0001f);
    }
    if (custom && !missing_height && !wrong_height) {
        assert(text->font->nearest);
        assert(fabsf(text->font->cell_height - 30 * sy) < 0.001f);
    }
    draws++;
}
float stereo_offset(float depth) { (void)depth; return 0; }
static void near(float actual, float expected) { assert(fabsf(actual - expected) < 0.001f); }
int main(void)
{
    for (int font = 0; font < 4; font++) {
        custom = font != 0;
        missing_height = font == 2 ? TEXT_SMALL_PX : 0;
        wrong_height = font == 3;
        assert(text_init());
        assert(text_has_custom_font() == custom);
        text_frame_begin();
        const float sizes[] = {TEXT_MICRO, TEXT_SMALL, TEXT_BODY, TEXT_LARGE, TEXT_TITLE, TEXT_HUGE};
        for (unsigned i = 0; i < sizeof(sizes) / sizeof(*sizes); i++) {
            const float scale = sizes[i];
            const float width = text_width("Volume", scale);
            near(width, 90 * scale);
            /* Repeat uses the parsed-text cache as well. */
            for (int repeat = 0; repeat < 2; repeat++) {
                text_draw(160, 20, 0, scale, 0, ALIGN_CENTER, "Volume");
                near(drawn_x, roundf(160 - width / 2));
                near(drawn_y, 20);
                near(drawn_width, width);
                near(drawn_height, text_height(scale));
            }
        }
        text_draw_clipped(100, 20, 0, TEXT_BODY, 0, ALIGN_RIGHT, 60, "Long button label");
        assert(drawn_width <= 60);
        assert(fabsf(drawn_x + drawn_width - 100) <= 0.5f);
        text_draw(160.25f, 20.7f, 0, TEXT_SMALL, 0, ALIGN_CENTER, "Volume");
        near(drawn_x, roundf(160.25f - text_width("Volume", TEXT_SMALL) / 2));
        near(drawn_y, 21);
        unsigned before = draws;
        text_draw_clipped(0, 0, 0, TEXT_BODY, 0, ALIGN_LEFT, 1, "Too narrow");
        assert(draws == before);
        text_exit();
        assert(live_fonts == 0);
    }
    puts("text renderer: system/custom scale, alignment, cache and clipping passed");
}
