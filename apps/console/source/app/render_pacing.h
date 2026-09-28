#ifndef DECK3DS_RENDER_PACING_H
#define DECK3DS_RENDER_PACING_H

#include <stdbool.h>

/** Cadence de rafraîchissement d'une page immobile en veille. */
#define IDLE_RENDER_INTERVAL 1.0f

typedef struct {
	float elapsed;
	double last_rx_at;
	bool was_idle;
} RenderPacing;

/**
 * Ne suspend que le dessin. L'appelant continue à traiter les entrées, le
 * réseau et l'état de l'application à chaque passage dans sa boucle.
 */
bool render_pacing_should_draw(RenderPacing *pacing, float dt, bool idle,
                               double last_rx_at);

#endif
