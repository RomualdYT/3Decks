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

/* Preserve intrinsic alpha while fading all card elements together. */
static u32 entrance_color(u32 color, float opacity)
{
	return theme_alpha(color, (u8)roundf((float)(color >> 24) * opacity));
}

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

	/* 260 ms ease-out with a 20 ms wave across columns and rows.
	 * Physical pixel positions keep text and icons sharp during movement. */
	const float delay = (float)(slot % GRID_COLS + slot / GRID_COLS) * 0.02f;
	float appear = (app->enter_anim * 0.32f - delay) / 0.26f;
	if (appear < 0.0f) appear = 0.0f;
	if (appear > 1.0f) appear = 1.0f;
	const float inv = 1.0f - appear;
	const float eased = 1.0f - inv * inv * inv;
	if (eased <= 0.01f) return;
	const float rise = roundf((1.0f - eased) * 6.0f);
	const float x = rect.x;
	const float y = rect.y + rise + roundf(press);
	const float w = rect.w;
	const float h = rect.h;
	const float radius = 8.0f;

	const u32 accent = unavailable ? COL_TEXT_FAINT : button->color;

	const u32 base = C2D_Color32(0x19, 0x19, 0x1D, 0xFF);
	u32 top = theme_mix(base, accent, active ? 0.30f : 0.17f);
	if (feedback == ACTION_FEEDBACK_PENDING) {
		top = theme_mix(top, COL_ACCENT, 0.08f);
	} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
		top = theme_mix(top, COL_OK, 0.13f);
	} else if (feedback == ACTION_FEEDBACK_ERROR) {
		top = theme_mix(top, COL_ERR, 0.13f);
	}

	if (press > 0.01f) {
		top = theme_mix(top, COL_WHITE, press * 0.12f);
	}

	draw_round_rect(x, y, w, h, radius, Z_CARD, entrance_color(top, eased));

	const bool has_hold = button->hold_label[0] != '\0';
	const float text_block = 23.0f;
	const float cx = x + w * 0.5f;
	const float icon_cy = y + 29.0f;
	const float icon_size = 28.0f;

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
	u32 outline_color = theme_mix(COL_BORDER, accent, 0.45f);

	if (active) {
		outline = 1.5f;
		outline_color = theme_alpha(accent, 0xEE);
	}
	if (selected) {
		outline = 1.5f;
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
	                        entrance_color(outline_color, eased));

	const u32 icon_color =
	    active ? COL_WHITE : theme_mix(accent, COL_WHITE, 0.20f);

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

	icons_draw(icon, cx, icon_cy, icon_size, Z_OVERLAY, entrance_color(icon_color, eased));

	/* Anneau qui se remplit autour de l'icône pendant l'appui long. */
	const float hold_progress = app_hold_progress(app, slot);
	if (hold_progress > 0.0f) {
		const float ring_radius = icon_size * 0.80f;
		draw_ring(cx, icon_cy, ring_radius, 1.3f, Z_OVERLAY,
		          entrance_color(theme_alpha(COL_ACCENT, 0x3A), eased));
		draw_arc(cx, icon_cy, ring_radius, 2.2f, 0.0f, hold_progress,
		         Z_OVERLAY, entrance_color(COL_ACCENT, eased));
	}

	/* Le nom secondaire n'apparaît que pendant le geste qui le déclenche. */
	const float label_y = y + h - text_block + 2.0f;
	const bool showing_hold =
	    has_hold && app->pressed_slot == slot && app->press_time > 0.08f;
	const char *label = showing_hold ? button->hold_label : button->label;

	/* Si le texte est long (ex: « Navigateur », « Volumes »), on réduit la police
	 * d'un cran pour éviter de le tronquer avec des points de suspension. */
	float scale = TEXT_SMALL;
	if (text_width(label, scale) > w - 12.0f) {
		scale = TEXT_MICRO;
	}

	text_draw_clipped(cx, label_y, Z_OVERLAY, scale,
	                  entrance_color(active ? COL_WHITE : COL_TEXT, eased), ALIGN_CENTER, w - 12.0f,
	                  label);

	/* Trois points signalent sans texte qu'une action secondaire existe. */
	if (has_hold && !showing_hold) {
		const u32 marker = active ? theme_alpha(COL_WHITE, 0x8A)
		                          : theme_alpha(COL_TEXT_DIM, 0xB0);
		for (int i = 0; i < 3; i++) {
			draw_circle(x + 8.0f + (float)i * 4.0f, y + 9.0f,
			            1.0f, Z_OVERLAY, entrance_color(marker, eased));
		}
	}

	/*
	 * Pastille d'état : rend l'activation lisible d'un seul coup d'œil, même
	 * de loin ou de biais.
	 */
	if (feedback != ACTION_FEEDBACK_NONE && appear >= 1.0f) {
		draw_action_feedback(feedback, x + w - 11.0f, y + 11.0f,
		                     app->uptime);
	} else if (active) {
		draw_circle(x + w - 10.0f, y + 10.0f, 3.0f, Z_OVERLAY, entrance_color(COL_WHITE, eased));
	}
}
