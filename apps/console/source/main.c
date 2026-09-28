/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file main.c
 * @brief Point d'entrée : initialisation, boucle principale, entrées.
 *
 * Deck3DS transforme la console en surface de contrôle pour un ordinateur :
 * l'écran tactile agit, l'écran supérieur informe.
 *
 * Principe directeur de la boucle : le réseau reste non bloquant et la première
 * tentative de connexion suit la première image. En veille, seules les images
 * inchangées sont omises ; les entrées et le réseau continuent d'être traités.
 */

#include <3ds.h>
#include <citro2d.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "app.h"
#include "i18n.h"
#include "modal.h"
#include "setup.h"
#include "sound.h"
#include "stereo.h"
#include "artwork.h"
#include "net.h"
#include "discovery.h"
#include "protocol.h"
#include "text.h"
#include "theme.h"
#include "ui.h"
#include "ui_intro.h"
#include "ui_companion.h"
#include "render_pacing.h"

/** Durée d'un pas de temps nominal (60 images par seconde). */
#define FRAME_TIME (1.0f / 60.0f)
#define TOUCH_DRAG_THRESHOLD 6.0f
#define LIST_ROW_HEIGHT 42.0f
#define CIRCLE_DEAD_ZONE 22.0f
#define CIRCLE_MAX_AXIS 154.0f
#define LIST_SCROLL_SPEED 9.0f

static App s_app;
static Setup s_setup;
static Modal s_modal;
static volatile bool s_network_resume_requested = false;

static void apt_status_hook(APT_HookType hook, void *param)
{
	(void)param;
	if (hook == APTHOOK_ONRESTORE || hook == APTHOOK_ONWAKEUP) {
		s_network_resume_requested = true;
	}
}

/** Suivi de l'appui tactile en cours. */
typedef struct {
	bool active;
	int slot;
	/** Élément de liste pressé, -1 si l'appui concerne la grille. */
	int entry;
	/** Position du doigt lors du contact, pour détecter un glissement. */
	float start_y;
	/** Défilement de la liste au moment du contact. */
	float start_scroll;
	/** Vrai dès que le doigt a suffisamment bougé pour être un glissement. */
	bool dragging;
	float seek_x;
} TouchTracker;

static TouchTracker s_touch;
/**
 * Donne la priorité aux écrans qui capturent toutes les commandes.
 *
 * @return Vrai si l'entrée a été entièrement consommée.
 */
static bool handle_exclusive_input(App *app, u32 down, u32 held, u32 up)
{
	if (s_setup.active) {
		if (down & KEY_TOUCH) {
			touchPosition touch;
			hidTouchRead(&touch);
			setup_touch(&s_setup, app, (float)touch.px, (float)touch.py);
		}
		setup_buttons(&s_setup, app, down);
		return true;
	}

	if (s_modal.active) {
		touchPosition touch;
		hidTouchRead(&touch);

		if ((down & KEY_TOUCH) || (held & KEY_TOUCH) || (up & KEY_TOUCH)) {
			modal_touch(&s_modal, app, (float)touch.px, (float)touch.py,
			            (down & KEY_TOUCH) != 0, (up & KEY_TOUCH) != 0);
		}

		modal_buttons(&s_modal, app, down);
		return true;
	}

	/*
	 * En plein écran, la console sert d'objet d'affichage : un contact ou une
	 * touche en sort, sans déclencher d'action.
	 */
	if (app->frame_mode) {
		if (down != 0) {
			app->frame_mode = false;
			sound_play(SOUND_PAGE);
		}
		return true;
	}

	/* Le raccourci L + SELECT ouvre les réglages depuis l'écran principal. */
	if ((down & KEY_SELECT) && (held & KEY_L)) {
		setup_open_settings(&s_setup);
		return true;
	}

	return false;
}

/**
 * Mémorise le début d'un geste tactile.
 *
 * @return Vrai lorsqu'une liste a capturé le geste et que la trame est finie.
 */
