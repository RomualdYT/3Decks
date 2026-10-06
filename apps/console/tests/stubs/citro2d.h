#pragma once
#include "3ds.h"
static inline u32 C2D_Color32(u8 r, u8 g, u8 b, u8 a)
{
    return (u32)r | (u32)g << 8 | (u32)b << 16 | (u32)a << 24;
}
void C2D_DrawRectSolid(float x, float y, float depth, float width, float height,
                       u32 color);
void C2D_DrawRectangle(float x, float y, float depth, float width, float height,
                       u32 color0, u32 color1, u32 color2, u32 color3);
void C2D_DrawCircleSolid(float x, float y, float depth, float radius, u32 color);
void C2D_DrawTriangle(float x0, float y0, u32 color0,
                      float x1, float y1, u32 color1,
                      float x2, float y2, u32 color2, float depth);
void C2D_DrawLine(float x0, float y0, u32 color0,
                  float x1, float y1, u32 color1, float thickness, float depth);

/* Text SDK boundary, implemented by test_text_render.c. */
typedef struct TestTextBuffer *C2D_TextBuf;
typedef struct TestFont *C2D_Font;
typedef struct { u8 cellHeight; } TGLP_s;
typedef struct { TGLP_s *tglp; } FINF_s;
#define GPU_NEAREST 0
FINF_s *C2D_FontGetInfo(C2D_Font font);
void C2D_FontSetFilter(C2D_Font font, int mag, int min);
typedef struct { float width; C2D_Font font; } C2D_Text;
#define C2D_WithColor 2
C2D_TextBuf C2D_TextBufNew(size_t glyphs);
void C2D_TextBufDelete(C2D_TextBuf buf);
void C2D_TextBufClear(C2D_TextBuf buf);
C2D_Font C2D_FontLoad(const char *path);
void C2D_FontFree(C2D_Font font);
const char *C2D_TextFontParse(C2D_Text *text, C2D_Font font,
                            C2D_TextBuf buf, const char *str);
void C2D_TextOptimize(const C2D_Text *text);
void C2D_TextGetDimensions(const C2D_Text *text, float sx, float sy,
                           float *width, float *height);
void C2D_DrawText(const C2D_Text *text, u32 flags, float x, float y,
                  float z, float sx, float sy, ...);
