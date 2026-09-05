#pragma once
#include "3ds.h"
static inline u32 C2D_Color32(u8 r, u8 g, u8 b, u8 a)
{
    return (u32)r | (u32)g << 8 | (u32)b << 16 | (u32)a << 24;
}
