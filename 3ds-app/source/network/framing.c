#include "framing.h"
#include <string.h>

FrameResult frame_peek(const FrameBuffer *buffer, size_t *length)
{
    *length = 0;
    if (buffer->used < 4) return FRAME_INCOMPLETE;
    const unsigned char *p = buffer->data;
    const uint32_t size = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
                          ((uint32_t)p[2] << 8) | p[3];
    if (size == 0 || size > FRAME_MAX_PAYLOAD) return FRAME_INVALID;
    *length = size;
    return buffer->used >= size + 4 ? FRAME_READY : FRAME_INCOMPLETE;
}

FrameResult frame_take(FrameBuffer *buffer, char *out, size_t capacity, size_t *length)
{
    size_t size;
    if (length) *length = 0;
    const FrameResult result = frame_peek(buffer, &size);
    if (result != FRAME_READY) return result;
    if (!out || capacity <= size) return FRAME_OUTPUT_TOO_SMALL;
    memcpy(out, buffer->data + 4, size);
    out[size] = '\0';
    buffer->used -= size + 4;
    memmove(buffer->data, buffer->data + size + 4, buffer->used);
    if (length) *length = size;
    return FRAME_READY;
}
