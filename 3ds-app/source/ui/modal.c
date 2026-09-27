/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "modal.h"

#include <stdio.h>
#include <string.h>

#include "draw.h"
#include "i18n.h"
#include "icons.h"
#include "net.h"
#include "protocol.h"
#include "sound.h"
#include "text.h"
#include "theme.h"

/*
 * Intervalle minimal entre deux envois pendant un glissement.
 *
 * Transmettre une valeur à chaque pixel saturerait la liaison et l'ordinateur :
 * une centaine de millisecondes suffit à donner une impression de continuité,
 * et la valeur finale est toujours envoyée au relâchement.
 */
#define SEND_INTERVAL 0.12f

/* Géométrie du panneau. */
#define PANEL_X 12.0f
#define PANEL_W (SCREEN_BOTTOM_W - PANEL_X * 2.0f)
#define PANEL_Y 22.0f

/* Hauteur d'un interrupteur : deux lignes de texte et leurs marges. */
#define MUTE_H (TEXT_LINE_PX(TEXT_MICRO) * 2.0f + 10.0f)

/* Hauteur de la ligne de sortie audio. */
#define OUTPUT_H 24.0f
#define OUTPUT_LIST_Y 50.0f
#define OUTPUT_LIST_PITCH 26.0f
#define OUTPUT_LIST_VISIBLE 6

/* Pas vertical entre les deux curseurs. */
#define SLIDER_PITCH 42.0f

/*
 * Hauteur du panneau, déduite de son contenu.
 *
 * La calculer évite les chevauchements : une valeur fixe devenait fausse dès
 * qu'un élément grandissait, et la ligne de sortie finissait par recouvrir les
 * interrupteurs.
 */
#define PANEL_TOP_GAP 44.0f
#define PANEL_H                                                               \
	(PANEL_TOP_GAP + SLIDER_PITCH * 2.0f + OUTPUT_H + MUTE_H + 24.0f)

#define SLIDER_X (PANEL_X + 18.0f)
#define SLIDER_W (PANEL_W - 36.0f)
#define SLIDER_H 12.0f

/** Ordonnée du curseur d'une ligne. */
static float slider_y(int row)
{
	return PANEL_Y + PANEL_TOP_GAP + (float)row * SLIDER_PITCH;
}

/**
 * Emplacement de la ligne de sortie audio.
 *
 * Elle s'insère entre le dernier curseur et les interrupteurs : sa position est
 * donc calculée, non fixée, afin qu'un changement de hauteur des uns ou des
 * autres ne provoque pas de chevauchement.
 */
static void output_bounds(float *y, float *height)
{
	*height = OUTPUT_H;
	/* Juste sous le second curseur, avec une respiration. */
	*y = PANEL_Y + PANEL_TOP_GAP + SLIDER_PITCH * 2.0f - 4.0f;
}

/** Emplacement d'un des deux boutons de coupure. */
static void mute_bounds(int index, float *x, float *y, float *w, float *h)
{
	/*
	 * Hauteur calculée pour deux lignes de texte : le nom de l'objet et son
	 * état. Une valeur fixe trop courte les faisait déborder du cadre.
	 */
	*w = (PANEL_W - 42.0f) * 0.5f;
	*h = MUTE_H;
	*x = PANEL_X + 18.0f + (float)index * (*w + 6.0f);
	*y = PANEL_Y + PANEL_H - MUTE_H - 10.0f;
}

void modal_open(Modal *modal, const App *app)
{
	memset(modal, 0, sizeof(*modal));

	modal->active = true;
	modal->dragging = -1;
	modal->appear = 0.0f;

	/* Les valeurs de départ viennent de l'état transmis par l'ordinateur. */
	modal->system_volume = (app->state.volume >= 0) ? app->state.volume : 50;
	modal->music_volume =
	    (app->state.app_volume >= 0) ? app->state.app_volume : 50;
	for (int i = 0; i < app->state.audio_output_count; i++) {
		if (app->state.audio_outputs[i].active) {
			modal->output_focus = i;
			break;
		}
	}
}

