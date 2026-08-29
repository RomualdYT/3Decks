/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file app.h
 * @brief État global de l'application et son cycle de mise à jour.
 */
#pragma once

#include "model.h"
#include "net.h"
#include "performance_history.h"

/** Paramètres lus depuis la carte SD. */
typedef struct {
	/** Nom humain de l'ordinateur choisi par découverte automatique. */
	char agent_name[64];
	char host[64];
	int port;
	char token[64];
	bool sound;
	/** Langue de l'interface, valeur de l'énumération `Language`. */
	int language;
	/** Secondes d'inactivité avant assombrissement, 0 pour jamais. */
	int dim_delay;
	/** Relief stéréoscopique de l'écran supérieur. */
	bool stereo;
	/** Faux tant que l'assistant de premier démarrage n'a pas été suivi. */
	bool configured;
} Settings;

/** Retour visuel d'une action, corrélé à la réponse de l'agent. */
typedef enum {
	ACTION_FEEDBACK_NONE = 0,
	ACTION_FEEDBACK_PENDING,
	ACTION_FEEDBACK_SUCCESS,
	ACTION_FEEDBACK_ERROR,
} ActionFeedbackState;

#define MAX_ACTION_FEEDBACK 8
#define AUDIO_VISUALIZER_BARS 16

typedef struct {
	int request_id;
	char page_id[LEN_ID];
	char item_id[LEN_ID];
	ActionFeedbackState state;
	/** Délai avant expiration ou transition vers l'erreur. */
	float ttl;
} ActionFeedback;

/**
 * Etat purement visuel de l'ecran superieur.
 *
 * Ces valeurs ne sont ni transmises ni persistantes. Elles conservent juste
 * assez d'historique entre deux frames pour lisser le spectre, faire apparaitre
 * une nouvelle pochette et souligner un changement de volume. Le tableau est
 * alloue dans `App` afin que le rendu n'alloue jamais de memoire par frame.
 */
typedef struct {
	char media_title[LEN_TEXT];
	u32 media_art;
	float media_reveal;
	int last_volume;
	int last_app_volume;
	float system_volume_emphasis;
	float music_volume_emphasis;
	float equalizer[AUDIO_VISUALIZER_BARS];
	unsigned int media_seed;
	/** Position affichee, extrapolee entre deux collectes de l'agent. */
	float media_position_display;
	/** Derniere position brute observee, -1 tant qu'elle est inconnue. */
	int last_media_position;
} TopVisualState;

typedef struct {
	Settings settings;
	Config config;
	PcState state;
	Toast toast;

	LinkStatus link;
	/**
	 * Vrai si l'adresse du PC provient de `3dslink` plutôt que du fichier de
	 * réglages. Utile pour l'indiquer sur l'écran de connexion.
	 */
	bool host_from_netload;
	/** Secondes avant la prochaine tentative de connexion. */
	float reconnect_in;
	/** Palier courant du délai progressif de reconnexion. */
	int reconnect_attempt;
	/** Message d'erreur réseau à afficher sur l'écran de connexion. */
	char link_error[96];
	/** Diagnostic brut, conservé sans l'imposer à l'utilisateur. */
	char link_error_detail[96];
	bool hello_sent;
	bool handshake_ok;
	bool config_received;
	/** Code court saisi, effacé dès que l'agent renvoie le jeton durable. */
	char pair_code[8];
	/** Demande à l'assistant d'ouvrir la saisie du code d'appairage. */
	bool pairing_requested;
	/** Dernière trame reçue, pour détecter une connexion devenue muette. */
	float last_rx_at;
	float next_ping_at;
	int pending_ping_id;
	/**
	 * Nombre de pages de la dernière configuration appliquée.
	 * Sert à distinguer une vraie refonte d'un simple rafraîchissement.
	 */
	int last_page_count;

	int current_page;
	/** Compteur de requêtes, corrèle `button.press` et `action.result`. */
	int next_request_id;
	/** Actions récentes, conservées jusqu'à leur confirmation ou expiration. */
	ActionFeedback action_feedback[MAX_ACTION_FEEDBACK];
	int action_feedback_cursor;

	/** Index du bouton pressé, -1 si aucun. */
	int pressed_slot;
	/** Durée de maintien du bouton courant, en secondes. */
	float press_time;
	bool hold_fired;

	/** Horloge locale, utilisée si le PC ne fournit pas l'heure. */
	char local_time[8];
	/** Date locale, formatée dans la langue choisie sur la console. */
	char local_date[24];

	float uptime;
	/** Fraction de seconde accumulée pour vieillir l'historique localement. */
	float notification_age_timer;
	/** Secondes depuis la dernière interaction, pour la mise en veille. */
	float idle_time;
	bool dimmed;

	/** Animation de transition entre pages. */
	float page_fade;
	/**
	 * Défilement de la page en mode liste, exprimé en rangées.
	 * Une valeur fractionnaire permet un glissement fluide.
	 */
	float list_scroll;
	/** Cible du défilement, atteinte progressivement. */
	float list_target;
	/** Élément mis en avant sur l'écran supérieur, -1 si aucun. */
	int list_focus;
	/**
	 * Emplacement sélectionné dans la grille, -1 si aucun.
	 *
	 * La sélection n'apparaît qu'après un appui sur la croix : au stylet, elle
	 * serait un repère inutile.
	 */
	int grid_focus;
	/**
	 * Avancement de l'animation d'entrée des boutons, de 0 à 1.
	 * Chaque bouton démarre avec un léger retard, ce qui produit une cascade.
	 */
	float enter_anim;
	/** Mis à vrai quand l'agent demande l'ouverture des réglages. */
	bool settings_requested;
	/** Mis à vrai quand l'ordinateur demande l'ouverture du panneau de volumes. */
	bool modal_requested;
	/** Mis à vrai quand l'ordinateur demande le basculement en plein écran. */
	bool frame_requested;
	/**
	 * Affichage en plein écran. Ce n'est pas une page mais un état.
	 *
	 * Deux intentions distinctes l'activent, et l'écran tactile s'adapte à
	 * chacune : un passage volontaire suppose que l'utilisateur est présent et
	 * conserve les contrôles ; la mise en veille suppose l'inverse et laisse
	 * place à un affichage informatif sur fond noir.
	 */
	bool frame_mode;
	/** Vrai si le plein écran résulte de l'inactivité et non d'un appui. */
	bool frame_from_idle;

	/** Niveau de batterie de la console, de 0 à 5. -1 si inconnu. */
	int battery_level;
	/** Décompte avant le prochain relevé de batterie. */
	float battery_timer;
	/** Vrai si la console est en charge. */
	bool battery_charging;

	/** Intensité du liseré d'alerte, décroît après une notification. */
	float alert_glow;

	/** Animations persistantes du tableau de bord audio. */
	TopVisualState top_visual;

	/** Tendances CPU/RAM des trente dernières secondes. */
	PerformanceHistory performance_history;
} App;

