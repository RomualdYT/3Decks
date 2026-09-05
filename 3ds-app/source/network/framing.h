#pragma once
#include <stddef.h>
#include <stdint.h>

#define FRAME_MAX_PAYLOAD 65536u
typedef struct {
    unsigned char data[FRAME_MAX_PAYLOAD + 4];
    size_t used;
} FrameBuffer;
typedef enum {
    FRAME_INCOMPLETE, FRAME_READY, FRAME_INVALID, FRAME_OUTPUT_TOO_SMALL
} FrameResult;

/* No allocation; incomplete frames and undersized outputs are not consumed. */
FrameResult frame_peek(const FrameBuffer *buffer, size_t *length);
FrameResult frame_take(FrameBuffer *buffer, char *out, size_t capacity, size_t *length);
