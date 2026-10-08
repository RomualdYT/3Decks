#include "setup_internal.h"
#include "discovery.h"
#include "theme.h"

/** Bouton principal, en bas de l'écran. */
void primary_button_bounds(float *x, float *y, float *w, float *h)
{
	*w = SCREEN_BOTTOM_W - 40.0f;
	*h = PRIMARY_BUTTON_H;
	*x = 20.0f;
	*y = SCREEN_H - PRIMARY_BUTTON_MARGIN - PRIMARY_BUTTON_H;
}

/**
 * Géométrie d'une ligne de liste.
 *
 * Le pas est calculé à partir de l'espace réellement disponible et du nombre de
 * lignes, jamais codé en dur : ajouter un réglage resserre automatiquement la
 * liste au lieu de la faire déborder sous le bouton.
 *
 * Le pas est plafonné pour que quelques lignes ne s'étalent pas sur tout
 * l'écran, et un plancher garantit que le texte reste lisible.
 */
void row_bounds(int index, float *y, float *height)
{
	float pitch = ROWS_AVAILABLE / (float)SETTINGS_ROWS;

	if (pitch > 30.0f) {
		pitch = 30.0f;
	}
	if (pitch < 18.0f) {
		/*
		 * En deçà, le texte ne tiendrait plus : mieux vaut accepter un léger
		 * dépassement visuel qu'un texte illisible.
		 */
		pitch = 18.0f;
	}

	*height = pitch - 4.0f;
	*y = ROWS_TOP + (float)index * pitch;
}

/** Premier résultat à afficher lorsque la liste dépasse trois ordinateurs. */
int first_visible_agent(const Setup *setup)
{
	const int count = discovery_count();
	if (count <= AGENT_VISIBLE || setup->selected_agent < AGENT_VISIBLE) {
		return 0;
	}

	int first = setup->selected_agent - AGENT_VISIBLE + 1;
	const int maximum = count - AGENT_VISIBLE;
	if (first > maximum) {
		first = maximum;
	}
	return first;
}

void agent_card_bounds(int index, float *y)
{
	*y = AGENT_CARD_TOP + (float)index * (AGENT_CARD_H + AGENT_CARD_GAP);
}
