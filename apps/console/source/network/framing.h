#pragma once
#include <stddef.h>
#include <stdint.h>

#define FRAME_MAX_PAYLOAD 65536u
#define FRAME_BUFFER_SIZE (FRAME_MAX_PAYLOAD + 4)
/*
 * Pending bytes are data[start, start + used). Taking a frame only advances
 * `start`; the bytes are moved back to the front solely when the tail cannot
 * hold the rest of the pending frame, so a burst of messages costs no copy.
 */
typedef struct {
    unsigned char data[FRAME_BUFFER_SIZE];
    size_t start;
    size_t used;
} FrameBuffer;
typedef enum {
    FRAME_INCOMPLETE, FRAME_READY, FRAME_INVALID, FRAME_OUTPUT_TOO_SMALL
} FrameResult;

void frame_reset(FrameBuffer *buffer);
/* No allocation; incomplete frames and undersized outputs are not consumed. */
FrameResult frame_peek(const FrameBuffer *buffer, size_t *length);
FrameResult frame_take(FrameBuffer *buffer, char *out, size_t capacity, size_t *length);
/*
 * Free space where received bytes can be written, after compaction if needed.
 * Zero means the buffer is full: a complete frame is waiting to be taken, or
 * the pending header is invalid.
 */
unsigned char *frame_write_area(FrameBuffer *buffer, size_t *space);
/* Records `count` bytes written at the area returned by `frame_write_area`. */
void frame_commit(FrameBuffer *buffer, size_t count);