static bool begin_touch(App *app)
{
	touchPosition touch;
	hidTouchRead(&touch);

	const Page *page = app_current_page(app);
	if (page != NULL && page->dashboard == DASH_LYRICS &&
	    app->state.media_seekable && app->state.media_duration > 0 &&
	    touch.py >= 28 && touch.py < (u16)GRID_TOP &&
	    touch.px >= (u16)GRID_MARGIN_X &&
	    touch.px < (u16)(SCREEN_BOTTOM_W - GRID_MARGIN_X)) {
		s_touch.active = true;
		s_touch.slot = -2; /* curseur de lecture */
		s_touch.entry = -1;
		s_touch.dragging = true;
		s_touch.seek_x = (float)touch.px;
		return true;
	}
	const bool is_list = (page != NULL) && page->layout == LAYOUT_LIST;
	const int entry =
	    is_list ? ui_list_at(app, (float)touch.px, (float)touch.py) : -1;

	if (entry >= 0) {
		s_touch.active = true;
		s_touch.slot = -1;
		s_touch.entry = entry;
		s_touch.start_y = (float)touch.py;
		s_touch.start_scroll = app->list_target;
		s_touch.dragging = false;
		app->list_focus = entry;
		app->press_time = 0.0f;
		app->hold_fired = false;
		return true;
	}

	/*
	 * Sur une page en liste, tout contact dans la zone centrale fait défiler.
	 * La barre d'onglets et le bouton des réglages restent ainsi accessibles.
	 */
	if (is_list && touch.py < (u16)(SCREEN_H - GRID_BOTTOM_BAR)) {
		s_touch.active = true;
		s_touch.slot = -1;
		s_touch.entry = -1;
		s_touch.start_y = (float)touch.py;
		s_touch.start_scroll = app->list_target;
		s_touch.dragging = true;
		return true;
	}

	const int slot =
	    is_list ? -1 : ui_slot_at((float)touch.px, (float)touch.py);
	if (slot >= 0) {
		s_touch.active = true;
		s_touch.slot = slot;
		s_touch.entry = -1;
		app->pressed_slot = slot;
		/*
		 * Le stylet retire la sélection afin de ne pas afficher deux pointeurs
		 * concurrents.
		 */
		app->grid_focus = -1;
		app->press_time = 0.0f;
		app->hold_fired = false;
	} else if ((!app->config_received &&
	            ui_waiting_settings_at((float)touch.px, (float)touch.py)) ||
	           ui_settings_at((float)touch.px, (float)touch.py)) {
		setup_open_settings(&s_setup);
	} else {
		const int tab = ui_tab_at((float)touch.px, (float)touch.py,
		                          app->config.page_count);
		if (tab >= 0) {
			app_goto_page(app, tab);
		}
	}

	return false;
}

/**
 * Fait suivre une liste au doigt pendant un glissement.
 *
 * @return Vrai si la page en liste a capturé la trame tactile.
 */
static bool update_list_touch(App *app, u32 held)
{
	if (!(held & KEY_TOUCH) || !s_touch.active) {
		return false;
	}

	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_LIST) {
		return false;
	}

	touchPosition touch;
	hidTouchRead(&touch);

	const float delta = (float)touch.py - s_touch.start_y;
	if (!s_touch.dragging &&
	    (delta > TOUCH_DRAG_THRESHOLD || delta < -TOUCH_DRAG_THRESHOLD)) {
		s_touch.dragging = true;
	}

	if (s_touch.dragging) {
		app->list_target =
		    s_touch.start_scroll - delta / LIST_ROW_HEIGHT;

		if (app->list_target < 0.0f) {
			app->list_target = 0.0f;
		}

		const float max_scroll = ui_list_max_scroll(app);
		if (app->list_target > max_scroll) {
			app->list_target = max_scroll;
		}

		app_touch_activity(app);
	}

	return true;
}

