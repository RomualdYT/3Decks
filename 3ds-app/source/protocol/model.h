/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file model.h
 * @brief Modèle de données de l'application : configuration, état, notification.
 *
 * Toutes les tailles sont bornées à la compilation. Une configuration reçue du
 * PC qui dépasse ces bornes est tronquée ou rejetée, jamais copiée au-delà.
 */
#pragma once

#include <stdbool.h>

#include "theme.h"

#define MAX_PAGES 12
#define MAX_BUTTONS GRID_SLOTS

/** Éléments d'une page en mode liste. */
#define MAX_ENTRIES 32

/** Notifications conservées pour l'affichage. */
#define MAX_NOTIFICATIONS 4

/** Longueur de la ligne secondaire d'un élément de liste. */
#define LEN_DETAIL 41

#define LEN_ID 33
#define LEN_LABEL 25
#define LEN_TITLE 25
#define LEN_TEXT 65
#define LEN_ICON 17
#define LEN_STATE_KEY 25

/** Icônes vectorielles dessinées par `icons.c`. */
typedef enum {
	ICON_NONE = 0,
	ICON_MIC,
	ICON_MIC_OFF,
	ICON_VOLUME_UP,
	ICON_VOLUME_DOWN,
	ICON_VOLUME_MUTE,
	ICON_PLAY,
	ICON_PAUSE,
	ICON_NEXT,
	ICON_PREVIOUS,
	ICON_APP,
	ICON_BROWSER,
	ICON_TERMINAL,
	ICON_FOLDER,
	ICON_MUSIC,
	ICON_CHAT,
	ICON_VIDEO,
	ICON_RECORD,
	ICON_LOCK,
	ICON_PAGE,
	ICON_POWER,
	ICON_GEAR,
	ICON_STAR,
	ICON_COUNT,
} IconId;

/** Mode d'affichage de l'écran supérieur. */
typedef enum {
	DASH_AUTO = 0, /**< Média si de la musique joue, sinon applications. */
	DASH_MEDIA,
	DASH_SYSTEM,
	DASH_APPS,
	DASH_AUDIO, /**< Volumes, sortie active et égaliseur animé. */
	DASH_FRAME,        /**< Cadre à musique : pochette plein écran. */
	DASH_NOTIFICATIONS, /**< Notifications récentes du système. */
	DASH_EXTENSION, /**< Cartes déclaratives fournies par une extension. */
} DashboardMode;

typedef struct {
	char id[LEN_ID];
	char label[LEN_LABEL];
	char hold_label[LEN_LABEL];
	IconId icon;
	u32 color;
	/** Clé d'état pilotant l'apparence active, vide si le bouton est neutre. */
	char toggle[LEN_STATE_KEY];
	bool used;

	/* Animation d'appui, non transmise par le réseau. */
	float press;
} Button;

/** Présentation d'une page. */
typedef enum {
	LAYOUT_GRID = 0, /**< Grille de boutons, pour des actions fixes. */
	LAYOUT_LIST,     /**< Liste défilante, pour un contenu de longueur variable. */
} PageLayout;

/**
 * Élément d'une page en mode liste.
 *
 * Deux lignes de texte plutôt qu'une : le libellé nomme l'application, le détail
 * permet de distinguer deux fenêtres de la même application.
 */
typedef struct {
	char id[LEN_ID];
	char label[LEN_LABEL];
	char detail[LEN_DETAIL];
	IconId icon;
	u32 color;
	bool active;
	bool used;
} ListEntry;

typedef struct {
	char id[LEN_ID];
	char title[LEN_TITLE];
	/** Icône de l'onglet, plus lisible qu'un numéro sur une barre étroite. */
	IconId icon;
	DashboardMode dashboard;
	PageLayout layout;
	Button buttons[MAX_BUTTONS];
	ListEntry entries[MAX_ENTRIES];
	int entry_count;
	bool used;
} Page;

typedef struct {
	int revision;
	Page pages[MAX_PAGES];
	int page_count;
} Config;

#define MAX_APPS 8
#define MAX_OUTPUTS 6
#define LEN_APP_NAME 25

#define MAX_EXTENSION_CARDS 4
#define MAX_EXTENSION_BUTTONS (MAX_PAGES * MAX_BUTTONS)
typedef struct {
	char label[LEN_LABEL];
	char value[LEN_DETAIL];
	char detail[LEN_TEXT];
	int progress; /**< -1 si aucune jauge. */
} ExtensionCard;