void modal_close(Modal *modal)
{
	modal->active = false;
	modal->dragging = -1;
	modal->editing_system = false;
	modal->editing_music = false;
	modal->choosing_output = false;
}

/** Envoie la valeur d'un curseur à l'ordinateur. */
static void send_value(App *app, const char *target, int value)
{
	if (app->link != LINK_ONLINE) {
		return;
	}

	char payload[128];
	const int written = protocol_encode_value(payload, sizeof(payload),
	                                          app->next_request_id, target,
	                                          value);

	if (written > 0 && (size_t)written < sizeof(payload) &&
	    net_send(payload, (size_t)written)) {
		app->next_request_id++;
	}
}

static bool send_output_select(App *app, int index)
{
	if (app->link != LINK_ONLINE ||
	    app->state.audio_output_mode != AUDIO_OUTPUT_DIRECT || index < 0 ||
	    index >= app->state.audio_output_count) {
		return false;
	}
	const AudioOutput *output = &app->state.audio_outputs[index];
	if (output->id[0] == '\0' || output->active) {
		return false;
	}
	char payload[160];
	const int written = protocol_encode_audio_output_select(
	    payload, sizeof(payload), app->next_request_id, output->id);
	if (written <= 0 || (size_t)written >= sizeof(payload) ||
	    !net_send(payload, (size_t)written)) {
		app_notify(app, tr(STR_SEND_FAILED), true);
		return false;
	}
	app->next_request_id++;
	return true;
}

void modal_update(Modal *modal, App *app, float dt)
{
	if (!modal->active) {
		return;
	}
	if (modal->choosing_output) {
		if (app->state.audio_output_mode != AUDIO_OUTPUT_DIRECT ||
		    app->state.audio_output_count == 0) {
			modal->choosing_output = false;
		} else if (modal->output_focus >= app->state.audio_output_count) {
			modal->output_focus = app->state.audio_output_count - 1;
		}
	}

	if (modal->appear < 1.0f) {
		modal->appear += dt * 5.0f;
		if (modal->appear > 1.0f) {
			modal->appear = 1.0f;
		}
	}

	/*
	 * Les valeurs en attente sont transmises à intervalle régulier plutôt qu'à
	 * chaque déplacement : la liaison reste disponible et l'ordinateur n'est pas
	 * submergé.
	 */
	modal->send_timer += dt;

	if (modal->pending && modal->send_timer >= SEND_INTERVAL) {
		modal->send_timer = 0.0f;
		modal->pending = false;

		if (modal->editing_system) {
			send_value(app, "volume", modal->system_volume);
		}
		if (modal->editing_music) {
			send_value(app, "app_volume", modal->music_volume);
		}
	}

	/*
	 * Hors édition, l'affichage suit l'état réel : une modification faite
	 * ailleurs, au clavier par exemple, apparaît donc dans le panneau.
	 */
	if (modal->dragging < 0) {
		if (!modal->editing_system && app->state.volume >= 0) {
			modal->system_volume = app->state.volume;
		}
		if (!modal->editing_music && app->state.app_volume >= 0) {
			modal->music_volume = app->state.app_volume;
		}
	}
}

/* --- Rendu ---------------------------------------------------------------- */

