#include "framing.h"
#include <string.h>

void frame_reset(FrameBuffer *buffer)
{
    buffer->start = 0;
    buffer->used = 0;
}

FrameResult frame_peek(const FrameBuffer *buffer, size_t *length)
{
    *length = 0;
    if (buffer->used < 4) return FRAME_INCOMPLETE;
    const unsigned char *p = buffer->data + buffer->start;
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
    memcpy(out, buffer->data + buffer->start + 4, size);
    out[size] = '\0';
    buffer->used -= size + 4;
    buffer->start = buffer->used ? buffer->start + size + 4 : 0;
    if (length) *length = size;
    return FRAME_READY;
}

unsigned char *frame_write_area(FrameBuffer *buffer, size_t *space)
{
    size_t size;
    const FrameResult pending = frame_peek(buffer, &size);
    /* Bytes still missing before the pending frame can be taken. */
    const size_t missing = pending == FRAME_INCOMPLETE
                               ? (buffer->used < 4 ? 4 - buffer->used
                                                   : size + 4 - buffer->used)
                               : 0;
    const size_t tail = FRAME_BUFFER_SIZE - buffer->start - buffer->used;
    if (buffer->start > 0 && tail < missing) {
        memmove(buffer->data, buffer->data + buffer->start, buffer->used);
        buffer->start = 0;
    }
    const size_t end = buffer->start + buffer->used;
    *space = pending == FRAME_INVALID ? 0 : FRAME_BUFFER_SIZE - end;
    return buffer->data + end;
}

void frame_commit(FrameBuffer *buffer, size_t count)
{
    const size_t space = FRAME_BUFFER_SIZE - buffer->start - buffer->used;
    buffer->used += count < space ? count : space;
}
