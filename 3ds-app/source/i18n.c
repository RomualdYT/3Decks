#include "i18n.h"

#include <3ds.h>
#include <stddef.h>

static Language s_language = LANG_EN;

/*
 * Tables de traduction.
 *
 * Chaque table suit exactement l'ordre de l'énumération `StringId`. Une
 * vérification à la compilation garantit qu'aucune entrée ne manque : oublier
 * une traduction produirait sinon un décalage silencieux de tous les textes
 * suivants, bien plus difficile à repérer qu'une erreur de compilation.
 */

static const char *const kEnglish[STR_COUNT] = {
    /* Liaison */
    [STR_CONNECTED] = "Connected",
    [STR_CONNECTING] = "Connecting",
    [STR_OFFLINE] = "Offline",
    [STR_WAITING_PC] = "Waiting for PC",
    [STR_RECEIVING_CONFIG] = "Receiving layout",
    [STR_PC_NOT_FOUND] = "PC not found",
    [STR_CONNECTING_TO_PC] = "Connecting to PC",
    [STR_RETRY_IN] = "Retrying in %.0f s",
    [STR_DETECTED_VIA_LINK] = "address detected via 3dslink",
    [STR_PC_DISCONNECTED] = "PC disconnected",

    /* Média */
    [STR_NOTHING_PLAYING] = "Nothing playing",
    [STR_PLAYING] = "Playing",
    [STR_PAUSED] = "Paused",

    /* Micro et audio */
    [STR_MIC_UNKNOWN] = "Mic ?",
    [STR_MIC_ACTIVE] = "Mic live",
    [STR_MIC_MUTED] = "Mic muted",
    [STR_AUDIO_OUTPUT] = "AUDIO OUTPUT",
    [STR_OUTPUT_UNKNOWN] = "Unknown",
    [STR_MUSIC] = "Music",
    [STR_COMPUTER] = "COMPUTER",

    /* Système */
    [STR_FOREGROUND] = "IN FOREGROUND",
    [STR_UNKNOWN] = "Unknown",
    [STR_NO_APPS] = "No app reported",
    [STR_NOTIFICATIONS] = "NOTIFICATIONS",
    [STR_NO_NOTIFICATIONS] = "Nothing new",
    [STR_TOUCH_TO_WAKE] = "Touch to wake",
    [STR_BATTERY] = "Battery",
    [STR_SPEAKERS] = "Speakers",
    [STR_MICROPHONE] = "Microphone",
    [STR_MUTED] = "Muted",
    [STR_LIVE] = "Live",
    [STR_PROCESSOR] = "PROCESSOR",
    [STR_MEMORY] = "MEMORY",
    [STR_VOLUME] = "VOLUME",
    [STR_VOLUMES] = "Volumes",
    [STR_VOLUME_PC] = "PC",

    /* Erreurs */
    [STR_ACTION_REFUSED] = "Action refused",
    [STR_COMMAND_TOO_LONG] = "Command too long",
    [STR_SEND_FAILED] = "Could not send",
    [STR_NETWORK_UNAVAILABLE] = "Network unavailable",
    [STR_CONFIG_REQUESTED] = "Layout requested",

    /* Premier démarrage */
    [STR_WELCOME_TITLE] = "Welcome to Deck3DS",
    [STR_WELCOME_SUBTITLE] = "Turn your console into a control surface",
    [STR_CHOOSE_LANGUAGE] = "Choose your language",
    [STR_SETUP_STEP_LANGUAGE] = "Language",
    [STR_SETUP_STEP_HOST] = "Computer",
    [STR_SETUP_STEP_DONE] = "Ready",
    [STR_SETUP_HOST_TITLE] = "Where is your computer?",
    [STR_SETUP_HOST_HELP] = "The agent shows its address when it starts.",
    [STR_SETUP_HOST_EDIT] = "Edit address",
    [STR_SETUP_AUTO_DETECT] = "Detected automatically",
    [STR_SETUP_TEST] = "Test connection",
    [STR_SETUP_TESTING] = "Testing...",
    [STR_SETUP_TEST_OK] = "Connection works",
    [STR_SETUP_TEST_FAIL] = "No answer from this address",
    [STR_SETUP_FINISH] = "Start using Deck3DS",
    [STR_SETUP_DONE_TITLE] = "All set",
    [STR_SETUP_DONE_HELP] = "Buttons come from the agent. Edit config.json to "
                            "change them, no rebuild needed.",
    [STR_CONTINUE] = "Continue",
    [STR_BACK] = "Back",
    [STR_NEXT] = "Next",

    /* Réglages */
    [STR_SETTINGS] = "Settings",
    [STR_SETTINGS_LANGUAGE] = "Language",
    [STR_SETTINGS_SOUND] = "Touch feedback",
    [STR_SETTINGS_DIM] = "Dim screen after",
    [STR_SETTINGS_STEREO] = "3D depth",
    [STR_SETTINGS_HOST] = "Computer address",
    [STR_SETTINGS_PORT] = "Port",
    [STR_SETTINGS_RECONNECT] = "Reconnect now",
    [STR_SETTINGS_SAVE] = "Save",
    [STR_SETTINGS_SAVED] = "Settings saved",
    [STR_SETTINGS_SAVE_FAILED] = "Could not save to SD card",
    [STR_SETTINGS_RESET_SETUP] = "Run setup again",
    [STR_ON] = "On",
    [STR_OFF] = "Off",
    [STR_NEVER] = "Never",
    [STR_SECONDS] = "s",

    /* Aide */
    [STR_HELP_TOUCH] = "Tap a button to run it, hold for its second action",
    [STR_HELP_PAGES] = "L / R or the D-pad switch pages",
    [STR_HELP_RELOAD] = "SELECT reloads the layout",
    [STR_HELP_QUIT] = "START quits",
};

