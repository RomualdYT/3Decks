/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file stereo.h
 * @brief Rendu stéréoscopique de l'écran supérieur.
 *
 * L'écran supérieur de la console affiche deux images légèrement décalées, une
 * par œil. En attribuant une profondeur à chaque élément et en décalant son
 * abscisse proportionnellement, on obtient un relief réel plutôt qu'un simple
 * effet d'ombre.
 *
 * Le décalage suit le curseur 3D de la console : à zéro, les deux images sont
 * identiques et le rendu redevient plat, sans coût supplémentaire.
 *
 * Convention de profondeur : une valeur positive place l'élément *derrière*
 * l'écran, une valeur négative le fait ressortir. Les plans lointains sont donc
 * les fonds, et les éléments saillants les cartes et le texte de premier plan.
 */
#pragma once

#include <stdbool.h>

/*
 * Le relief est dérivé de la profondeur de rendu déjà utilisée par l'interface
 * (`Z_BG`, `Z_CARD`, `Z_CONTENT`, `Z_OVERLAY`). Aucun appel de dessin n'a donc
 * besoin d'être modifié : la hiérarchie visuelle existante devient une
 * hiérarchie spatiale.
 *
 * `Z_BG` valant zéro reste au plan de l'écran, et les couches supérieures
 * ressortent progressivement.
 */

/** Facteur convertissant une profondeur de rendu en amplitude de relief. */
#define STEREO_FROM_Z (-6.0f)

/**
 * Prépare le rendu d'un œil.
 *
 * `eye` vaut 0 pour l'œil gauche et 1 pour le droit. L'intensité provient du
 * curseur de la console.
 */
void stereo_begin_eye(int eye, float strength);

/** Termine le rendu de l'œil courant. */
void stereo_end_eye(void);

/**
 * Décalage horizontal à appliquer à un élément situé à la profondeur `depth`.
 *
 * Retourne zéro lorsque le relief est désactivé, ce qui permet d'appeler cette
 * fonction sans condition dans le code de rendu.
 */
float stereo_offset(float depth);

/** Indique si le rendu en relief est actif pour l'image courante. */
bool stereo_active(void);
