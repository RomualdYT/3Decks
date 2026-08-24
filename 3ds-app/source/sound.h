/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file sound.h
 * @brief Retour sonore de l'interface.
 *
 * Les sons sont synthétisés au démarrage plutôt que chargés depuis des fichiers.
 * Ils occupent ainsi quelques kilooctets de mémoire au lieu d'alourdir
 * l'application, et leur timbre se règle en modifiant quelques valeurs.
 *
 * Chaque son reste très bref : un retour tactile doit se percevoir sans jamais
 * retarder la sensation d'immédiateté.
 */
#pragma once

#include <stdbool.h>

typedef enum {
	SOUND_TAP = 0,   /**< Appui sur un bouton. */
	SOUND_TOGGLE,    /**< Activation ou désactivation d'un état. */
	SOUND_PAGE,      /**< Changement de page. */
	SOUND_ERROR,     /**< Action refusée ou échouée. */
	SOUND_CONNECT,   /**< Liaison établie avec l'ordinateur. */
	SOUND_COUNT,
} SoundId;

/**
 * Prépare le service audio et synthétise les sons.
 * Retourne `false` si l'audio est indisponible ; l'application reste alors
 * utilisable, simplement silencieuse.
 */
bool sound_init(void);

/** Libère les ressources audio. */
void sound_exit(void);

/** Active ou coupe le retour sonore. */
void sound_set_enabled(bool enabled);

/** Joue un son, sans effet si le retour sonore est coupé. */
void sound_play(SoundId id);