static const char *const kFrench[STR_COUNT] = {
    /* Liaison */
    [STR_CONNECTED] = "Connecté",
    [STR_CONNECTING] = "Connexion",
    [STR_OFFLINE] = "Hors ligne",
    [STR_WAITING_PC] = "En attente du PC",
    [STR_RECEIVING_CONFIG] = "Réception de la configuration",
    [STR_PC_NOT_FOUND] = "PC introuvable",
    [STR_CONNECTING_TO_PC] = "Connexion au PC",
    [STR_RETRY_IN] = "Nouvelle tentative dans %.0f s",
    [STR_DETECTED_VIA_LINK] = "adresse détectée via 3dslink",
    [STR_PC_DISCONNECTED] = "PC déconnecté",

    /* Média */
    [STR_NOTHING_PLAYING] = "Aucune lecture",
    [STR_PLAYING] = "Lecture",
    [STR_PAUSED] = "Pause",

    /* Micro et audio */
    [STR_MIC_UNKNOWN] = "Micro ?",
    [STR_MIC_ACTIVE] = "Micro actif",
    [STR_MIC_MUTED] = "Micro coupé",
    [STR_AUDIO_OUTPUT] = "SORTIE AUDIO",
    [STR_OUTPUT_UNKNOWN] = "Inconnue",
    [STR_MUSIC] = "Musique",
    [STR_COMPUTER] = "ORDINATEUR",

    /* Système */
    [STR_FOREGROUND] = "AU PREMIER PLAN",
    [STR_UNKNOWN] = "Inconnu",
    [STR_NO_APPS] = "Aucune application signalée",
    [STR_NOTIFICATIONS] = "NOTIFICATIONS",
    [STR_NO_NOTIFICATIONS] = "Rien de nouveau",
    [STR_TOUCH_TO_WAKE] = "Touchez pour réveiller",
    [STR_BATTERY] = "Batterie",
    [STR_SPEAKERS] = "Sortie",
    [STR_MICROPHONE] = "Microphone",
    [STR_MUTED] = "Coupé",
    [STR_LIVE] = "Actif",
    [STR_PROCESSOR] = "PROCESSEUR",
    [STR_MEMORY] = "MÉMOIRE",
    [STR_VOLUME] = "VOLUME",
    [STR_VOLUMES] = "Volumes",
    [STR_VOLUME_PC] = "PC",

    /* Erreurs */
    [STR_ACTION_REFUSED] = "Action refusée",
    [STR_COMMAND_TOO_LONG] = "Commande trop longue",
    [STR_SEND_FAILED] = "Envoi impossible",
    [STR_NETWORK_UNAVAILABLE] = "Réseau indisponible",
    [STR_CONFIG_REQUESTED] = "Configuration demandée",

    /* Premier démarrage */
    [STR_WELCOME_TITLE] = "Bienvenue dans Deck3DS",
    [STR_WELCOME_SUBTITLE] = "Votre console devient une surface de contrôle",
    [STR_CHOOSE_LANGUAGE] = "Choisissez votre langue",
    [STR_SETUP_STEP_LANGUAGE] = "Langue",
    [STR_SETUP_STEP_HOST] = "Ordinateur",
    [STR_SETUP_STEP_DONE] = "Prêt",
    [STR_SETUP_HOST_TITLE] = "Où se trouve votre ordinateur ?",
    [STR_SETUP_HOST_HELP] = "L'agent affiche son adresse au démarrage.",
    [STR_SETUP_HOST_EDIT] = "Modifier l'adresse",
    [STR_SETUP_AUTO_DETECT] = "Détectée automatiquement",
    [STR_SETUP_TEST] = "Tester la connexion",
    [STR_SETUP_TESTING] = "Test en cours...",
    [STR_SETUP_TEST_OK] = "La connexion fonctionne",
    [STR_SETUP_TEST_FAIL] = "Aucune réponse à cette adresse",
    [STR_SETUP_FINISH] = "Commencer",
    [STR_SETUP_DONE_TITLE] = "Tout est prêt",
    [STR_SETUP_DONE_HELP] = "Les boutons viennent de l'agent. Modifiez "
                            "config.json pour les changer, sans recompiler.",
    [STR_CONTINUE] = "Continuer",
    [STR_BACK] = "Retour",
    [STR_NEXT] = "Suivant",

    /* Réglages */
    [STR_SETTINGS] = "Réglages",
    [STR_SETTINGS_LANGUAGE] = "Langue",
    [STR_SETTINGS_SOUND] = "Retour au toucher",
    [STR_SETTINGS_DIM] = "Assombrir après",
    [STR_SETTINGS_STEREO] = "Relief 3D",
    [STR_SETTINGS_HOST] = "Adresse de l'ordinateur",
    [STR_SETTINGS_PORT] = "Port",
    [STR_SETTINGS_RECONNECT] = "Reconnecter",
    [STR_SETTINGS_SAVE] = "Enregistrer",
    [STR_SETTINGS_SAVED] = "Réglages enregistrés",
    [STR_SETTINGS_SAVE_FAILED] = "Enregistrement impossible sur la carte SD",
    [STR_SETTINGS_RESET_SETUP] = "Relancer la configuration",
    [STR_ON] = "Activé",
    [STR_OFF] = "Désactivé",
    [STR_NEVER] = "Jamais",
    [STR_SECONDS] = "s",

    /* Aide */
    [STR_HELP_TOUCH] = "Touchez un bouton pour l'activer, maintenez pour son "
                       "action secondaire",
    [STR_HELP_PAGES] = "L / R ou la croix changent de page",
    [STR_HELP_RELOAD] = "SELECT recharge la configuration",
    [STR_HELP_QUIT] = "START quitte",
};