/** Annule un appui de grille lorsque le doigt quitte le bouton. */
static void update_grid_touch(App *app, u32 held)
{
	if (!(held & KEY_TOUCH) || !s_touch.active || s_touch.entry >= 0) {
		return;
	}

	touchPosition touch;
	hidTouchRead(&touch);
	if (s_touch.slot == -2) {
		s_touch.seek_x = (float)touch.px;
		return;
	}

	const int slot = ui_slot_at((float)touch.px, (float)touch.py);
	if (slot != s_touch.slot) {
		s_touch.active = false;
		app->pressed_slot = -1;
	}
}

/** Déclenche ou annule l'action tactile lors du relâchement. */
static void finish_touch(App *app, u32 up)
{
	if (!(up & KEY_TOUCH)) {
		return;
	}
	if (s_touch.active && s_touch.slot == -2 && app->link == LINK_ONLINE) {
		float ratio = (s_touch.seek_x - GRID_MARGIN_X) /
		              (SCREEN_BOTTOM_W - GRID_MARGIN_X * 2.0f);
		if (ratio < 0.0f) ratio = 0.0f;
		if (ratio > 1.0f) ratio = 1.0f;
		const int seconds = (int)(ratio * (float)app->state.media_duration);
		char payload[128];
		const int length = protocol_encode_value(payload, sizeof(payload),
		                                         app->next_request_id,
		                                         "media_position", seconds);
		if (length > 0 && (size_t)length < sizeof(payload) &&
		    net_send(payload, (size_t)length)) {
			app->next_request_id++;
			app->state.media_position = seconds;
			app->top_visual.media_position_display = (float)seconds;
		}
	}

	if (s_touch.active && !app->hold_fired && !s_touch.dragging) {
		if (s_touch.entry >= 0) {
			app_press_entry(app, s_touch.entry, false);
		} else {
			app_press_button(app, s_touch.slot, false);
		}
	}

	s_touch.active = false;
	s_touch.entry = -1;
	s_touch.dragging = false;
	app->pressed_slot = -1;
	app->press_time = 0.0f;
	app->hold_fired = false;
}

/** Traite le défilement et la sélection d'une page en liste. */
static void handle_list_controls(App *app, u32 down)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_LIST) {
		return;
	}

	const int columns = ui_list_columns();
	const int rows = ui_list_rows();
	const float max_scroll = ui_list_max_scroll(app);

	circlePosition circle;
	hidCircleRead(&circle);
	circlePosition cstick;
	hidCstickRead(&cstick);

	/* Sélectionne l'axe vertical le plus incliné entre Circle Pad et C-Stick */
	const float value = (fabsf((float)cstick.dy) > fabsf((float)circle.dy))
	                        ? (float)cstick.dy
	                        : (float)circle.dy;

	if (value > CIRCLE_DEAD_ZONE || value < -CIRCLE_DEAD_ZONE) {
		const float amount =
		    (value - (value > 0.0f ? CIRCLE_DEAD_ZONE : -CIRCLE_DEAD_ZONE)) /
		    (CIRCLE_MAX_AXIS - CIRCLE_DEAD_ZONE);
		const float speed =
		    amount * amount * amount * LIST_SCROLL_SPEED;

		/* Le pavé ou le C-Stick pointé vers le haut fait remonter la liste. */
		app_scroll_list(app, -speed * FRAME_TIME, max_scroll);
		app_touch_activity(app);
	}

	if (down & KEY_UP) {
		app_move_list_focus(app, 0, -1, columns, rows);
	}
	if (down & KEY_DOWN) {
		app_move_list_focus(app, 0, 1, columns, rows);
	}
	if (down & KEY_LEFT) {
		app_move_list_focus(app, -1, 0, columns, rows);
	}
	if (down & KEY_RIGHT) {
		app_move_list_focus(app, 1, 0, columns, rows);
	}

	if ((down & KEY_A) && app_list_focus(app) >= 0) {
		app_press_entry(app, app_list_focus(app), false);
	}
	if (down & KEY_B) {
		app_clear_focus(app);
	}
}

