/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file ui.h
 * @brief Rendu des deux écrans.
 */
#pragma once

#include "app.h"

/** Dessine l'écran supérieur : dashboard contextuel. */
void ui_draw_top(const App *app);

/** Dessine l'écran inférieur : grille de contrôle. */
void ui_draw_bottom(const App *app);

/**
 * Retourne l'emplacement de la grille situé sous le point (`x`, `y`),
 * ou -1 si le point est en dehors des boutons.
 */
int ui_slot_at(float x, float y);

/** Indique si le point touché correspond à l'onglet de page `index`. */
int ui_tab_at(float x, float y, int page_count);

/** Indique si le point touché correspond au bouton des réglages. */
bool ui_settings_at(float x, float y);

/** Bouton élargi affiché pendant la connexion et l'attente du PC. */
bool ui_waiting_settings_at(float x, float y);

/**
 * Élément de liste situé sous le point touché, ou -1.
 * Ne concerne que les pages en présentation `LAYOUT_LIST`.
 */
int ui_list_at(const App *app, float x, float y);

/** Défilement maximal de la liste courante, en rangées. */
float ui_list_max_scroll(const App *app);

/** Nombre de colonnes de la présentation en liste. */
int ui_list_columns(void);

/** Nombre de rangées entièrement visibles. */
int ui_list_rows(void);