/** Dessine un curseur avec son intitulé et sa valeur. */
static void draw_slider(int row, float offset, const char *label, int value,
                        u32 color, bool selected, bool active)
{
	/*
	 * Le décalage d'ouverture est reçu en paramètre : les curseurs doivent
	 * accompagner le panneau. Sans lui, ils restaient immobiles pendant que le
	 * cadre glissait, et semblaient flotter à côté.
	 */
	const float y = slider_y(row) + offset;

	/* Intitulé à gauche, valeur à droite, sur la même ligne. */
	char text[12];
	snprintf(text, sizeof(text), "%u %%", (unsigned)value % 101u);

	const float label_y = y - TEXT_LINE_PX(TEXT_SMALL) - 5.0f;

	text_draw(SLIDER_X, label_y, Z_MODAL_CONTENT, TEXT_SMALL,
	          selected ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT, label);
	text_draw(SLIDER_X + SLIDER_W, label_y, Z_MODAL_CONTENT, TEXT_SMALL,
	          active ? color : COL_TEXT_DIM, ALIGN_RIGHT, text);

	/* Rail puis remplissage. */
	draw_progress(SLIDER_X, y, SLIDER_W, SLIDER_H, (float)value / 100.0f,
	              Z_MODAL_CONTENT, theme_alpha(COL_SURFACE_HI, 0xEE), color);

	/*
	 * Poignée : elle matérialise le point de saisie et rend le curseur
	 * manifestement manipulable, là où une simple barre ressemblerait à un
	 * indicateur passif.
	 */
	const float knob_x =
	    SLIDER_X + SLIDER_W * ((float)value / 100.0f);
	const float knob_r = selected ? 9.0f : 7.5f;
	const float middle = y + SLIDER_H * 0.5f;

	draw_circle(knob_x, middle, knob_r + 1.5f, Z_MODAL_TOP,
	            theme_alpha(COL_BG, 0xCC));
	draw_circle(knob_x, middle, knob_r, Z_MODAL_TOP, COL_WHITE);
	draw_circle(knob_x, middle, knob_r * 0.45f, Z_MODAL_TOP, color);

	if (selected) {
		draw_ring(knob_x, middle, knob_r + 4.0f, 1.2f, Z_MODAL_TOP,
		          theme_alpha(color, 0x99));
	}
}

static void draw_output_choices(const Modal *modal, const App *app, float offset)
{
	const float y = 14.0f + offset;
	draw_shadow(PANEL_X, y, PANEL_W, 214.0f, 12.0f, Z_MODAL_VEIL);
	draw_round_rect_vgrad(PANEL_X, y, PANEL_W, 214.0f, 12.0f,
	                      Z_MODAL_CARD, COL_SURFACE_HI, COL_SURFACE_LO);
	draw_round_rect_outline(PANEL_X, y, PANEL_W, 214.0f, 12.0f, 1.0f,
	                        Z_MODAL_CONTENT, theme_alpha(COL_ACCENT, 0x66));
	text_draw(PANEL_X + 16.0f, y + 11.0f, Z_MODAL_TOP, TEXT_LARGE,
	          COL_TEXT, ALIGN_LEFT, tr(STR_AUDIO_OUTPUT));
	text_draw(PANEL_X + PANEL_W - 15.0f, y + 15.0f, Z_MODAL_TOP,
	          TEXT_MICRO, COL_TEXT_DIM, ALIGN_RIGHT, tr(STR_BACK));

	const int first = (modal->output_focus / OUTPUT_LIST_VISIBLE) *
	                  OUTPUT_LIST_VISIBLE;
	for (int slot = 0; slot < OUTPUT_LIST_VISIBLE; slot++) {
		const int index = first + slot;
		if (index >= app->state.audio_output_count) break;
		const AudioOutput *output = &app->state.audio_outputs[index];
		const float row_y = OUTPUT_LIST_Y + slot * OUTPUT_LIST_PITCH + offset;
		const bool focused = index == modal->output_focus;
		const u32 color = output->active ? COL_ACCENT : COL_TEXT_DIM;
		draw_round_rect(SLIDER_X, row_y, SLIDER_W, 24.0f, 7.0f,
		                Z_MODAL_CONTENT,
		                focused ? theme_alpha(COL_ACCENT, 0x33)
		                        : theme_alpha(COL_SURFACE, 0xAA));
		if (focused) {
			draw_round_rect_outline(SLIDER_X, row_y, SLIDER_W, 24.0f,
			                        7.0f, 1.0f, Z_MODAL_TOP,
			                        theme_alpha(COL_ACCENT, 0x99));
		}
		draw_circle(SLIDER_X + 13.0f, row_y + 12.0f, 4.0f,
		            Z_MODAL_TOP, output->active ? color : COL_BORDER);
		if (output->active) {
			draw_circle(SLIDER_X + 13.0f, row_y + 12.0f, 2.0f,
			            Z_MODAL_TOP, COL_WHITE);
		}
		text_draw_clipped(SLIDER_X + 25.0f, row_y + 5.0f, Z_MODAL_TOP,
		                  TEXT_SMALL, focused ? COL_TEXT : COL_TEXT_DIM,
		                  ALIGN_LEFT, output->active ? SLIDER_W - 100.0f
		                                             : SLIDER_W - 36.0f,
		                  output->name);
		if (output->active) {
			text_draw(SLIDER_X + SLIDER_W - 9.0f, row_y + 7.0f,
			          Z_MODAL_TOP, TEXT_MICRO, color, ALIGN_RIGHT,
			          tr(STR_OUTPUT_ACTIVE));
		}
	}
	if (app->state.audio_output_count > OUTPUT_LIST_VISIBLE) {
		char page[40];
		snprintf(page, sizeof(page), "<  %d / %d  >",
		         first / OUTPUT_LIST_VISIBLE + 1,
		         (app->state.audio_output_count + OUTPUT_LIST_VISIBLE - 1) /
		             OUTPUT_LIST_VISIBLE);
		text_draw(SCREEN_BOTTOM_W * 0.5f, y + 194.0f, Z_MODAL_TOP,
		          TEXT_MICRO, COL_TEXT_DIM, ALIGN_CENTER, page);
	}
}