/** Enregistre les réglages sur la carte SD. Retourne `false` en cas d'échec. */
bool app_save_settings(App *app);

/** Initialise l'application et charge les réglages. */
void app_init(App *app);

/** Fait progresser l'application d'un pas de temps `dt` (en secondes). */
void app_update(App *app, float dt);

/** Traite les messages réseau en attente. */
void app_pump_network(App *app);

/** Coupe la liaison et programme une reconnexion immédiate. */
void app_force_reconnect(App *app);

/** Affiche une notification temporaire. */
void app_notify(App *app, const char *text, bool error);

/** Déclenche l'action associée à un bouton. */
void app_press_button(App *app, int slot, bool hold);

/**
 * Déclenche une action désignée par son nom.
 *
 * Utilisé par les panneaux de réglage, qui agissent sans qu'un bouton de la
 * grille leur corresponde. L'ordinateur reçoit un identifiant préfixé, qu'il
 * résout comme une action directe.
 */
void app_press_action(App *app, const char *action);

/** Déclenche l'action associée à un élément de liste. */
void app_press_entry(App *app, int index, bool hold);

/** État visuel le plus récent d'un bouton ou d'un élément de liste. */
ActionFeedbackState app_action_feedback(const App *app, const char *page_id,
                                        const char *item_id);

/** Progression de l'appui long du bouton, entre 0 et 1. */
float app_hold_progress(const App *app, int slot);

/** Fait défiler la liste courante de `rows` rangées. */
void app_scroll_list(App *app, float rows, float max_scroll);

/**
 * Déplace la sélection dans la liste.
 *
 * `dx` et `dy` valent -1, 0 ou 1. Le déplacement suit la disposition en
 * colonnes, et la liste défile si nécessaire pour garder la sélection visible.
 */
void app_move_list_focus(App *app, int dx, int dy, int columns, int visible_rows);

/** Élément sélectionné, ou -1. */
int app_list_focus(const App *app);

/**
 * Déplace la sélection dans la grille.
 *
 * Le déplacement s'arrête aux bords plutôt que de reboucler, et ignore les
 * emplacements vides afin que la navigation reste prévisible.
 */
void app_move_grid_focus(App *app, int dx, int dy);

/** Retire la sélection courante, quelle que soit la présentation. */
void app_clear_focus(App *app);

/** Change de page, en bornant l'index. */
void app_goto_page(App *app, int index);

/** Passe à la page suivante ou précédente. */
void app_cycle_page(App *app, int delta);

/** Page courante, ou NULL si la configuration est vide. */
const Page *app_current_page(const App *app);

/** Mode de dashboard effectif, `DASH_AUTO` étant résolu selon l'état. */
DashboardMode app_effective_dashboard(const App *app);

/** Signale une interaction utilisateur (réveille l'écran). */
void app_touch_activity(App *app);
