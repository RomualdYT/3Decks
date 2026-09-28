#pragma once
#include "setup.h"
#include <3ds.h>
#include <stddef.h>
/** Nombre de lignes de l'écran de réglages. */
#define SETTINGS_ROWS 7

/* Indices des lignes de réglages. */
enum {
	ROW_LANGUAGE = 0,
	ROW_CONNECTION,
	ROW_SOUND,
	ROW_DIM,
	ROW_STEREO,
	ROW_COMPANION,
	ROW_RESET,
};

/** Hauteur du bouton principal. */
#define PRIMARY_BUTTON_H 36.0f

/** Marge sous le bouton principal. */
#define PRIMARY_BUTTON_MARGIN 10.0f

/** Première ligne de liste, sous le titre. */
#define ROWS_TOP 36.0f

/** Carte de choix de langue : hauteur et pas vertical. */
#define LANG_CARD_H 48.0f
#define LANG_CARD_PITCH 58.0f

/** Espace laissé entre la dernière ligne et le bouton. */
#define ROWS_GAP 8.0f

/** Espace vertical réellement disponible pour les lignes. */
#define ROWS_AVAILABLE                                                        \
	(SCREEN_H - PRIMARY_BUTTON_MARGIN - PRIMARY_BUTTON_H - ROWS_GAP - ROWS_TOP)

#define AGENT_CARD_TOP 38.0f
#define AGENT_CARD_H 34.0f
#define AGENT_CARD_GAP 5.0f
#define AGENT_VISIBLE 3
#define MANUAL_CARD_Y 160.0f


void begin_connection_step(Setup *setup);
void start_probe(Setup *setup, App *app);
bool prompt_text(const char *hint, char *value, size_t size, SwkbdType type, int max_length);
bool prompt_pairing_code(App *app);
bool select_discovered_agent(Setup *setup, App *app, int index);
void primary_button_bounds(float *x, float *y, float *w, float *h);
void row_bounds(int index, float *y, float *height);
int first_visible_agent(const Setup *setup);
void agent_card_bounds(int index, float *y);