void modal_draw(const Modal *modal, const App *app)
{
	/*
	 * Voile assombrissant, tracé au-dessus de toute la page.
	 *
	 * Il doit occulter les boutons et leurs icônes : dessiné à la profondeur du
	 * fond, il passait dessous et n'assombrissait rien, laissant la grille se
	 * mêler au panneau.
	 */
	const u8 veil = (u8)(modal->appear * 0xE0);
	draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_MODAL_VEIL,
	          C2D_Color32(0x04, 0x05, 0x09, veil));

	/* Le panneau glisse légèrement en apparaissant. */
	const float offset = (1.0f - modal->appear) * 12.0f;
	if (modal->choosing_output) {
		draw_output_choices(modal, app, offset);
		return;
	}
	const float y = PANEL_Y + offset;

	draw_shadow(PANEL_X, y, PANEL_W, PANEL_H, 12.0f, Z_MODAL_VEIL);
	draw_round_rect_vgrad(PANEL_X, y, PANEL_W, PANEL_H, 12.0f, Z_MODAL_CARD,
	                      COL_SURFACE_HI, COL_SURFACE_LO);
	draw_round_rect_outline(PANEL_X, y, PANEL_W, PANEL_H, 12.0f, 1.0f, Z_MODAL_CONTENT,
	                        theme_alpha(COL_ACCENT, 0x66));

	/* Titre et croix de fermeture. */
	text_draw(PANEL_X + 18.0f, y + 10.0f, Z_MODAL_CONTENT, TEXT_LARGE, COL_TEXT,
	          ALIGN_LEFT, tr(STR_VOLUMES));

	const float close_cx = PANEL_X + PANEL_W - 20.0f;
	const float close_cy = y + 20.0f;
	draw_circle(close_cx, close_cy, 11.0f, Z_MODAL_CONTENT,
	            theme_alpha(COL_SURFACE, 0xCC));
	draw_line(close_cx - 4.0f, close_cy - 4.0f, close_cx + 4.0f,
	          close_cy + 4.0f, 1.8f, Z_MODAL_TOP, COL_TEXT_DIM);
	draw_line(close_cx - 4.0f, close_cy + 4.0f, close_cx + 4.0f,
	          close_cy - 4.0f, 1.8f, Z_MODAL_TOP, COL_TEXT_DIM);

	/* Les deux volumes, visibles ensemble. */
	draw_slider(MODAL_ROW_SYSTEM, offset, tr(STR_VOLUME_PC),
	            modal->system_volume,
	            app->state.muted ? COL_ERR : COL_ACCENT,
	            modal->row == MODAL_ROW_SYSTEM, !app->state.muted);

	draw_slider(MODAL_ROW_MUSIC, offset, tr(STR_MUSIC), modal->music_volume,
	            COL_BLUE, modal->row == MODAL_ROW_MUSIC, true);

	/* Sortie audio : la sélection directe dépend des capacités de l'agent. */
	float out_y;
	float out_h;
	output_bounds(&out_y, &out_h);
	out_y += offset;

	const bool can_choose = app->state.audio_output_mode ==
	                        AUDIO_OUTPUT_DIRECT &&
	                        app->state.audio_output_count > 0;
	const bool out_selected = can_choose && modal->row == MODAL_ROW_OUTPUT;

	draw_round_rect(SLIDER_X, out_y, SLIDER_W, out_h, 7.0f, Z_MODAL_CONTENT,
	                out_selected ? theme_alpha(COL_ACCENT, 0x33)
	                             : theme_alpha(COL_SURFACE, 0xAA));
	if (out_selected) {
		draw_round_rect_outline(SLIDER_X, out_y, SLIDER_W, out_h, 7.0f, 1.0f,
		                        Z_MODAL_TOP, theme_alpha(COL_ACCENT, 0x99));
	}

	icons_draw(ICON_VOLUME_UP, SLIDER_X + 14.0f, out_y + out_h * 0.5f, 13.0f,
	           Z_MODAL_TOP, out_selected ? COL_ACCENT : COL_TEXT_DIM);

	const float out_text_y = out_y + (out_h - TEXT_LINE_PX(TEXT_MICRO)) * 0.5f;
	text_draw_clipped(SLIDER_X + 26.0f, out_text_y, Z_MODAL_TOP, TEXT_MICRO,
	                  out_selected ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT,
	                  SLIDER_W - 70.0f,
	                  app->state.audio_output[0] != '\0'
	                      ? app->state.audio_output
	                      : tr(STR_OUTPUT_UNKNOWN));
	if (can_choose || app->state.audio_output_mode == AUDIO_OUTPUT_HOST_ONLY) {
		text_draw(SLIDER_X + SLIDER_W - 10.0f, out_text_y, Z_MODAL_TOP,
		          TEXT_MICRO, out_selected ? COL_ACCENT : COL_TEXT_FAINT,
		          ALIGN_RIGHT, can_choose ? ">" : "PC");
	}

	/*
	 * Interrupteurs de coupure.
	 *
	 * Chaque bouton nomme l'objet qu'il commande, et affiche son état en
	 * dessous. Le libellé précédent décrivait l'état sur la ligne principale,
	 * ce qui prêtait à confusion : « Micro actif » sur un bouton laissait croire
	 * qu'appuyer allait l'activer, alors que cela le coupe.
	 *
	 * Un témoin lumineux renforce la lecture : vert lorsque le son passe, rouge
	 * lorsqu'il est coupé.
	 */
	for (int i = 0; i < 2; i++) {
		float bx;
		float by;
		float bw;
		float bh;
		mute_bounds(i, &bx, &by, &bw, &bh);
		by += offset;

		const bool muted = (i == 0) ? app->state.muted : app->state.mic_muted;
		const bool known = (i == 0) || app->state.mic_known;
		const bool selected = modal->row == MODAL_ROW_MUTES &&
		                      modal->mute_focus == i;

		const u32 accent = muted ? COL_ERR : COL_OK;

		draw_round_rect_vgrad(bx, by, bw, bh, 8.0f, Z_MODAL_CARD,
		                      muted ? theme_mix(COL_SURFACE_HI, COL_ERR, 0.30f)
		                            : COL_SURFACE_HI,
		                      muted ? theme_mix(COL_SURFACE_LO, COL_ERR, 0.16f)
		                            : COL_SURFACE_LO);

		draw_round_rect_outline(bx, by, bw, bh, 8.0f, selected ? 1.6f : 1.0f,
		                        Z_MODAL_CONTENT,
		                        selected ? COL_WHITE
		                                 : theme_alpha(known ? accent
		                                                     : COL_BORDER,
		                                               muted ? 0xBB : 0x66));

		/* Icône à gauche, barrée lorsque la source est coupée. */
		const IconId icon = (i == 0)
		                        ? (muted ? ICON_VOLUME_MUTE : ICON_VOLUME_UP)
		                        : (muted ? ICON_MIC_OFF : ICON_MIC);

		icons_draw(icon, bx + 17.0f, by + bh * 0.5f, 16.0f, Z_MODAL_TOP,
		           known ? accent : COL_TEXT_FAINT);

		/* Nom de l'objet commandé, puis son état. */
		const float text_x = bx + 31.0f;
		const float text_w = bw - 44.0f;

		text_draw_clipped(text_x, by + 5.0f, Z_MODAL_TOP, TEXT_MICRO,
		                  COL_TEXT, ALIGN_LEFT, text_w,
		                  (i == 0) ? tr(STR_SPEAKERS) : tr(STR_MICROPHONE));

		const char *state;
		if (!known) {
			state = "--";
		} else {
			state = muted ? tr(STR_MUTED) : tr(STR_LIVE);
		}

		text_draw_clipped(text_x, by + 5.0f + TEXT_LINE_PX(TEXT_MICRO),
		                  Z_MODAL_TOP, TEXT_MICRO,
		                  known ? accent : COL_TEXT_FAINT, ALIGN_LEFT, text_w,
		                  state);

		/* Témoin lumineux, à droite. */
		if (known) {
			const float dot_x = bx + bw - 11.0f;
			const float dot_y = by + bh * 0.5f;

			draw_circle(dot_x, dot_y, 4.5f, Z_MODAL_TOP,
			            theme_alpha(accent, 0x44));
			draw_circle(dot_x, dot_y, 2.5f, Z_MODAL_TOP, accent);
		}
	}
}

