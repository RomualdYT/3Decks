/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file draw.h
 * @brief Primitives de dessin de plus haut niveau que citro2d.
 *
 * citro2d fournit rectangles, ellipses, triangles et lignes. Les formes
 * arrondies, anneaux, arcs et étoiles sont composés ici afin que l'interface
 * reste lisible et cohérente.
 *
 * Note de performance : citro2d change d'état interne entre le mode « cercle »
 * et le mode normal, ce qui coûte cher. On regroupe donc les formes circulaires
 * autant que possible dans l'ordre de rendu.
 */
#pragma once

#include <3ds.h>
#include <citro2d.h>

/** Rectangle plein. */
void draw_rect(float x, float y, float w, float h, float z, u32 color);

/** Rectangle à dégradé vertical. */
void draw_rect_vgrad(float x, float y, float w, float h, float z, u32 top,
                     u32 bottom);

/** Rectangle aux coins arrondis. */
void draw_round_rect(float x, float y, float w, float h, float radius, float z,
                     u32 color);

/** Rectangle arrondi à dégradé vertical. */
void draw_round_rect_vgrad(float x, float y, float w, float h, float radius,
                           float z, u32 top, u32 bottom);

/** Contour de rectangle arrondi, d'épaisseur `thickness`. */
void draw_round_rect_outline(float x, float y, float w, float h, float radius,
                             float thickness, float z, u32 color);

/** Disque plein. */
void draw_circle(float cx, float cy, float radius, float z, u32 color);

/** Anneau d'épaisseur `thickness`. */
void draw_ring(float cx, float cy, float radius, float thickness, float z,
               u32 color);

/** Anneau elliptique. */
void draw_ellipse_ring(float cx, float cy, float rx, float ry, float thickness,
                       float z, u32 color);

/**
 * Arc de cercle. `start` et `sweep` sont exprimés en tours (1.0 = 360°),
 * l'origine étant en haut et le sens horaire.
 */
void draw_arc(float cx, float cy, float radius, float thickness, float start,
              float sweep, float z, u32 color);

/** Segment épais. */
void draw_line(float x0, float y0, float x1, float y1, float thickness, float z,
               u32 color);

/** Triangle plein. */
void draw_triangle(float x0, float y0, float x1, float y1, float x2, float y2,
                   float z, u32 color);

/** Rayon partant du centre, utilisé pour les dents d'engrenage. */
void draw_spoke(float cx, float cy, float angle, float inner, float outer,
                float thickness, float z, u32 color);

/** Étoile à cinq branches. */
void draw_star(float cx, float cy, float outer, float inner, float z,
               u32 color);

/** Barre de progression arrondie. `ratio` est borné à [0, 1]. */
void draw_progress(float x, float y, float w, float h, float ratio, float z,
                   u32 track, u32 fill);

/** Ombre portée douce sous un rectangle arrondi. */
void draw_shadow(float x, float y, float w, float h, float radius, float z);
