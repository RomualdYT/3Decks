/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "render_pacing.h"

bool render_pacing_should_draw(RenderPacing *pacing, float dt, bool idle,
                               double last_rx_at)
{
	if (!idle) {
		pacing->elapsed = 0.0f;
		pacing->last_rx_at = last_rx_at;
		pacing->was_idle = false;
		return true;
	}

	pacing->elapsed += dt;
	if (!pacing->was_idle || pacing->elapsed >= IDLE_RENDER_INTERVAL ||
	    pacing->last_rx_at != last_rx_at) {
		pacing->elapsed = 0.0f;
		pacing->last_rx_at = last_rx_at;
		pacing->was_idle = true;
		return true;
	}
	return false;
}