static const char *const *const kCatalogues[LANG_COUNT] = {
    [LANG_EN] = kEnglish,
    [LANG_FR] = kFrench,
};

static const char *const kLanguageNames[LANG_COUNT] = {
    [LANG_EN] = "English",
    [LANG_FR] = "Français",
};

void i18n_set_language(Language language)
{
	/*
	 * L'énumération ne comporte aucune valeur négative : le compilateur peut
	 * la représenter sans signe, une comparaison à zéro serait donc toujours
	 * vraie. Seule la borne supérieure est vérifiée.
	 */
	if (language < LANG_COUNT) {
		s_language = language;
	}
}

Language i18n_language(void)
{
	return s_language;
}

const char *i18n_language_name(Language language)
{
	if (language >= LANG_COUNT) {
		return kLanguageNames[LANG_EN];
	}
	return kLanguageNames[language];
}

Language i18n_detect_system_language(void)
{
	/*
	 * La langue de la console sert seulement à proposer un choix pertinent au
	 * premier lancement. En cas d'échec, l'anglais reste le repli le plus
	 * largement compréhensible.
	 */
	u8 code = 0;

	if (R_FAILED(cfguInit())) {
		return LANG_EN;
	}

	const Result result = CFGU_GetSystemLanguage(&code);
	cfguExit();

	if (R_FAILED(result)) {
		return LANG_EN;
	}

	if (code == CFG_LANGUAGE_FR) {
		return LANG_FR;
	}
	return LANG_EN;
}

const char *tr(StringId id)
{
	if (id >= STR_COUNT) {
		return "";
	}

	const char *const *catalogue = kCatalogues[s_language];
	const char *text = catalogue[id];

	if (text != NULL) {
		return text;
	}

	/*
	 * Traduction manquante : on se rabat sur l'anglais plutôt que d'afficher un
	 * vide, ce qui rendrait l'interface incompréhensible.
	 */
	text = kEnglish[id];
	return (text != NULL) ? text : "";
}
