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
    [STR_DECKY_DISCREET] = "Discreet",
    [STR_DECKY_STANDBY] = "Companion idle",
    [STR_DECKY_LISTENING] = "A little music, a little company.",
    [STR_DECKY_RESTING] = "Resting here with you.",
    [STR_DECKY_HELP] = "Choose off, discreet or companion idle below.",
    [STR_EXTENSION_WAITING] = "Waiting for extension data",
    [STR_EXTENSION_UNAVAILABLE] = "Enable this extension on your computer",
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
    [STR_AGENT_UNAVAILABLE] = "Agent is not running on this computer",
    [STR_CONNECTION_LOST] = "Connection to the computer was lost",
    [STR_CONNECTION_STALE] = "The agent is no longer responding",

    /* Média */
    [STR_NOTHING_PLAYING] = "Nothing playing",
    [STR_LYRICS_LOADING] = "Finding lyrics...",
    [STR_LYRICS_UNAVAILABLE] = "No synced lyrics found",
    [STR_LYRICS_DISABLED] = "Enable lyrics in 3Decks",
    [STR_LYRICS_INSTRUMENTAL] = "Instrumental track",
    [STR_PLAYING] = "Playing",
    [STR_PAUSED] = "Paused",

    /* Micro et audio */
    [STR_MIC_UNKNOWN] = "Mic ?",
    [STR_MIC_ACTIVE] = "Mic live",
    [STR_MIC_MUTED] = "Mic muted",
    [STR_AUDIO_OUTPUT] = "AUDIO OUTPUT",
    [STR_OUTPUT_UNKNOWN] = "Unknown",
    [STR_MUSIC] = "Music",
    [STR_SYSTEM_AUDIO] = "System",
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
    [STR_PERFORMANCE_HEALTHY] = "Everything is running smoothly",
    [STR_PERFORMANCE_BUSY] = "The computer is working hard",
    [STR_PERFORMANCE_ALERT] = "Performance needs attention",
    [STR_PERFORMANCE_WAITING] = "Waiting for performance data",
    [STR_NETWORK] = "NETWORK",
    [STR_STORAGE] = "STORAGE",
    [STR_GRAPHICS] = "GRAPHICS",
    [STR_DOWNLOAD] = "DOWN",
    [STR_UPLOAD] = "UP",
    [STR_TOP_PROCESS] = "TOP APP",
    [STR_LAST_30_SECONDS] = "30 SEC",
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
    [STR_WELCOME_TITLE] = "Welcome to 3Decks",
    [STR_WELCOME_SUBTITLE] = "Turn your console into a control surface",
    [STR_CHOOSE_LANGUAGE] = "Choose your language",
    [STR_SETUP_STEP_LANGUAGE] = "Language",
    [STR_SETUP_STEP_HOST] = "Computer",
    [STR_SETUP_STEP_DONE] = "Ready",
    [STR_SETUP_HOST_TITLE] = "Where is your computer?",
    [STR_SETUP_HOST_HELP] = "The agent shows its address when it starts.",
    [STR_SETUP_HOST_EDIT] = "Edit address",
    [STR_SETUP_AUTO_DETECT] = "Detected automatically",
    [STR_SETUP_SEARCHING] = "Looking for nearby computers...",
    [STR_SETUP_NO_AGENT] = "No 3Decks agent found",
    [STR_SETUP_AGENTS_FOUND] = "Choose your computer",
    [STR_SETUP_SEARCH_AGAIN] = "Search again",
    [STR_SETUP_MANUAL] = "Manual setup",
    [STR_SETUP_AUTOMATIC] = "Automatic search",
    [STR_SETUP_CONNECT] = "Connect",
    [STR_SETUP_PAIR_CODE] = "Pairing code",
    [STR_SETUP_PAIR_HELP] = "Enter the 6-digit code shown on your computer",
    [STR_PAIRING_REQUIRED] = "Pairing code required",
    [STR_PAIRING_SAVED] = "Console paired securely",
    [STR_SETUP_TEST] = "Test connection",
    [STR_SETUP_TESTING] = "Testing...",
    [STR_SETUP_TEST_OK] = "Connection works",
    [STR_SETUP_TEST_FAIL] = "No answer from this address",
    [STR_SETUP_FINISH] = "Start using 3Decks",
    [STR_SETUP_DONE_TITLE] = "All set",
    [STR_SETUP_DONE_HELP] = ("Your pages and buttons can now be changed from "
                            "the 3Decks interface on your computer."),
    [STR_CONTINUE] = "Continue",
    [STR_BACK] = "Back",
    [STR_NEXT] = "Next",

    /* Réglages */
    [STR_SETTINGS] = "Settings",
    [STR_SETTINGS_LANGUAGE] = "Language",
    [STR_SETTINGS_SOUND] = "Touch feedback",
    [STR_SETTINGS_DIM] = "Dim screen after",
    [STR_SETTINGS_STEREO] = "3D depth",
    [STR_SETTINGS_COMPUTER] = "Connected computer",
    [STR_SETTINGS_HOST] = "Computer IPv4 address",
    [STR_SETTINGS_IPV4_REQUIRED] = "Enter an IPv4 address, e.g. 192.168.1.10",
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
    [STR_DECKY_DISCREET] = "Discret",
    [STR_DECKY_STANDBY] = "Veille compagnon",
    [STR_DECKY_LISTENING] = "Un peu de musique, un peu de compagnie.",
    [STR_DECKY_RESTING] = "Une petite pause avec toi.",
    [STR_DECKY_HELP] = "Choisis le mode de Decky sur l'écran du bas.",
    [STR_EXTENSION_WAITING] = "En attente de l'extension",
    [STR_EXTENSION_UNAVAILABLE] = "Activez cette extension sur l'ordinateur",
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
    [STR_AGENT_UNAVAILABLE] = "L'agent n'est pas lancé sur cet ordinateur",
    [STR_CONNECTION_LOST] = "Connexion à l'ordinateur interrompue",
    [STR_CONNECTION_STALE] = "L'agent ne répond plus",

    /* Média */
    [STR_NOTHING_PLAYING] = "Aucune lecture",
    [STR_LYRICS_LOADING] = "Recherche des paroles...",
    [STR_LYRICS_UNAVAILABLE] = "Paroles indisponibles",
    [STR_LYRICS_DISABLED] = "Activer les paroles dans 3Decks",
    [STR_LYRICS_INSTRUMENTAL] = "Morceau instrumental",
    [STR_PLAYING] = "Lecture",
    [STR_PAUSED] = "Pause",

    /* Micro et audio */
    [STR_MIC_UNKNOWN] = "Micro ?",
    [STR_MIC_ACTIVE] = "Micro actif",
    [STR_MIC_MUTED] = "Micro coupé",
    [STR_AUDIO_OUTPUT] = "SORTIE AUDIO",
    [STR_OUTPUT_UNKNOWN] = "Inconnue",
    [STR_MUSIC] = "Musique",
    [STR_SYSTEM_AUDIO] = "Système",
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
    [STR_PERFORMANCE_HEALTHY] = "Tout fonctionne normalement",
    [STR_PERFORMANCE_BUSY] = "L'ordinateur travaille beaucoup",
    [STR_PERFORMANCE_ALERT] = "Performances à surveiller",
    [STR_PERFORMANCE_WAITING] = "Mesures de performances en attente",
    [STR_NETWORK] = "RÉSEAU",
    [STR_STORAGE] = "STOCKAGE",
    [STR_GRAPHICS] = "CARTE GRAPHIQUE",
    [STR_DOWNLOAD] = "REÇU",
    [STR_UPLOAD] = "ENVOYÉ",
    [STR_TOP_PROCESS] = "APP ACTIVE",
    [STR_LAST_30_SECONDS] = "30 SEC",
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
    [STR_WELCOME_TITLE] = "Bienvenue dans 3Decks",
    [STR_WELCOME_SUBTITLE] = "Votre console devient une surface de contrôle",
    [STR_CHOOSE_LANGUAGE] = "Choisissez votre langue",
    [STR_SETUP_STEP_LANGUAGE] = "Langue",
    [STR_SETUP_STEP_HOST] = "Ordinateur",
    [STR_SETUP_STEP_DONE] = "Prêt",
    [STR_SETUP_HOST_TITLE] = "Où se trouve votre ordinateur ?",
    [STR_SETUP_HOST_HELP] = "L'agent affiche son adresse au démarrage.",
    [STR_SETUP_HOST_EDIT] = "Modifier l'adresse",
    [STR_SETUP_AUTO_DETECT] = "Détectée automatiquement",
    [STR_SETUP_SEARCHING] = "Recherche des ordinateurs à proximité...",
    [STR_SETUP_NO_AGENT] = "Aucun agent 3Decks détecté",
    [STR_SETUP_AGENTS_FOUND] = "Choisissez votre ordinateur",
    [STR_SETUP_SEARCH_AGAIN] = "Rechercher à nouveau",
    [STR_SETUP_MANUAL] = "Configuration manuelle",
    [STR_SETUP_AUTOMATIC] = "Recherche automatique",
    [STR_SETUP_CONNECT] = "Se connecter",
    [STR_SETUP_PAIR_CODE] = "Code d'appairage",
    [STR_SETUP_PAIR_HELP] = "Saisissez les 6 chiffres affichés sur l'ordinateur",
    [STR_PAIRING_REQUIRED] = "Code d'appairage requis",
    [STR_PAIRING_SAVED] = "Console appairée en sécurité",
    [STR_SETUP_TEST] = "Tester la connexion",
    [STR_SETUP_TESTING] = "Test en cours...",
    [STR_SETUP_TEST_OK] = "La connexion fonctionne",
    [STR_SETUP_TEST_FAIL] = "Aucune réponse à cette adresse",
    [STR_SETUP_FINISH] = "Commencer",
    [STR_SETUP_DONE_TITLE] = "Tout est prêt",
    [STR_SETUP_DONE_HELP] = "Vos pages et boutons se modifient maintenant "
                            "depuis l'interface 3Decks sur l'ordinateur.",
    [STR_CONTINUE] = "Continuer",
    [STR_BACK] = "Retour",
    [STR_NEXT] = "Suivant",

    /* Réglages */
    [STR_SETTINGS] = "Réglages",
    [STR_SETTINGS_LANGUAGE] = "Langue",
    [STR_SETTINGS_SOUND] = "Retour au toucher",
    [STR_SETTINGS_DIM] = "Assombrir après",
    [STR_SETTINGS_STEREO] = "Relief 3D",
    [STR_SETTINGS_COMPUTER] = "Ordinateur connecté",
    [STR_SETTINGS_HOST] = "Adresse IPv4 de l'ordinateur",
    [STR_SETTINGS_IPV4_REQUIRED] = "Saisissez une IPv4, ex. 192.168.1.10",
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
