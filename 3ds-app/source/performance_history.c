/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "performance_history.h"

#include <string.h>

static unsigned char sample(int value)
{
	if (value < 0) {
		return PERFORMANCE_UNKNOWN;
	}
	if (value > 100) {
		return 100;
	}
	return (unsigned char)value;
}

void performance_history_init(PerformanceHistory *history)
{
	memset(history, 0, sizeof(*history));
	memset(history->cpu, PERFORMANCE_UNKNOWN, sizeof(history->cpu));
	memset(history->memory, PERFORMANCE_UNKNOWN, sizeof(history->memory));
	/* Le premier état connu est visible immédiatement, sans seconde d'attente. */
	history->elapsed = 1.0f;
}

void performance_history_update(PerformanceHistory *history,
                                const PcState *state, float dt)
{
	history->elapsed += dt;
	while (history->elapsed >= 1.0f) {
		history->elapsed -= 1.0f;
		history->cpu[history->head] = sample(state->cpu);
		history->memory[history->head] = sample(state->memory);
		history->head = (history->head + 1) % PERFORMANCE_HISTORY_SAMPLES;
		if (history->count < PERFORMANCE_HISTORY_SAMPLES) {
			history->count++;
		}
	}
}

static int chronological(const unsigned char *samples,
                         const PerformanceHistory *history, int index)
{
	if (index < 0 || index >= history->count) {
		return -1;
	}
	const int oldest =
	    (history->head - history->count + PERFORMANCE_HISTORY_SAMPLES) %
	    PERFORMANCE_HISTORY_SAMPLES;
	const unsigned char value =
	    samples[(oldest + index) % PERFORMANCE_HISTORY_SAMPLES];
	return value == PERFORMANCE_UNKNOWN ? -1 : (int)value;
}

int performance_history_cpu(const PerformanceHistory *history, int index)
{
	return chronological(history->cpu, history, index);
}

int performance_history_memory(const PerformanceHistory *history, int index)
{
	return chronological(history->memory, history, index);
}

