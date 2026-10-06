/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file text.h
 * @brief Rendu de texte au-dessus de citro2d.
 *
 * citro2d exige de « parser » une chaîne dans un tampon de glyphes avant de
 * l'afficher. Ce module encapsule ce cycle, gère l'alignement et tronque
 * proprement les textes trop longs avec une ellipse.
 */
#pragma once

#include <3ds.h>
#include <citro2d.h>

typedef enum {
	ALIGN_LEFT = 0,
	ALIGN_CENTER,
	ALIGN_RIGHT,
} TextAlign;

/**
 * Échelles Citro2D : la bibliothèque normalise la cellule de toutes les
 * polices (système et BCFNT) à 30 pixels avant d'appliquer cette échelle.
 * Ne pas appliquer de conversion depuis la taille en points de mkbcfnt.
 * Cette référence commune garde mesures, dessin et placement cohérents.
 */
#define TEXT_REFERENCE_PX 30.0f
enum {
#define FONT_FACE(name, pixels, points) TEXT_##name##_PX = pixels,
#include "font_faces.def"
#undef FONT_FACE
};
#define TEXT_HUGE (TEXT_HUGE_PX / TEXT_REFERENCE_PX)
#define TEXT_TITLE (TEXT_TITLE_PX / TEXT_REFERENCE_PX)
#define TEXT_LARGE (TEXT_LARGE_PX / TEXT_REFERENCE_PX)
#define TEXT_BODY (TEXT_BODY_PX / TEXT_REFERENCE_PX)
#define TEXT_SMALL (TEXT_SMALL_PX / TEXT_REFERENCE_PX)
#define TEXT_MICRO (TEXT_MICRO_PX / TEXT_REFERENCE_PX)

/** Hauteur en pixels d'une ligne à l'échelle donnée. */
#define TEXT_LINE_PX(scale) ((scale) * TEXT_REFERENCE_PX)

/** Alloue les tampons de texte. À appeler après `C2D_Init`. */
bool text_init(void);

/** Indique si la police embarquée a pu être chargée. */
bool text_has_custom_font(void);

/** Libère les tampons. */
void text_exit(void);

/**
 * Vide le tampon de glyphes de la frame, et le cache de textes s'il est plein.
 * À appeler une fois par frame, avant tout dessin.
 */
void text_frame_begin(void);

/** Largeur qu'occuperait `str` à l'échelle `scale`. */
float text_width(const char *str, float scale);

/** Hauteur d'une ligne à l'échelle `scale`. */
float text_height(float scale);

/**
 * Dessine `str` à la position (`x`, `y`), `y` désignant le haut du texte.
 * Retourne la largeur dessinée.
 */
float text_draw(float x, float y, float depth, float scale, u32 color,
                TextAlign align, const char *str);

/**
 * Dessine `str` en le tronquant avec une ellipse si sa largeur dépasse
 * `max_width`.
 */
void text_draw_clipped(float x, float y, float depth, float scale, u32 color,
                       TextAlign align, float max_width, const char *str);
