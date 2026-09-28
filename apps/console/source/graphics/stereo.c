/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "stereo.h"

/*
 * Le décalage appliqué reste volontairement modeste. Une parallaxe trop marquée
 * fatigue rapidement et provoque un dédoublement perceptible dès que l'on
 * s'écarte de l'axe de l'écran ; quelques pixels suffisent à donner du relief
 * sans inconfort.
 */
#define MAX_SHIFT_PIXELS 2.6f

/** Signe du décalage : négatif pour l'œil gauche, positif pour le droit. */
static float s_direction = 0.0f;

/** Intensité courante, de 0 (plat) à 1 (relief maximal). */
static float s_strength = 0.0f;

void stereo_begin_eye(int eye, float strength)
{
	if (strength < 0.0f) {
		strength = 0.0f;
	}
	if (strength > 1.0f) {
		strength = 1.0f;
	}

	s_strength = strength;
	/*
	 * L'œil gauche voit les objets proches décalés vers la droite, et
	 * inversement : c'est ce croisement qui crée la sensation de profondeur.
	 */
	s_direction = (eye == 0) ? -1.0f : 1.0f;
}

void stereo_end_eye(void)
{
	s_strength = 0.0f;
	s_direction = 0.0f;
}

float stereo_offset(float depth)
{
	if (s_strength <= 0.001f) {
		return 0.0f;
	}
	return depth * s_direction * s_strength * MAX_SHIFT_PIXELS;
}

bool stereo_active(void)
{
	return s_strength > 0.001f;
}
