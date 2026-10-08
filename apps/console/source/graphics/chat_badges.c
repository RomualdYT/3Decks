#include "chat_badges.h"
#include "stereo.h"
#include <citro2d.h>
#include <string.h>

#define BADGE_SIDE 16
#define BADGE_SLOTS 64
#define BADGE_FRAME_BYTES (12 + BADGE_SIDE * BADGE_SIDE * 4)

typedef struct {
    C3D_Tex texture;
    u32 token;
    bool ready;
} BadgeSlot;
static BadgeSlot s_badges[BADGE_SLOTS];
static unsigned s_next;
static Tex3DS_SubTexture s_subtex = {
    .width = BADGE_SIDE, .height = BADGE_SIDE,
    .left = 0, .top = 1, .right = 1, .bottom = 0,
};

bool chat_badges_consume(const char *payload, size_t length)
{
    if (length < 12 || memcmp(payload, "BDG0", 4)) return false;
    const unsigned char *header = (const unsigned char *)payload;
    const u16 width = header[4] | (header[5] << 8);
    const u16 height = header[6] | (header[7] << 8);
    const u32 token = (u32)header[8] | ((u32)header[9] << 8) |
                      ((u32)header[10] << 16) | ((u32)header[11] << 24);
    if (width != BADGE_SIDE || height != BADGE_SIDE || length != BADGE_FRAME_BYTES || !token) return true;
    for (unsigned i = 0; i < BADGE_SLOTS; i++) if (s_badges[i].ready && s_badges[i].token == token) return true;
    BadgeSlot *slot = &s_badges[s_next];
    if (!slot->ready) {
        if (!C3D_TexInit(&slot->texture, BADGE_SIDE, BADGE_SIDE, GPU_RGBA8)) return true;
        C3D_TexSetFilter(&slot->texture, GPU_LINEAR, GPU_LINEAR);
        C3D_TexSetWrap(&slot->texture, GPU_CLAMP_TO_EDGE, GPU_CLAMP_TO_EDGE);
        slot->ready = true;
    }
    C3D_TexUpload(&slot->texture, payload + 12);
    C3D_TexFlush(&slot->texture);
    slot->token = token;
    s_next = (s_next + 1) % BADGE_SLOTS;
    return true;
}

bool chat_badges_draw(u32 token, float x, float y, float size, float depth)
{
    for (unsigned i = 0; i < BADGE_SLOTS; i++) {
        const BadgeSlot *slot = &s_badges[i];
        if (!slot->ready || slot->token != token) continue;
        const C2D_Image image = { (C3D_Tex *)&slot->texture, &s_subtex };
        const C2D_DrawParams params = {
            .pos = { x + stereo_offset(depth * STEREO_FROM_Z), y, size, size },
            .center = {0, 0}, .depth = depth, .angle = 0,
        };
        C2D_DrawImage(image, &params, NULL);
        return true;
    }
    return false;
}

void chat_badges_exit(void)
{
    for (unsigned i = 0; i < BADGE_SLOTS; i++) if (s_badges[i].ready) C3D_TexDelete(&s_badges[i].texture);
    memset(s_badges, 0, sizeof(s_badges));
    s_next = 0;
}