/** Traite la sélection et les raccourcis d'une page en grille. */
static void handle_grid_controls(App *app, u32 down)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_GRID) {
		return;
	}

	if (down & KEY_UP) {
		app_move_grid_focus(app, 0, -1);
	}
	if (down & KEY_DOWN) {
		app_move_grid_focus(app, 0, 1);
	}
	if (down & KEY_LEFT) {
		app_move_grid_focus(app, -1, 0);
	}
	if (down & KEY_RIGHT) {
		app_move_grid_focus(app, 1, 0);
	}

	if (down & KEY_A) {
		if (app->grid_focus >= 0) {
			app_press_button(app, app->grid_focus, false);
		} else {
			/* Sans sélection, A désigne le premier emplacement. */
			app_move_grid_focus(app, 0, 0);
		}
	}

	if (down & KEY_B) {
		app_clear_focus(app);
	}
}

/** Demande à l'agent de renvoyer immédiatement la configuration. */
static void request_config(App *app, u32 down)
{
	if (!(down & KEY_SELECT)) {
		return;
	}

	char payload[64];
	const int written = protocol_encode_config_request(
	    payload, sizeof(payload), app->next_request_id++);
	if (written > 0 && (size_t)written < sizeof(payload) &&
	    net_send(payload, (size_t)written)) {
		app_notify(app, tr(STR_CONFIG_REQUESTED), false);
	}
}

/**
 * Distribue les entrées vers les contrôleurs spécialisés.
 *
 * Le tactile déclenche l'action au relâchement, pas à l'appui : cela permet
 * d'annuler en glissant hors du bouton, et rend possible l'appui long.
 */
static void handle_input(App *app)
{
	hidScanInput();

	const u32 down = hidKeysDown();
	const u32 up = hidKeysUp();
	const u32 held = hidKeysHeld();

	if (down != 0 || up != 0) {
		app_touch_activity(app);
	}

	if (handle_exclusive_input(app, down, held, up)) {
		return;
	}

	if ((down & KEY_TOUCH) && begin_touch(app)) {
		return;
	}
	if (update_list_touch(app, held)) {
		return;
	}

	update_grid_touch(app, held);
	finish_touch(app, up);
	handle_list_controls(app, down);

	if (down & KEY_L) {
		app_cycle_page(app, -1);
	}
	if (down & KEY_R) {
		app_cycle_page(app, 1);
	}

	if (down & KEY_ZL) {
		if (app->link == LINK_ONLINE) {
			app_press_action(app, "volume.down");
			sound_play(SOUND_TAP);
		} else {
			sound_play(SOUND_ERROR);
			app_notify(app, tr(STR_PC_DISCONNECTED), true);
		}
	}
	if (down & KEY_ZR) {
		if (app->link == LINK_ONLINE) {
			app_press_action(app, "volume.up");
			sound_play(SOUND_TAP);
		} else {
			sound_play(SOUND_ERROR);
			app_notify(app, tr(STR_PC_DISCONNECTED), true);
		}
	}

	handle_grid_controls(app, down);
	request_config(app, down);
}

