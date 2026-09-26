/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "draw.h"
#include "i18n.h"
#include "icons.h"
#include "text.h"
#include "theme.h"
#include "ui.h"
#include "extension_ui.h"

#include "ui_bottom_internal.h"

/** Dessine un bouton de la grille. */
void draw_button(const App *app, const Button *button, int slot)
{
	const Rect rect = slot_rect(slot);

	if (!button->used) {
		/*
		 * Emplacement vide : un contour en pointillés indique qu'il est
		 * disponible, sans donner l'illusion d'un bouton actionnable.
		 */
		const u32 faint = theme_alpha(COL_BORDER, 0x55);
		const float dash = 5.0f;
		for (float dx = rect.x + 10.0f; dx < rect.x + rect.w - 10.0f;
		     dx += dash * 2.0f) {
			draw_rect(dx, rect.y, dash, 1.0f, Z_CARD, faint);
			draw_rect(dx, rect.y + rect.h - 1.0f, dash, 1.0f, Z_CARD, faint);
		}
		for (float dy = rect.y + 10.0f; dy < rect.y + rect.h - 10.0f;
		     dy += dash * 2.0f) {
			draw_rect(rect.x, dy, 1.0f, dash, Z_CARD, faint);
			draw_rect(rect.x + rect.w - 1.0f, dy, 1.0f, dash, Z_CARD, faint);
		}
		return;
	}

	const Page *page = app_current_page(app);
	const ExtensionButtonState *extension = page ?
	    extension_button_state(&app->state, page->id, button->id) : NULL;
	const bool unavailable = extension && !extension->available;
	const bool active = extension ? extension->active : model_toggle_active(&app->state, button->toggle);
	const ActionFeedbackState feedback =
	    page != NULL ? app_action_feedback(app, page->id, button->id)
	                 : ACTION_FEEDBACK_NONE;
	const float press = button->press;

	/*
	 * Animation d'entrée en cascade.
	 *
	 * Volontairement discrète : un simple fondu accompagné d'un glissement de
	 * quelques pixels. Une variation d'échelle attirait trop l'attention et
	 * donnait une impression d'agitation à chaque changement de page.
	 *
	 * Le décalage entre emplacements reste faible : la cascade doit se
	 * percevoir sans qu'on ait à l'attendre.
	 */
	const float stagger = (float)slot * 0.05f;
	float appear = (app->enter_anim - stagger) / (1.0f - stagger * 0.5f);
	if (appear < 0.0f) {
		appear = 0.0f;
	}
	if (appear > 1.0f) {
		appear = 1.0f;
	}

	/* Amortissement cubique : départ franc, arrivée très douce. */
	const float inv = 1.0f - appear;
	const float eased = 1.0f - inv * inv * inv;

	if (eased <= 0.01f) {
		return; /* pas encore apparu */
	}

	/*
	 * L'enfoncement réduit légèrement la carte et supprime son ombre : le
	 * retour visuel est immédiat même sans retour haptique.
	 */
	const float shrink = press * 2.5f;

	/*
	 * Le bouton conserve sa taille et se contente de glisser vers sa place.
	 * Sans variation d'échelle, l'entrée paraît nettement plus posée.
	 */
	const float rise = (1.0f - eased) * 5.0f;

	const float x = rect.x + shrink;
	const float y = rect.y + shrink + rise;
	const float w = rect.w - shrink * 2.0f;
	const float h = rect.h - shrink * 2.0f;
	const float radius = 11.0f;

	const u32 accent = unavailable ? COL_TEXT_FAINT : button->color;

	u32 top;
	u32 bottom;
	if (active) {
		/* État actif : la couleur d'accent imprègne toute la carte. */
		top = theme_mix(COL_SURFACE_HI, accent, 0.50f);
		bottom = theme_mix(COL_SURFACE_LO, accent, 0.30f);
	} else {
		top = COL_SURFACE_HI;
		bottom = COL_SURFACE_LO;
	}
	if (feedback == ACTION_FEEDBACK_PENDING) {
		top = theme_mix(top, COL_ACCENT, 0.08f);
	} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
		top = theme_mix(top, COL_OK, 0.13f);
	} else if (feedback == ACTION_FEEDBACK_ERROR) {
		top = theme_mix(top, COL_ERR, 0.13f);
	}

	if (press > 0.01f) {
		top = theme_mix(top, COL_WHITE, press * 0.12f);
		bottom = theme_mix(bottom, COL_WHITE, press * 0.07f);
	}

	if (press < 0.5f) {
		draw_shadow(x, y, w, h, radius, Z_BG);
	}
	draw_round_rect_vgrad(x, y, w, h, radius, Z_CARD, top, bottom);

	/*
	 * Halo coloré derrière l'icône : apporte de la profondeur et rappelle la
	 * couleur du bouton même lorsqu'il est au repos.
	 */
	/*
	 * Répartition verticale, calculée depuis le bas.
	 *
	 * L'action secondaire ne réserve plus une ligne permanente. Son marqueur
	 * reste visible dans un coin, et son nom ne remplace le libellé principal
	 * que pendant le geste de maintien.
	 */
	const bool has_hold = button->hold_label[0] != '\0';

	const float label_h = TEXT_LINE_PX(TEXT_BODY);
	const float text_block = label_h + 5.0f;

	const float cx = x + w * 0.5f;
	/* L'icône se centre dans l'espace laissé au-dessus du texte. */
	const float icon_zone = h - text_block;
	const float icon_cy = y + icon_zone * 0.52f;
	const float icon_size = icon_zone * 0.62f;

	draw_circle(cx, icon_cy, icon_size * 0.78f, Z_CONTENT,
	            theme_alpha(accent, active ? 0x3A : 0x1E));

	/*
	 * Contour : il distingue trois états.
	 *
	 * L'état actif traduit une information venue de l'ordinateur, par exemple un
	 * micro coupé. La sélection, elle, indique seulement où se trouve le
	 * curseur : elle emprunte donc la couleur d'accent de l'interface plutôt que
	 * celle du bouton, pour ne pas être confondue avec un état.
	 */
	const bool selected = (slot == app->grid_focus);

	float outline = 1.0f;
	u32 outline_color = theme_alpha(COL_BORDER, 0xAA);

	if (active) {
		outline = 1.8f;
		outline_color = theme_alpha(accent, 0xEE);
	}
	if (selected) {
		outline = 2.2f;
		outline_color = COL_WHITE;
	}
	if (feedback == ACTION_FEEDBACK_PENDING) {
		outline = 1.6f;
		outline_color = theme_alpha(COL_ACCENT, 0xD0);
	} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
		outline = 2.0f;
		outline_color = COL_OK;
	} else if (feedback == ACTION_FEEDBACK_ERROR) {
		outline = 2.0f;
		outline_color = COL_ERR;
	}

	draw_round_rect_outline(x, y, w, h, radius, outline, Z_CONTENT,
	                        outline_color);

	/* Halo extérieur : rend la sélection lisible même de biais. */
	if (selected) {
		draw_round_rect_outline(x - 2.0f, y - 2.0f, w + 4.0f, h + 4.0f,
		                        radius + 2.0f, 1.0f, Z_CONTENT,
		                        theme_alpha(COL_WHITE, 0x55));
	}

	/* Liseré supérieur : simule une lumière venant du haut. */
	draw_rect(x + radius, y + 1.0f, w - radius * 2.0f, 1.0f, Z_CONTENT,
	          theme_alpha(COL_WHITE, active ? 0x38 : 0x16));

	const u32 icon_color =
	    active ? COL_WHITE : theme_mix(accent, COL_WHITE, 0.30f);

	/*
	 * L'icône bascule automatiquement lorsque l'état est actif : un bouton
	 * « micro » doit montrer un micro barré quand le micro est coupé, sans
	 * qu'il faille deux boutons distincts.
	 */
	IconId icon = button->icon;
	if (active) {
		if (icon == ICON_MIC) {
			icon = ICON_MIC_OFF;
		} else if (icon == ICON_PLAY) {
			icon = ICON_PAUSE;
		}
	}

	icons_draw(icon, cx, icon_cy, icon_size, Z_OVERLAY, icon_color);

	/* Anneau qui se remplit autour de l'icône pendant l'appui long. */
	const float hold_progress = app_hold_progress(app, slot);
	if (hold_progress > 0.0f) {
		const float ring_radius = icon_size * 0.80f;
		draw_ring(cx, icon_cy, ring_radius, 1.3f, Z_OVERLAY,
		          theme_alpha(COL_ACCENT, 0x3A));
		draw_arc(cx, icon_cy, ring_radius, 2.2f, 0.0f, hold_progress,
		         Z_OVERLAY, COL_ACCENT);
	}

	/* Le nom secondaire n'apparaît que pendant le geste qui le déclenche. */
	const float label_y = y + h - text_block + 2.0f;
	const bool showing_hold =
	    has_hold && app->pressed_slot == slot && app->press_time > 0.08f;
	const char *label = showing_hold ? button->hold_label : button->label;

	/* Si le texte est long (ex: « Navigateur », « Volumes »), on réduit la police
	 * d'un cran pour éviter de le tronquer avec des points de suspension. */
	float scale = TEXT_BODY;
	if (text_width(label, scale) > w - 8.0f) {
		scale = TEXT_SMALL;
	}

	text_draw_clipped(cx, label_y, Z_OVERLAY, scale,
	                  active ? COL_WHITE : COL_TEXT, ALIGN_CENTER, w - 6.0f,
	                  label);

	/* Trois points signalent sans texte qu'une action secondaire existe. */
	if (has_hold && !showing_hold) {
		const u32 marker = active ? theme_alpha(COL_WHITE, 0x8A)
		                          : theme_alpha(COL_TEXT_DIM, 0xB0);
		for (int i = 0; i < 3; i++) {
			draw_circle(x + w - 15.0f + (float)i * 4.0f, y + h - 8.0f,
			            1.0f, Z_OVERLAY, marker);
		}
	}

	/*
	 * Pastille d'état : rend l'activation lisible d'un seul coup d'œil, même
	 * de loin ou de biais.
	 */
	if (feedback != ACTION_FEEDBACK_NONE) {
		draw_action_feedback(feedback, x + w - 11.0f, y + 11.0f,
		                     app->uptime);
	} else if (active) {
		draw_circle(x + w - 10.0f, y + 10.0f, 3.0f, Z_OVERLAY, COL_WHITE);
	}
}