void modal_draw_top(const Modal *modal, const App *app)
{
	(void)modal;
	(void)app;
}

/* --- Interaction ---------------------------------------------------------- */

/** Convertit une abscisse en valeur de curseur. */
static int value_from_x(float x)
{
	float ratio = (x - SLIDER_X) / SLIDER_W;

	if (ratio < 0.0f) {
		ratio = 0.0f;
	}
	if (ratio > 1.0f) {
		ratio = 1.0f;
	}

	return (int)(ratio * 100.0f + 0.5f);
}

/** Applique une valeur au curseur indiqué. */
static void set_row_value(Modal *modal, int row, int value)
{
	if (value < 0) {
		value = 0;
	}
	if (value > 100) {
		value = 100;
	}

	if (row == MODAL_ROW_SYSTEM) {
		if (modal->system_volume != value) {
			modal->system_volume = value;
			modal->editing_system = true;
			modal->pending = true;
		}
	} else if (row == MODAL_ROW_MUSIC) {
		if (modal->music_volume != value) {
			modal->music_volume = value;
			modal->editing_music = true;
			modal->pending = true;
		}
	}
}

/** Transmet immédiatement les valeurs en attente. */
static void flush(Modal *modal, App *app)
{
	if (modal->editing_system) {
		send_value(app, "volume", modal->system_volume);
	}
	if (modal->editing_music) {
		send_value(app, "app_volume", modal->music_volume);
	}

	modal->pending = false;
	modal->editing_system = false;
	modal->editing_music = false;
}

