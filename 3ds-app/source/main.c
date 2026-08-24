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
 * Principe directeur de la boucle : le rendu passe toujours en premier et n'est
 * jamais retardé par le réseau. Toute opération réseau est non bloquante, et la
 * première tentative de connexion a lieu après la première image affichée, afin
 * que l'application ne paraisse jamais figée sur matériel réel.
 */

#include <3ds.h>
#include <citro2d.h>
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
#include "protocol.h"
#include "text.h"
#include "theme.h"
#include "ui.h"

/** Durée d'un pas de temps nominal (60 images par seconde). */
#define FRAME_TIME (1.0f / 60.0f)

static App s_app;
static Setup s_setup;
static Modal s_modal;

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
} TouchTracker;

static TouchTracker s_touch;

/**
 * Traite les entrées : tactile, boutons physiques, pavé directionnel.
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

	/*
	 * L'assistant et les réglages sont modaux : tant qu'ils sont ouverts, ils
	 * reçoivent seuls les commandes, ce qui évite de déclencher une action par
	 * mégarde.
	 */
	if (s_setup.active) {
		if (down & KEY_TOUCH) {
			touchPosition touch;
			hidTouchRead(&touch);
			setup_touch(&s_setup, app, (float)touch.px, (float)touch.py);
		}
		setup_buttons(&s_setup, app, down);
		return;
	}

	/*
	 * Le panneau de volumes est modal : il reçoit seul les commandes tant qu'il
	 * est ouvert, ce qui évite de déclencher une action de la grille par
	 * mégarde.
	 */
	if (s_modal.active) {
		touchPosition touch;
		hidTouchRead(&touch);

		if ((down & KEY_TOUCH) || (held & KEY_TOUCH) || (up & KEY_TOUCH)) {
			modal_touch(&s_modal, app, (float)touch.px, (float)touch.py,
			            (down & KEY_TOUCH) != 0, (up & KEY_TOUCH) != 0);
		}

		modal_buttons(&s_modal, app, down);
		return;
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
		return;
	}

	/* SELECT maintenu ouvre les réglages. */
	if ((down & KEY_SELECT) && (held & KEY_L)) {
		setup_open_settings(&s_setup);
		return;
	}

	/* --- Tactile --- */
	if (down & KEY_TOUCH) {
		touchPosition touch;
		hidTouchRead(&touch);

		const Page *page = app_current_page(app);
		const bool is_list = (page != NULL) && page->layout == LAYOUT_LIST;

		/*
		 * En présentation liste, la zone centrale contient des éléments et non
		 * une grille : on les traite en priorité.
		 */
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
			return;
		}

		/*
		 * Contact en dehors d'un élément, sur une page en liste : le geste sert
		 * à faire défiler.
		 *
		 * La barre d'onglets et le bouton des réglages doivent toutefois rester
		 * atteignables : ils sont donc écartés avant que le geste ne soit
		 * interprété comme un défilement. Sans cette réserve, toucher un onglet
		 * revenait à faire glisser la liste, et le changement de page devenait
		 * impossible au stylet.
		 */
		if (is_list && touch.py < (u16)(SCREEN_H - GRID_BOTTOM_BAR)) {
			s_touch.active = true;
			s_touch.slot = -1;
			s_touch.entry = -1;
			s_touch.start_y = (float)touch.py;
			s_touch.start_scroll = app->list_target;
			s_touch.dragging = true;
			return;
		}

		const int slot =
		    is_list ? -1 : ui_slot_at((float)touch.px, (float)touch.py);
		if (slot >= 0) {
			s_touch.active = true;
			s_touch.slot = slot;
			s_touch.entry = -1;
			app->pressed_slot = slot;
			/*
			 * Le stylet retire la sélection : garder un curseur affiché alors
			 * que l'utilisateur touche l'écran laisserait croire à deux
			 * pointeurs concurrents.
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
	}

	/*
	 * Glissement au doigt sur une page en liste.
	 *
	 * La liste suit le doigt au pixel : c'est le geste attendu sur un écran
	 * tactile, et il rend le parcours d'une longue liste immédiat.
	 */
	if ((held & KEY_TOUCH) && s_touch.active) {
		const Page *page = app_current_page(app);

		if (page != NULL && page->layout == LAYOUT_LIST) {
			touchPosition touch;
			hidTouchRead(&touch);

			const float delta = (float)touch.py - s_touch.start_y;

			/*
			 * Seuil de déclenchement : sans lui, un appui un peu tremblant
			 * serait interprété comme un glissement et l'élément ne
			 * s'activerait jamais.
			 */
			if (!s_touch.dragging && (delta > 6.0f || delta < -6.0f)) {
				s_touch.dragging = true;
			}

			if (s_touch.dragging) {
				/* Une rangée correspond à sa hauteur plus l'espacement. */
				const float row_height = 42.0f;
				const float target =
				    s_touch.start_scroll - delta / row_height;

				app->list_target = target;
				if (app->list_target < 0.0f) {
					app->list_target = 0.0f;
				}
				const float max_scroll = ui_list_max_scroll(app);
				if (app->list_target > max_scroll) {
					app->list_target = max_scroll;
				}

				app_touch_activity(app);
			}

			return;
		}
	}

	if ((held & KEY_TOUCH) && s_touch.active && s_touch.entry < 0) {
		touchPosition touch;
		hidTouchRead(&touch);

		/*
		 * Si le doigt quitte le bouton, on annule l'appui : c'est le
		 * comportement attendu d'une surface tactile et cela évite les
		 * déclenchements involontaires.
		 */
		const int slot = ui_slot_at((float)touch.px, (float)touch.py);
		if (slot != s_touch.slot) {
			s_touch.active = false;
			app->pressed_slot = -1;
		}
	}

	if (up & KEY_TOUCH) {
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

	/* --- Navigation dans une page en mode liste ---
	 *
	 * Répartition des commandes :
	 *   - la croix directionnelle choisit un élément ;
	 *   - le pavé circulaire fait défiler la liste ;
	 *   - `A` active l'élément choisi.
	 *
	 * Séparer la sélection du défilement permet de parcourir une longue liste
	 * sans perdre l'élément désigné, et de désigner précisément sans faire
	 * bouger l'affichage.
	 */
	{
		const Page *page = app_current_page(app);
		const bool is_list = (page != NULL) && page->layout == LAYOUT_LIST;

		if (is_list) {
			const int columns = ui_list_columns();
			const int rows = ui_list_rows();
			const float max_scroll = ui_list_max_scroll(app);

			/* Pavé circulaire : défilement continu, vitesse progressive. */
			circlePosition circle;
			hidCircleRead(&circle);

			/*
			 * Zone morte : le pavé ne revient jamais exactement au centre, et
			 * sans elle la liste dériverait en permanence.
			 */
			const float dead_zone = 22.0f;
			const float value = (float)circle.dy;

			if (value > dead_zone || value < -dead_zone) {
				const float amount =
				    (value - (value > 0.0f ? dead_zone : -dead_zone)) /
				    (154.0f - dead_zone);
				const float speed = amount * amount * amount * 9.0f;

				/* Le pavé pointé vers le haut fait remonter la liste. */
				app_scroll_list(app, -speed * FRAME_TIME, max_scroll);
				app_touch_activity(app);
			}

			/* Croix : déplacement de la sélection. */
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

			/* `A` active l'élément désigné. */
			if ((down & KEY_A) && app_list_focus(app) >= 0) {
				app_press_entry(app, app_list_focus(app), false);
			}

			/* `B` retire la sélection. */
			if (down & KEY_B) {
				app_clear_focus(app);
			}
		}
	}

	/* --- Pagination par les gâchettes --- */
	if (down & KEY_L) {
		app_cycle_page(app, -1);
	}
	if (down & KEY_R) {
		app_cycle_page(app, 1);
	}

	/* --- Commandes de la grille ---
	 *
	 * La répartition est la même que sur une page en liste : la croix déplace la
	 * sélection, `A` valide, `B` annule. Le comportement ne dépend donc plus de
	 * la page affichée.
	 *
	 * `X` et `Y` restent des raccourcis directs vers deux emplacements, ce qui
	 * permet de garder un accès immédiat sans passer par la sélection.
	 */
	{
		const Page *page = app_current_page(app);

		if (page != NULL && page->layout == LAYOUT_GRID) {
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
					/*
					 * Sans sélection, `A` désigne le premier emplacement : le
					 * bouton reste ainsi utilisable sans navigation préalable.
					 */
					app_move_grid_focus(app, 0, 0);
				}
			}

			if (down & KEY_B) {
				app_clear_focus(app);
			}

			/* Raccourcis directs, indépendants de la sélection. */
			if (down & KEY_X) {
				app_press_button(app, 2, false);
			}
			if (down & KEY_Y) {
				app_press_button(app, 3, false);
			}
		}
	}

	/* Demande explicite de rechargement de la configuration. */
	if (down & KEY_SELECT) {
		char payload[64];
		const int written = protocol_encode_config_request(
		    payload, sizeof(payload), app->next_request_id++);
		if (written > 0 && net_send(payload, (size_t)written)) {
			app_notify(app, tr(STR_CONFIG_REQUESTED), false);
		}
	}
}

