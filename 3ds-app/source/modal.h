/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file modal.h
 * @brief Panneau modal de réglages continus.
 *
 * Un volume est une valeur continue : l'exprimer avec des boutons plus et moins
 * oblige à multiplier les appuis et les échanges réseau. Un curseur que l'on
 * fait glisser atteint la valeur voulue d'un seul geste, et laisse voir les deux
 * volumes simultanément.
 *
 * Le panneau est modal : tant qu'il est ouvert, il reçoit seul les commandes.
 * Cela évite de déclencher une action de la grille par mégarde.
 */
#pragma once

#include <stdbool.h>

#include "app.h"

/** Curseurs du panneau. */
typedef enum {
	MODAL_ROW_SYSTEM = 0, /**< Volume du système. */
	MODAL_ROW_MUSIC,      /**< Volume interne du lecteur. */
	MODAL_ROW_OUTPUT,     /**< Sortie audio. */
	MODAL_ROW_MUTES,      /**< Boutons de coupure. */
	MODAL_ROW_COUNT,
} ModalRow;

typedef struct {
	bool active;
	/** Ligne sélectionnée, pour la navigation à la croix. */
	int row;

	/**
	 * Valeurs en cours d'édition.
	 *
	 * Pendant un glissement, l'affichage suit le doigt sans attendre la réponse
	 * de l'ordinateur : sans cela, le curseur paraîtrait accrocher.
	 */
	int system_volume;
	int music_volume;
	bool editing_system;
	bool editing_music;

	/** Curseur actuellement manipulé, -1 si aucun. */
	int dragging;
	/** Interrupteur désigné sur la ligne des coupures : 0 ou 1. */
	int mute_focus;

	/** Temps écoulé depuis le dernier envoi, pour espacer les messages. */
	float send_timer;
	/** Vrai si une valeur reste à transmettre. */
	bool pending;

	float appear;
} Modal;

/** Ouvre le panneau, en reprenant les valeurs connues de l'état courant. */
void modal_open(Modal *modal, const App *app);

/** Ferme le panneau. */
void modal_close(Modal *modal);

/** Fait progresser les animations et les envois différés. */
void modal_update(Modal *modal, App *app, float dt);

/** Dessine le panneau sur l'écran tactile. */
void modal_draw(const Modal *modal, const App *app);

/** Dessine le rappel du panneau sur l'écran supérieur. */
void modal_draw_top(const Modal *modal, const App *app);

/**
 * Traite un contact tactile.
 * Retourne `true` si le panneau a consommé le geste.
 */
bool modal_touch(Modal *modal, App *app, float x, float y, bool pressed,
                 bool released);

/** Traite les boutons physiques. */
void modal_buttons(Modal *modal, App *app, u32 pressed);