typedef struct {
	char page[LEN_ID];
	char title[LEN_TEXT];
	int status; /**< 0 neutre, 1 OK, 2 avertissement, 3 erreur. */
	int count;
	ExtensionCard cards[MAX_EXTENSION_CARDS];
} ExtensionPanel;

typedef struct {
	char page[LEN_ID];
	char id[LEN_ID];
	bool active;
	bool available;
} ExtensionButtonState;

/** État courant du PC, reçu par patchs successifs. */
typedef struct {
	int volume; /**< 0..100, -1 si inconnu. */
	/** Volume interne du lecteur, indépendant du système. -1 si inconnu. */
	int app_volume;
	bool muted;
	bool mic_muted;
	bool mic_known;

	char media_title[LEN_TEXT];
	char media_artist[LEN_TEXT];
	char media_album[LEN_TEXT];
	/** Couleur dominante de la pochette, accent de l'interface. */
	u32 media_accent;
	bool media_accent_known;
	char media_app[LEN_APP_NAME];
	bool media_playing;
	bool media_present;
	/** Jeton de la pochette annoncée par le PC, 0 si aucune. */
	u32 media_art;
	/** Position de lecture et durée, en secondes. -1 si inconnues. */
	int media_position;
	int media_duration;

	char active_app[LEN_APP_NAME];
	char apps[MAX_APPS][LEN_APP_NAME];
	int app_count;

	int cpu;    /**< 0..100, -1 si inconnu. */
	int memory; /**< 0..100, -1 si inconnu. */
	/** Détails facultatifs du cockpit de performances. */
	int memory_used_mb;
	int memory_total_mb;
	int disk; /**< Occupation du disque système, 0..100. */
	int disk_free_mb;
	int disk_total_mb;
	int network_down_kbps;
	int network_up_kbps;
	char top_process[LEN_APP_NAME];
	int top_process_cpu;
	int gpu;         /**< 0..100, -1 si le pilote ne l'expose pas. */
	int temperature; /**< Degrés Celsius, -1 si indisponible. */

	char host[LEN_APP_NAME];
	char time[8];  /**< "HH:MM" fourni par le PC. */
	char date[24]; /**< Date lisible fournie par le PC. */

	/** Notifications récentes, de la plus récente à la plus ancienne. */
	struct {
		char app[LEN_APP_NAME];
		char title[LEN_TEXT];
		char body[LEN_TEXT];
		IconId icon;
		int age; /**< Ancienneté en secondes. */
	} notifications[MAX_NOTIFICATIONS];
	int notification_count;
	/** Nombre total signalé par l'ordinateur, au-delà de ce qui est transmis. */
	int notification_total;

	/** Sortie audio active et sorties disponibles. */
	char audio_output[LEN_APP_NAME];
	char audio_outputs[MAX_OUTPUTS][LEN_APP_NAME];
	int audio_output_count;

	ExtensionPanel extension_panels[MAX_PAGES];
	int extension_panel_count;
	ExtensionButtonState extension_buttons[MAX_EXTENSION_BUTTONS];
	int extension_button_count;
} PcState;

/** Notification éphémère affichée sur l'écran supérieur. */
typedef struct {
	char text[LEN_TEXT];
	bool error;
	/** Icône affichée, `ICON_NONE` pour l'icône par défaut. */
	IconId icon;
	float ttl;   /**< Secondes restantes avant disparition. */
	float alpha; /**< Opacité courante, lissée. */
} Toast;

typedef enum {
	LINK_OFFLINE = 0,
	LINK_CONNECTING,
	LINK_ONLINE,
} LinkStatus;

/** Réinitialise une configuration à l'état vide. */
void model_config_clear(Config *config);

/** Réinitialise un état PC (valeurs inconnues). */
void model_state_clear(PcState *state);

/** Traduit un nom d'icône du protocole en identifiant. */
IconId model_icon_from_name(const char *name);

/** Traduit un nom de mode de dashboard. */
DashboardMode model_dashboard_from_name(const char *name);

/** Retourne la page d'index donné, ou NULL. */
const Page *model_page_at(const Config *config, int index);

/** Cherche l'index d'une page par identifiant, -1 si absente. */
int model_find_page(const Config *config, const char *id);

/**
 * Évalue la clé d'état d'un bouton.
 * Retourne `true` si l'état correspondant est actif (micro coupé, lecture en
 * cours, son coupé...). Une clé inconnue retourne `false`.
 */
bool model_toggle_active(const PcState *state, const char *key);