static void open_output_choices(Modal *modal, const App *app)
{
	if (app->state.audio_output_mode != AUDIO_OUTPUT_DIRECT ||
	    app->state.audio_output_count == 0) {
		return;
	}
	modal->choosing_output = true;
	for (int i = 0; i < app->state.audio_output_count; i++) {
		if (app->state.audio_outputs[i].active) {
			modal->output_focus = i;
			break;
		}
	}
	sound_play(SOUND_PAGE);
}

static void choose_output(Modal *modal, App *app, int index)
{
	if (index < 0 || index >= app->state.audio_output_count) return;
	if (!app->state.audio_outputs[index].active &&
	    !send_output_select(app, index)) return;
	modal->choosing_output = false;
	sound_play(SOUND_TOGGLE);
}

bool modal_touch(Modal *modal, App *app, float x, float y, bool pressed,
                 bool released)
{
	if (!modal->active) {
		return false;
	}

	if (released) {
		/*
		 * Fin du geste : la valeur exacte est transmise sans attendre le
		 * prochain intervalle, pour que le résultat corresponde au relâchement.
		 */
		if (modal->dragging >= 0) {
			flush(modal, app);
		}
		modal->dragging = -1;
		return true;
	}

	/* Poursuite d'un glissement. */
	if (!pressed && modal->dragging >= 0) {
		set_row_value(modal, modal->dragging, value_from_x(x));
		return true;
	}

	if (!pressed) {
		return true;
	}

	if (modal->choosing_output) {
		if (x < PANEL_X || x > PANEL_X + PANEL_W || y < 14.0f ||
		    y > 228.0f || y < 46.0f) {
			modal->choosing_output = false;
			sound_play(SOUND_PAGE);
			return true;
		}
		if (y >= OUTPUT_LIST_Y &&
		    y < OUTPUT_LIST_Y + OUTPUT_LIST_VISIBLE * OUTPUT_LIST_PITCH) {
			const int first = (modal->output_focus / OUTPUT_LIST_VISIBLE) *
			                  OUTPUT_LIST_VISIBLE;
			const int index = first +
			                  (int)((y - OUTPUT_LIST_Y) / OUTPUT_LIST_PITCH);
			if (index < app->state.audio_output_count) {
				modal->output_focus = index;
				choose_output(modal, app, index);
			}
			return true;
		}
		if (y >= 207.0f &&
		    app->state.audio_output_count > OUTPUT_LIST_VISIBLE) {
			const int page = modal->output_focus / OUTPUT_LIST_VISIBLE;
			const int pages = (app->state.audio_output_count +
			                   OUTPUT_LIST_VISIBLE - 1) / OUTPUT_LIST_VISIBLE;
			const int next = x < SCREEN_BOTTOM_W * 0.5f
			                     ? (page + pages - 1) % pages
			                     : (page + 1) % pages;
			modal->output_focus = next * OUTPUT_LIST_VISIBLE;
			sound_play(SOUND_PAGE);
		}
		return true;
	}

	/* Croix de fermeture. */
	const float close_cx = PANEL_X + PANEL_W - 20.0f;
	const float close_cy = PANEL_Y + 20.0f;
	const float dx = x - close_cx;
	const float dy = y - close_cy;
	if (dx * dx + dy * dy <= 16.0f * 16.0f) {
		flush(modal, app);
		modal_close(modal);
		sound_play(SOUND_PAGE);
		return true;
	}

	/* Contact en dehors du panneau : fermeture, geste attendu d'une modale. */
	if (x < PANEL_X || x > PANEL_X + PANEL_W || y < PANEL_Y ||
	    y > PANEL_Y + PANEL_H) {
		flush(modal, app);
		modal_close(modal);
		return true;
	}

	/* Curseurs : la zone de saisie est élargie pour rester confortable. */
	for (int row = 0; row < 2; row++) {
		const float sy = slider_y(row);

		if (y >= sy - 14.0f && y <= sy + SLIDER_H + 14.0f) {
			modal->row = row;
			modal->dragging = row;
			set_row_value(modal, row, value_from_x(x));
			sound_play(SOUND_TAP);
			return true;
		}
	}

	/* Sortie audio. */
	float out_y;
	float out_h;
	output_bounds(&out_y, &out_h);

	if (y >= out_y && y <= out_y + out_h) {
		modal->row = MODAL_ROW_OUTPUT;
		if (app->state.audio_output_mode == AUDIO_OUTPUT_HOST_ONLY) {
			app_notify(app, tr(STR_OUTPUT_CHANGE_PC), false);
		} else {
			open_output_choices(modal, app);
		}
		return true;
	}

	/* Coupures. */
	for (int i = 0; i < 2; i++) {
		float bx;
		float by;
		float bw;
		float bh;
		mute_bounds(i, &bx, &by, &bw, &bh);

		if (x >= bx && x <= bx + bw && y >= by && y <= by + bh) {
			modal->row = MODAL_ROW_MUTES;
			modal->mute_focus = i;
			app_press_action(app, i == 0 ? "volume.mute_toggle"
			                            : "mic.mute_toggle");
			sound_play(SOUND_TOGGLE);
			return true;
		}
	}

	return true;
}

