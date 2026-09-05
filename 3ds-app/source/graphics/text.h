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
 * Échelle typographique.
 *
 * La police système de la console est une police bitmap dont la hauteur de
 * glyphe est de 30 pixels. L'échelle est donc un facteur de réduction, et non
 * une taille en points : à 0,30 les caractères ne mesurent plus que neuf
 * pixels, ce qui les rend illisibles quel que soit le filtrage appliqué.
 *
 * Les valeurs ci-dessous fixent un plancher au-delà duquel on ne descend pas.
 * Mieux vaut afficher moins de texte que du texte qu'on ne peut pas lire.
 */
#define TEXT_HUGE 0.80f   /**< 24 px : horloge du mode cadre. */
#define TEXT_TITLE 0.66f  /**< 20 px : titre de morceau, heure. */
#define TEXT_LARGE 0.58f  /**< 17 px : titres de page, valeurs importantes. */
#define TEXT_BODY 0.52f   /**< 16 px : libellés de boutons, texte courant. */
#define TEXT_SMALL 0.46f  /**< 14 px : informations secondaires. */
#define TEXT_MICRO 0.42f  /**< 13 px : plus petite taille encore lisible. */

/** Hauteur en pixels d'une ligne à l'échelle donnée. */
#define TEXT_LINE_PX(scale) ((scale) * 30.0f)

/** Alloue les tampons de texte. À appeler après `C2D_Init`. */
bool text_init(void);

/** Indique si la police embarquée a pu être chargée. */
bool text_has_custom_font(void);

/** Libère les tampons. */
void text_exit(void);

/** Vide le tampon de glyphes. À appeler une fois par frame, avant tout dessin. */
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
