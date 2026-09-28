#include "framing.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static FrameBuffer rx;
static char output[FRAME_MAX_PAYLOAD + 1];
static void header(unsigned char *out, size_t n)
{
    out[0] = n >> 24; out[1] = n >> 16; out[2] = n >> 8; out[3] = n;
}
/* Feeds bytes through the receive API, as net.c does. */
static void feed(const unsigned char *bytes, size_t count)
{
    while (count > 0) {
        size_t space;
        unsigned char *area = frame_write_area(&rx, &space);
        assert(space > 0);
        const size_t chunk = count < space ? count : space;
        memcpy(area, bytes, chunk);
        frame_commit(&rx, chunk);
        bytes += chunk; count -= chunk;
    }
}
static unsigned char big[FRAME_BUFFER_SIZE];
static void compaction(void)
{
    size_t length;
    frame_reset(&rx);
    const unsigned char wire[] = {0, 0, 0, 3, 'a', 'b', 'c'};
    feed(wire, sizeof(wire));
    /* Leave the header and half of a maximum frame behind a taken one. */
    header(big, FRAME_MAX_PAYLOAD);
    memset(big + 4, 'y', FRAME_MAX_PAYLOAD);
    feed(big, 4 + FRAME_MAX_PAYLOAD / 2);
    assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_READY);
    assert(length == 3 && rx.start == sizeof(wire));
    /* The tail cannot hold the rest: the pending bytes move to the front. */
    feed(big + 4 + FRAME_MAX_PAYLOAD / 2, FRAME_MAX_PAYLOAD / 2);
    assert(rx.start == 0);
    size_t space;
    frame_write_area(&rx, &space);
    assert(space == 0);
    assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_READY);
    assert(length == FRAME_MAX_PAYLOAD && output[0] == 'y' && output[length - 1] == 'y');
    assert(rx.used == 0 && rx.start == 0);
    /* An invalid header never receives more bytes. */
    const unsigned char invalid[] = {0, 0, 0, 0};
    feed(invalid, sizeof(invalid));
    frame_write_area(&rx, &space);
    assert(space == 0);
}
int main(void)
{
    size_t length;
    const unsigned char wire[] = {0, 0, 0, 3, 'a', 'b', 'c'};
    for (size_t split = 0; split < sizeof(wire); split++) {
        memset(&rx, 0, sizeof(rx));
        memcpy(rx.data, wire, split); rx.used = split;
        assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_INCOMPLETE);
        assert(rx.used == split);
        memcpy(rx.data + split, wire + split, sizeof(wire) - split);
        rx.used = sizeof(wire);
        assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_READY);
        assert(length == 3 && !strcmp(output, "abc") && rx.used == 0);
    }
    for (int i = 0; i < 100; i++) { feed(wire, sizeof(wire)); }
    for (int i = 0; i < 100; i++)
        assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_READY && length == 3);
    assert(rx.used == 0 && rx.start == 0);
    header(rx.data, FRAME_MAX_PAYLOAD); rx.used = sizeof(rx.data);
    memset(rx.data + 4, 'x', FRAME_MAX_PAYLOAD);
    assert(frame_take(&rx, output, FRAME_MAX_PAYLOAD, &length) == FRAME_OUTPUT_TOO_SMALL);
    assert(length == 0 && rx.used == sizeof(rx.data));
    assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_READY);
    assert(length == FRAME_MAX_PAYLOAD && output[length] == 0 && output[length-1] == 'x');
    const size_t invalid[] = {0, FRAME_MAX_PAYLOAD + 1, UINT32_MAX};
    for (size_t i = 0; i < sizeof(invalid)/sizeof(*invalid); i++) {
        header(rx.data, invalid[i]); rx.used = 4;
        assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_INVALID);
    }
    compaction();
    puts("framing: fragmented headers/payloads, bursts, maximum size, invalid lengths and compaction passed");
}
