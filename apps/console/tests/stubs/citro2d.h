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
