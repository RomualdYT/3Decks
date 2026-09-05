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
    for (int i = 0; i < 100; i++) { memcpy(rx.data + rx.used, wire, sizeof(wire)); rx.used += sizeof(wire); }
    for (int i = 0; i < 100; i++)
        assert(frame_take(&rx, output, sizeof(output), &length) == FRAME_READY && length == 3);
    assert(rx.used == 0);
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
    puts("framing: fragmented headers/payloads, bursts, maximum size and invalid lengths passed");
}
