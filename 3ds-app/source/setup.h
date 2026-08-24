/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file setup.h
 * @brief Assistant de premier démarrage et écran de réglages.
 *
 * Au premier lancement, l'utilisateur choisit sa langue puis l'adresse de son
 * ordinateur, et peut vérifier la liaison avant de commencer. Cet
 * accompagnement évite d'avoir à éditer un fichier sur la carte SD, ce qui
 * était jusqu'ici la seule façon de configurer l'application.
 *
 * Le même écran sert ensuite de page de réglages, accessible à tout moment.
 */
#pragma once

#include "app.h"

/** Étapes de l'assistant. */
typedef enum {
	SETUP_LANGUAGE = 0,
	SETUP_HOST,
	SETUP_DONE,
	SETUP_STEP_COUNT,
} SetupStep;

/** Résultat du test de connexion en cours. */
typedef enum {
	PROBE_IDLE = 0,
	PROBE_RUNNING,
	PROBE_SUCCESS,
	PROBE_FAILURE,
} ProbeState;

typedef struct {
	bool active;      /**< Vrai si l'assistant ou les réglages sont affichés. */
	bool first_run;   /**< Vrai lors du tout premier démarrage. */
	SetupStep step;
	int selection;    /**< Ligne sélectionnée dans les réglages. */
	ProbeState probe;
	float probe_time; /**< Durée écoulée depuis le début du test. */
} Setup;

/** Prépare l'assistant. `first_run` déclenche le parcours guidé. */
void setup_begin(Setup *setup, bool first_run);

/** Ouvre l'écran de réglages, hors premier démarrage. */
void setup_open_settings(Setup *setup);

/** Ferme l'écran. */
void setup_close(Setup *setup);

/** Fait progresser les animations et le test de connexion. */
void setup_update(Setup *setup, App *app, float dt);

/** Dessine l'écran supérieur de l'assistant. */
void setup_draw_top(const Setup *setup, const App *app);

/** Dessine l'écran tactile de l'assistant. */
void setup_draw_bottom(const Setup *setup, const App *app);

/**
 * Traite un appui tactile.
 * Retourne `true` si l'appui a été consommé par l'assistant.
 */
bool setup_touch(Setup *setup, App *app, float x, float y);

/** Traite les boutons physiques. */
void setup_buttons(Setup *setup, App *app, u32 pressed);
