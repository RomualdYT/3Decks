/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file i18n.h
 * @brief Traduction de l'interface.
 *
 * Les textes sont désignés par une clé et non par leur contenu : ajouter une
 * langue revient à compléter une table, sans toucher au code d'affichage.
 *
 * L'anglais est la langue par défaut, afin que l'application reste
 * compréhensible par le plus grand nombre dès le premier lancement. La langue
 * de la console est détectée pour proposer un choix pertinent, mais
 * l'utilisateur reste libre de la changer.
 */
#pragma once

#include <stdbool.h>

typedef enum {
	LANG_EN = 0,
	LANG_FR,
	LANG_COUNT,
} Language;

/** Clés de traduction. L'ordre doit correspondre aux tables de `i18n.c`. */
typedef enum {
	/* État de la liaison */
	STR_CONNECTED,
	STR_CONNECTING,
	STR_OFFLINE,
	STR_WAITING_PC,
	STR_RECEIVING_CONFIG,
	STR_PC_NOT_FOUND,
	STR_CONNECTING_TO_PC,
	STR_RETRY_IN,
	STR_DETECTED_VIA_LINK,
	STR_PC_DISCONNECTED,
	STR_AGENT_UNAVAILABLE,
	STR_CONNECTION_LOST,
	STR_CONNECTION_STALE,

	/* Média */
	STR_NOTHING_PLAYING,
	STR_PLAYING,
	STR_PAUSED,

	/* Micro et audio */
	STR_MIC_UNKNOWN,
	STR_MIC_ACTIVE,
	STR_MIC_MUTED,
	STR_AUDIO_OUTPUT,
	STR_OUTPUT_UNKNOWN,
	STR_MUSIC,
	STR_SYSTEM_AUDIO,
	STR_COMPUTER,

	/* Tableau de bord système */
	STR_FOREGROUND,
	STR_UNKNOWN,
	STR_NO_APPS,
	STR_NOTIFICATIONS,
	STR_NO_NOTIFICATIONS,
	STR_TOUCH_TO_WAKE,
	STR_BATTERY,
	/* Libellés du panneau de volumes : ils nomment l'objet, l'état étant
	   exprimé par la couleur et l'icône. */
	STR_SPEAKERS,
	STR_MICROPHONE,
	STR_MUTED,
	STR_LIVE,
	STR_PROCESSOR,
	STR_MEMORY,
	STR_PERFORMANCE_HEALTHY,
	STR_PERFORMANCE_BUSY,
	STR_PERFORMANCE_ALERT,
	STR_PERFORMANCE_WAITING,
	STR_NETWORK,
	STR_STORAGE,
	STR_GRAPHICS,
	STR_DOWNLOAD,
	STR_UPLOAD,
	STR_TOP_PROCESS,
	STR_LAST_30_SECONDS,
	STR_VOLUME,
	STR_VOLUMES,
	STR_VOLUME_PC,

	/* Erreurs d'action */
	STR_ACTION_REFUSED,
	STR_COMMAND_TOO_LONG,
	STR_SEND_FAILED,
	STR_NETWORK_UNAVAILABLE,
	STR_CONFIG_REQUESTED,

	/* Premier démarrage */
	STR_WELCOME_TITLE,
	STR_WELCOME_SUBTITLE,
	STR_CHOOSE_LANGUAGE,
	STR_SETUP_STEP_LANGUAGE,
	STR_SETUP_STEP_HOST,
	STR_SETUP_STEP_DONE,
	STR_SETUP_HOST_TITLE,
	STR_SETUP_HOST_HELP,
	STR_SETUP_HOST_EDIT,
	STR_SETUP_AUTO_DETECT,
	STR_SETUP_SEARCHING,
	STR_SETUP_NO_AGENT,
	STR_SETUP_AGENTS_FOUND,
	STR_SETUP_SEARCH_AGAIN,
	STR_SETUP_MANUAL,
	STR_SETUP_AUTOMATIC,
	STR_SETUP_CONNECT,
	STR_SETUP_PAIR_CODE,
	STR_SETUP_PAIR_HELP,
	STR_PAIRING_REQUIRED,
	STR_PAIRING_SAVED,
	STR_SETUP_TEST,
	STR_SETUP_TESTING,
	STR_SETUP_TEST_OK,
	STR_SETUP_TEST_FAIL,
	STR_SETUP_FINISH,
	STR_SETUP_DONE_TITLE,
	STR_SETUP_DONE_HELP,
	STR_CONTINUE,
	STR_BACK,
	STR_NEXT,

	/* Réglages */
	STR_SETTINGS,
	STR_SETTINGS_LANGUAGE,
	STR_SETTINGS_SOUND,
	STR_SETTINGS_DIM,
	STR_SETTINGS_STEREO,
	STR_SETTINGS_COMPUTER,
	STR_SETTINGS_HOST,
	STR_SETTINGS_PORT,
	STR_SETTINGS_RECONNECT,
	STR_SETTINGS_SAVE,
	STR_SETTINGS_SAVED,
	STR_SETTINGS_SAVE_FAILED,
	STR_SETTINGS_RESET_SETUP,
	STR_ON,
	STR_OFF,
	STR_NEVER,
	STR_SECONDS,

	/* Aide sur les commandes */
	STR_HELP_TOUCH,
	STR_HELP_PAGES,
	STR_HELP_RELOAD,
	STR_HELP_QUIT,

	STR_EXTENSION_WAITING,
	STR_EXTENSION_UNAVAILABLE,
	STR_COUNT,
} StringId;

/** Définit la langue courante. */
void i18n_set_language(Language language);

/** Langue courante. */
Language i18n_language(void);

/** Nom de la langue, dans cette langue même. */
const char *i18n_language_name(Language language);

/**
 * Langue déduite des réglages de la console.
 * Retourne `LANG_EN` si la console n'utilise aucune langue prise en charge.
 */
Language i18n_detect_system_language(void);

/** Texte associé à une clé, dans la langue courante. */
const char *tr(StringId id);