void modal_buttons(Modal *modal, App *app, u32 pressed)
{
	if (!modal->active) {
		return;
	}

	if (modal->choosing_output) {
		if (pressed & KEY_B) {
			modal->choosing_output = false;
			sound_play(SOUND_PAGE);
		} else if (pressed & KEY_UP) {
			modal->output_focus = (modal->output_focus +
			                       app->state.audio_output_count - 1) %
			                      app->state.audio_output_count;
			sound_play(SOUND_PAGE);
		} else if (pressed & KEY_DOWN) {
			modal->output_focus = (modal->output_focus + 1) %
			                      app->state.audio_output_count;
			sound_play(SOUND_PAGE);
		} else if (pressed & KEY_A) {
			choose_output(modal, app, modal->output_focus);
		}
		return;
	}

	if (pressed & (KEY_B | KEY_START)) {
		flush(modal, app);
		modal_close(modal);
		sound_play(SOUND_PAGE);
		return;
	}

	if (pressed & KEY_DOWN) {
		modal->row = (modal->row + 1) % MODAL_ROW_COUNT;
		sound_play(SOUND_PAGE);
	}
	if (pressed & KEY_UP) {
		modal->row = (modal->row + MODAL_ROW_COUNT - 1) % MODAL_ROW_COUNT;
		sound_play(SOUND_PAGE);
	}

	/*
	 * La croix ajuste finement : cinq points par appui, ce qui permet de viser
	 * une valeur précise là où le glissement au stylet est plus approximatif.
	 */
	const int step = 5;

	if (pressed & (KEY_LEFT | KEY_RIGHT)) {
		const int delta = (pressed & KEY_RIGHT) ? step : -step;

		if (modal->row == MODAL_ROW_MUTES) {
			/* Sur la ligne des coupures, la croix change d'interrupteur. */
			modal->mute_focus = (pressed & KEY_RIGHT) ? 1 : 0;
			sound_play(SOUND_PAGE);
		} else if (modal->row == MODAL_ROW_SYSTEM) {
			set_row_value(modal, MODAL_ROW_SYSTEM,
			              modal->system_volume + delta);
			flush(modal, app);
		} else if (modal->row == MODAL_ROW_MUSIC) {
			set_row_value(modal, MODAL_ROW_MUSIC, modal->music_volume + delta);
			flush(modal, app);
		}
	}

	if (pressed & (KEY_ZL | KEY_ZR)) {
		const int delta = (pressed & KEY_ZR) ? step : -step;
		set_row_value(modal, MODAL_ROW_SYSTEM, modal->system_volume + delta);
		flush(modal, app);
	}

	if (pressed & KEY_A) {
		if (modal->row == MODAL_ROW_OUTPUT) {
			if (app->state.audio_output_mode == AUDIO_OUTPUT_HOST_ONLY) {
				app_notify(app, tr(STR_OUTPUT_CHANGE_PC), false);
			} else {
				open_output_choices(modal, app);
			}
		} else if (modal->row == MODAL_ROW_MUTES) {
			app_press_action(app, modal->mute_focus == 0
			                          ? "volume.mute_toggle"
			                          : "mic.mute_toggle");
			sound_play(SOUND_TOGGLE);
		}
	}
}
