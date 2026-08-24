/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file theme.h
 * @brief Palette et constantes de mise en page.
 *
 * Les couleurs sont au format C2D (ABGR little-endian) via C2D_Color32.
 */
#pragma once

#include <3ds.h>
#include <citro2d.h>

/* --- Dimensions des écrans --- */
#define SCREEN_TOP_W 400
#define SCREEN_BOTTOM_W 320
#define SCREEN_H 240

/* --- Grille de boutons (écran bas) --- */
#define GRID_COLS 3
#define GRID_ROWS 2
#define GRID_SLOTS (GRID_COLS * GRID_ROWS)

#define GRID_MARGIN_X 10.0f
#define GRID_TOP 40.0f
#define GRID_BOTTOM_BAR 36.0f
#define GRID_GAP 8.0f

/* --- Profondeurs de rendu --- */
#define Z_BG 0.0f
#define Z_CARD 0.1f
#define Z_CONTENT 0.2f
#define Z_OVERLAY 0.4f

/*
 * Plans réservés aux panneaux modaux.
 *
 * Un panneau doit recouvrir entièrement la page qu'il masque. Réutiliser les
 * profondeurs ordinaires le faisait se mêler aux boutons : le voile passait
 * sous eux, sans rien assombrir, et les icônes de la grille ressortaient
 * par-dessus le contenu du panneau.
 *
 * Ces valeurs restent inférieures à 1 pour demeurer dans la plage de
 * profondeur admise.
 */
#define Z_MODAL_VEIL 0.55f    /**< Voile masquant la page. */
#define Z_MODAL_CARD 0.65f    /**< Fond du panneau. */
#define Z_MODAL_CONTENT 0.75f /**< Texte et curseurs du panneau. */
#define Z_MODAL_TOP 0.85f     /**< Poignées et éléments de premier plan. */

/* Palette sombre, teintée bleu nuit. */
#define COL_BG C2D_Color32(0x0B, 0x0E, 0x15, 0xFF)
#define COL_BG_ALT C2D_Color32(0x11, 0x15, 0x1F, 0xFF)
#define COL_SURFACE C2D_Color32(0x1A, 0x1F, 0x2C, 0xFF)
#define COL_SURFACE_HI C2D_Color32(0x25, 0x2C, 0x3D, 0xFF)
#define COL_SURFACE_LO C2D_Color32(0x14, 0x18, 0x23, 0xFF)
#define COL_BORDER C2D_Color32(0x2C, 0x34, 0x47, 0xFF)

#define COL_TEXT C2D_Color32(0xEC, 0xF0, 0xF7, 0xFF)
#define COL_TEXT_DIM C2D_Color32(0x8C, 0x98, 0xAE, 0xFF)
#define COL_TEXT_FAINT C2D_Color32(0x5C, 0x67, 0x7C, 0xFF)

#define COL_ACCENT C2D_Color32(0x6E, 0xE7, 0xB7, 0xFF)
#define COL_BLUE C2D_Color32(0x3B, 0x82, 0xF6, 0xFF)
#define COL_OK C2D_Color32(0x34, 0xD3, 0x99, 0xFF)
#define COL_WARN C2D_Color32(0xF5, 0x9E, 0x0B, 0xFF)
#define COL_ERR C2D_Color32(0xEF, 0x44, 0x44, 0xFF)

#define COL_SHADOW C2D_Color32(0x00, 0x00, 0x00, 0x55)
#define COL_WHITE C2D_Color32(0xFF, 0xFF, 0xFF, 0xFF)

/** Construit une couleur depuis des composantes RGB et un alpha. */
static inline u32 theme_rgba(u8 r, u8 g, u8 b, u8 a)
{
	return C2D_Color32(r, g, b, a);
}

/** Applique un facteur multiplicatif sur la luminosité d'une couleur C2D. */
u32 theme_scale(u32 color, float factor);

/** Mélange deux couleurs. `t` vaut 0 pour `a`, 1 pour `b`. */
u32 theme_mix(u32 a, u32 b, float t);

/** Remplace l'alpha d'une couleur. */
u32 theme_alpha(u32 color, u8 alpha);

/**
 * Analyse une couleur `#RRGGBB` ou `#RGB`.
 * Retourne `fallback` si la chaîne est invalide.
 */
u32 theme_parse_hex(const char *text, u32 fallback);