int main(int argc, char *argv[])
{
	(void)argc;
	(void)argv;

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

	C3D_Init(C3D_DEFAULT_CMDBUF_SIZE);
	/*
	 * Le budget d'objets est relevé : en relief, l'écran supérieur est dessiné
	 * deux fois, et les icônes vectorielles consomment davantage de géométrie
	 * que des images. La mesure donne environ 3600 objets dans le pire cas,
	 * auxquels s'ajoute le texte.
	 */
	C2D_Init(C2D_DEFAULT_MAX_OBJECTS * 2);
	C2D_Prepare();

	C3D_RenderTarget *top = C2D_CreateScreenTarget(GFX_TOP, GFX_LEFT);
	/* Seconde image de l'écran supérieur, pour l'œil droit. */
	C3D_RenderTarget *top_right = C2D_CreateScreenTarget(GFX_TOP, GFX_RIGHT);
	C3D_RenderTarget *bottom = C2D_CreateScreenTarget(GFX_BOTTOM, GFX_LEFT);

	if (!text_init()) {
		/* Sans tampon de texte, l'interface serait muette : on s'arrête. */
		C2D_Fini();
		C3D_Fini();
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

	/* Mesure du temps réel : les animations restent correctes même si le
	 * nombre d'images par seconde varie. */
	u64 previous_tick = svcGetSystemTick();

	while (aptMainLoop()) {
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
		handle_input(&s_app);

		if (hidKeysDown() & KEY_START) {
			break;
		}

		/* --- Réseau et logique --- */
		if (network_ready) {
			app_pump_network(&s_app);
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

		/* --- Rendu --- */
		text_frame_begin();

		C3D_FrameBegin(C3D_FRAME_SYNCDRAW);

		/*
		 * Intensité du relief : produit du curseur de la console et du réglage
		 * de l'application. Une intensité nulle évite de dessiner la seconde
		 * image, et donc son coût.
		 */
		const float slider = osGet3DSliderState();
		const float depth_strength =
		    s_app.settings.stereo ? slider : 0.0f;
		const bool stereo = depth_strength > 0.01f;

		for (int eye = 0; eye < (stereo ? 2 : 1); eye++) {
			C3D_RenderTarget *target = (eye == 0) ? top : top_right;

			stereo_begin_eye(eye, depth_strength);

			C2D_TargetClear(target, COL_BG);
			C2D_SceneBegin(target);
			if (s_setup.active) {
				setup_draw_top(&s_setup, &s_app);
			} else {
				ui_draw_top(&s_app);
			}

			stereo_end_eye();
		}

		C2D_TargetClear(bottom, COL_BG);
		C2D_SceneBegin(bottom);
		if (s_setup.active) {
			setup_draw_bottom(&s_setup, &s_app);
		} else {
			ui_draw_bottom(&s_app);

			/* Le panneau se superpose à la page qu'il recouvre. */
			if (s_modal.active) {
				modal_draw(&s_modal, &s_app);
			}
		}

		C3D_FrameEnd(0);
	}

	/* --- Libération --- */
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
