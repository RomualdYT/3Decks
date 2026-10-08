#pragma once
#include <3ds.h>
#include <stdbool.h>
#include <stddef.h>

/* Fixed 64-slot cache; images arrive as 16×16 tiled RGBA8, with alpha. */
bool chat_badges_consume(const char *payload, size_t length);
bool chat_badges_draw(u32 token, float x, float y, float size, float depth);
void chat_badges_exit(void);