int main(int argc, char *argv[])
{
	(void)argc;
	(void)argv;

	/*
	 * Sur New 3DS / New 2DS, débloque la fréquence CPU à 804 MHz et le cache L2
	 * pour assurer 60 FPS constants lors du rendu stéréoscopique double passe.
	 * Sans effet sur consoles Old 3DS.
	 */
	osSetSpeedupEnable(true);

	/* --- Initialisation graphique --- */
	gfxInitDefault();
	/*
	 * Le relief est activé au niveau du système : l'intensité effective suit le
	 * curseur de la console, et le rendu redevient plat lorsqu'il est en butée
	 * basse.
	 */
	gfxSet3D(true);
	aptSetHomeAllowed(true);

	/*
	 * Système de fichiers embarqué : il contient la police de l'interface. Son
	 * absence n'est pas bloquante, `text_init` se rabattra sur la police
	 * système.
	 */
	romfsInit();

	if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) {
		romfsExit();
		gfxExit();
		return 1;
	}
	/*
	 * Le budget d'objets est relevé : en relief, l'écran supérieur est dessiné
	 * deux fois, et les icônes vectorielles consomment davantage de géométrie
	 * que des images. La mesure donne environ 3600 objets dans le pire cas,
	 * auxquels s'ajoute le texte.
	 */
	if (!C2D_Init(C2D_DEFAULT_MAX_OBJECTS * 2)) {
		C3D_Fini();
		romfsExit();
		gfxExit();
		return 1;
	}
	C2D_Prepare();

	C3D_RenderTarget *top = C2D_CreateScreenTarget(GFX_TOP, GFX_LEFT);
	/* Seconde image de l'écran supérieur, pour l'œil droit. */
	C3D_RenderTarget *top_right = C2D_CreateScreenTarget(GFX_TOP, GFX_RIGHT);
	C3D_RenderTarget *bottom = C2D_CreateScreenTarget(GFX_BOTTOM, GFX_LEFT);

	if (top == NULL || top_right == NULL || bottom == NULL || !text_init()) {
		/* Sans tampon de texte, l'interface serait muette : on s'arrête. */
		C2D_Fini();
		C3D_Fini();
		romfsExit();
		gfxExit();
		return 1;
	}

	/*
	 * L'échec d'allocation de la texture de pochette n'est pas bloquant :
	 * l'interface se contentera du substitut dessiné.
	 */
	artwork_init();

	/*
	 * Le retour sonore est facultatif : son absence rend l'application
	 * silencieuse, sans l'empêcher de fonctionner.
	 */
	sound_init();

	/*
	 * Le service réseau est initialisé avant l'application : `app_init` doit
	 * pouvoir consulter l'état du réseau, et la première tentative de connexion
	 * ne doit pas partir avant que le service soit disponible.
	 *
	 * La connexion elle-même reste différée : `app_update` la déclenchera après
	 * la première image, afin que l'interface s'affiche immédiatement même si
	 * l'ordinateur est absent.
	 */
	const bool network_ready = net_init();

	app_init(&s_app);
	s_touch.active = false;
	s_touch.slot = -1;

	/*
	 * Au tout premier lancement, la langue de la console sert de proposition
	 * initiale : l'utilisateur reste libre de la changer à l'étape suivante.
	 */
	if (!s_app.settings.configured) {
		const Language detected = i18n_detect_system_language();
		i18n_set_language(detected);
		s_app.settings.language = (int)detected;
	}

	setup_begin(&s_setup, !s_app.settings.configured);
	if (s_app.settings.configured) {
		setup_close(&s_setup);
	}

	if (!network_ready) {
		app_notify(&s_app, tr(STR_NETWORK_UNAVAILABLE), true);
	}

	aptHookCookie apt_cookie;
	aptHook(&apt_cookie, apt_status_hook, NULL);

	/* Mesure du temps réel : les animations restent correctes même si le
	 * nombre d'images par seconde varie. */
	u64 previous_tick = svcGetSystemTick();
	UiIntro intro;
	ui_intro_begin(&intro, s_app.settings.companion != COMPANION_OFF);
	bool intro_input_guard = intro.active;
	RenderPacing render_pacing = {0};

	while (aptMainLoop()) {
		if (s_network_resume_requested) {
			s_network_resume_requested = false;
			app_force_reconnect(&s_app);
		}
		/* --- Temps écoulé --- */
		const u64 now = svcGetSystemTick();
		float dt = (float)((double)(now - previous_tick) /
		                   (double)SYSCLOCK_ARM11);
		previous_tick = now;

		/* Bornage : évite qu'une longue pause ne fasse sauter les animations. */
		if (dt <= 0.0f || dt > 0.25f) {
			dt = FRAME_TIME;
		}

		/* --- Entrées --- */
		if (intro_input_guard) {
			hidScanInput();
			const bool was_active = intro.active;
			ui_intro_update(&intro, dt, hidKeysDown() != 0);
			/* A dismissing press (including a held touch) cannot activate
			 * a control on the screen underneath. START still exits. */
			if (!was_active && hidKeysHeld() == 0) intro_input_guard = false;
		} else {
			handle_input(&s_app);
		}

		if (hidKeysDown() & KEY_START) {
			break;
		}

		/* --- Réseau et logique --- */
		if (network_ready) {
			app_pump_network(&s_app);
		}
		if (s_app.pairing_requested) {
			s_app.pairing_requested = false;
			setup_handle_pairing_request(&s_setup, &s_app);
		}
		app_update(&s_app, dt);
		setup_update(&s_setup, &s_app, dt);
		modal_update(&s_modal, &s_app, dt);

		/* L'agent peut demander l'ouverture des réglages depuis un bouton. */
		if (s_app.settings_requested) {
			s_app.settings_requested = false;
			setup_open_settings(&s_setup);
		}

		/* Demandes venues de l'ordinateur. */
		if (s_app.modal_requested) {
			s_app.modal_requested = false;
			modal_open(&s_modal, &s_app);
		}
		if (s_app.frame_requested) {
			s_app.frame_requested = false;
			s_app.frame_mode = !s_app.frame_mode;
		}

		/*
		 * En veille sans média ni compagnon, la page est presque immobile.
		 * Les entrées, la logique et le réseau restent traités à chaque tour ;
		 * une réception ou une animation impose aussitôt un nouveau dessin.
		 */
		const bool idle_render =
		    s_app.dimmed && !s_app.frame_mode && s_app.config_received &&
		    !intro.active && !s_setup.active && !s_modal.active &&
		    s_app.toast.ttl <= 0.0f && s_app.toast.alpha <= 0.01f &&
		    s_app.alert_glow <= 0.0f && s_app.enter_anim >= 1.0f &&
		    s_app.page_fade >= 1.0f &&
		    fabsf(s_app.list_target - s_app.list_scroll) < 0.001f;
		if (!render_pacing_should_draw(&render_pacing, dt, idle_render,
		                               s_app.last_rx_at)) {
			/* Deux VBlank gardent le réseau et le réveil réactifs (~30 Hz). */
			gspWaitForVBlank();
			gspWaitForVBlank();
			continue;
		}

		/* --- Rendu --- */
		text_frame_begin();

		C3D_FrameBegin(C3D_FRAME_SYNCDRAW);

		/*
		 * Intensité du relief : produit du curseur de la console et du réglage
		 * de l'application. En veille (dimmed), le relief est désactivé afin
		 * d'éviter la seconde passe de rendu et d'économiser la batterie.
		 */
		const float slider = osGet3DSliderState();
		const float depth_strength =
		    (!s_app.dimmed && s_app.settings.stereo) ? slider : 0.0f;
		const bool stereo = depth_strength > 0.01f;

		for (int eye = 0; eye < (stereo ? 2 : 1); eye++) {
			C3D_RenderTarget *target = (eye == 0) ? top : top_right;

			stereo_begin_eye(eye, depth_strength);

			C2D_TargetClear(target, COL_BG);
			C2D_SceneBegin(target);
			if (intro.active) {
				ui_intro_draw_top(&intro);
			} else if (s_setup.active) {
				setup_draw_top(&s_setup, &s_app);
			} else {
				ui_draw_top(&s_app);
			}

			stereo_end_eye();
		}

		C2D_TargetClear(bottom, COL_BG);
		C2D_SceneBegin(bottom);
		if (intro.active) {
			ui_intro_draw_bottom();
		} else if (s_setup.active) {
			setup_draw_bottom(&s_setup, &s_app);
		} else {
			ui_draw_bottom(&s_app);

			/* Le panneau se superpose à la page qu'il recouvre. */
			if (s_modal.active) {
				modal_draw(&s_modal, &s_app);
			}
		}

		C3D_FrameEnd(0);

		/*
		 * En veille, un VBlank supplémentaire borne la boucle à environ 30 Hz.
		 * Le rendu d'une page immobile est déjà espacé par render_pacing.
		 */
		if (s_app.dimmed) {
			gspWaitForVBlank();
		}
	}

	/* --- Libération --- */
	aptUnhook(&apt_cookie);
	discovery_stop();
	net_exit();
	ptmuExit();
	sound_exit();
	artwork_exit();
	text_exit();
	C2D_Fini();
	C3D_Fini();
	romfsExit();
	gfxExit();
	return 0;
}
