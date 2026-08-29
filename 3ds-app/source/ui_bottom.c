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

/*
 * L'écran inférieur est la surface de contrôle : une grille de 3x2 boutons,
 * une barre de titre et une barre d'onglets pour les pages.
 *
 * La géométrie est calculée par une seule fonction, utilisée à la fois par le
 * rendu et par la détection tactile. C'est indispensable : deux calculs
 * séparés finiraient par divulguer, et les boutons ne répondraient plus là où
 * ils sont dessinés.
 */

#define TAB_H 28.0f

typedef struct {
	float x;
	float y;
	float w;
	float h;
} Rect;

static Rect slot_rect(int slot)
{
	const int col = slot % GRID_COLS;
	const int row = slot / GRID_COLS;

	const float area_w = SCREEN_BOTTOM_W - GRID_MARGIN_X * 2.0f;
	const float area_h = SCREEN_H - GRID_TOP - GRID_BOTTOM_BAR;

	const float cell_w = (area_w - GRID_GAP * (GRID_COLS - 1)) / GRID_COLS;
	const float cell_h = (area_h - GRID_GAP * (GRID_ROWS - 1)) / GRID_ROWS;

	Rect rect;
	rect.x = GRID_MARGIN_X + (float)col * (cell_w + GRID_GAP);
	rect.y = GRID_TOP + (float)row * (cell_h + GRID_GAP);
	rect.w = cell_w;
	rect.h = cell_h;
	return rect;
}

int ui_slot_at(float x, float y)
{
	for (int slot = 0; slot < GRID_SLOTS; slot++) {
		const Rect rect = slot_rect(slot);
		if (x >= rect.x && x < rect.x + rect.w && y >= rect.y &&
		    y < rect.y + rect.h) {
			return slot;
		}
	}
	return -1;
}

/** Largeur réservée au bouton des réglages, à droite de la barre. */
#define SETTINGS_TAB_W 34.0f

/**
 * Emplacement du bouton des réglages.
 *
 * Il occupe une place fixe à droite de la barre : toujours accessible, il ne
 * dépend pas du nombre de pages et reste au même endroit quelle que soit la
 * configuration.
 */
static Rect settings_rect(void)
{
	Rect rect;
	rect.w = SETTINGS_TAB_W;
	rect.h = TAB_H - 4.0f;
	rect.x = SCREEN_BOTTOM_W - GRID_MARGIN_X - rect.w;
	rect.y = SCREEN_H - GRID_BOTTOM_BAR + 4.0f;
	return rect;
}

/** Bouton explicite affiché quand aucune page n'est encore disponible. */
static Rect waiting_settings_rect(void)
{
	Rect rect;
	rect.w = 148.0f;
	rect.h = 28.0f;
	rect.x = (SCREEN_BOTTOM_W - rect.w) * 0.5f;
	rect.y = SCREEN_H - rect.h - 4.0f;
	return rect;
}

static Rect tab_rect(int index, int page_count)
{
	const int count = (page_count < 1) ? 1 : page_count;

	/* La zone des onglets s'arrête avant le bouton des réglages. */
	const float area_w = SCREEN_BOTTOM_W - GRID_MARGIN_X * 2.0f -
	                     SETTINGS_TAB_W - 6.0f;
	const float gap = 3.0f;
	const float tab_w = (area_w - gap * (float)(count - 1)) / (float)count;

	Rect rect;
	rect.x = GRID_MARGIN_X + (float)index * (tab_w + gap);
	rect.y = SCREEN_H - GRID_BOTTOM_BAR + 4.0f;
	rect.w = tab_w;
	rect.h = TAB_H - 4.0f;
	return rect;
}

int ui_tab_at(float x, float y, int page_count)
{
	if (page_count <= 0) {
		return -1;
	}

	/* Bande tactile élargie vers le bas pour rester confortable au doigt. */
	for (int i = 0; i < page_count; i++) {
		const Rect rect = tab_rect(i, page_count);
		if (x >= rect.x && x < rect.x + rect.w && y >= rect.y - 4.0f &&
		    y < SCREEN_H) {
			return i;
		}
	}
	return -1;
}

bool ui_settings_at(float x, float y)
{
	const Rect rect = settings_rect();
	return x >= rect.x - 2.0f && x < rect.x + rect.w + 2.0f &&
	       y >= rect.y - 4.0f && y < SCREEN_H;
}

bool ui_waiting_settings_at(float x, float y)
{
	const Rect rect = waiting_settings_rect();
	return x >= rect.x - 3.0f && x < rect.x + rect.w + 3.0f &&
	       y >= rect.y - 3.0f && y < rect.y + rect.h + 3.0f;
}

/** Retour compact d'une action, sans recouvrir son libellé. */
static void draw_action_feedback(ActionFeedbackState state, float cx, float cy,
                                 float uptime)
{
	if (state == ACTION_FEEDBACK_NONE) {
		return;
	}

	draw_circle(cx, cy, 7.5f, Z_OVERLAY, theme_alpha(COL_BG, 0xE8));

	if (state == ACTION_FEEDBACK_PENDING) {
		draw_ring(cx, cy, 5.4f, 1.2f, Z_OVERLAY,
		          theme_alpha(COL_ACCENT, 0x42));
		draw_arc(cx, cy, 5.4f, 1.8f, fmodf(uptime * 1.4f, 1.0f), 0.30f,
		         Z_OVERLAY, COL_ACCENT);
		return;
	}

	const u32 fill =
	    state == ACTION_FEEDBACK_SUCCESS ? COL_OK : COL_ERR;
	draw_circle(cx, cy, 5.7f, Z_OVERLAY, fill);

	if (state == ACTION_FEEDBACK_SUCCESS) {
		draw_line(cx - 3.0f, cy, cx - 0.8f, cy + 2.3f, 1.4f,
		          Z_OVERLAY, COL_BG);
		draw_line(cx - 0.8f, cy + 2.3f, cx + 3.4f, cy - 2.7f, 1.4f,
		          Z_OVERLAY, COL_BG);
	} else {
		draw_line(cx - 2.4f, cy - 2.4f, cx + 2.4f, cy + 2.4f, 1.4f,
		          Z_OVERLAY, COL_WHITE);
		draw_line(cx - 2.4f, cy + 2.4f, cx + 2.4f, cy - 2.4f, 1.4f,
		          Z_OVERLAY, COL_WHITE);
	}
}

/** Dessine un bouton de la grille. */
static void draw_button(const App *app, const Button *button, int slot)
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

	const bool active = model_toggle_active(&app->state, button->toggle);
	const Page *page = app_current_page(app);
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

	const u32 accent = button->color;

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

	text_draw_clipped(cx, label_y, Z_OVERLAY, TEXT_BODY,
	                  active ? COL_WHITE : COL_TEXT, ALIGN_CENTER, w - 8.0f,
	                  showing_hold ? button->hold_label : button->label);

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

/* --- Présentation en liste ------------------------------------------------ */

/** Colonnes, hauteur de rangée et espacement de la liste. */
#define LIST_COLS 2
#define LIST_ROW_H 38.0f
#define LIST_GAP 4.0f
#define LIST_MARGIN 10.0f

/** Nombre de rangées entièrement visibles. */
static int list_visible_rows(void)
{
	const float zone = SCREEN_H - GRID_TOP - GRID_BOTTOM_BAR;
	return (int)((zone + LIST_GAP) / (LIST_ROW_H + LIST_GAP));
}

/** Nombre total de rangées nécessaires pour `count` éléments. */
static int list_total_rows(int count)
{
	return (count + LIST_COLS - 1) / LIST_COLS;
}

/** Emplacement d'un élément, en tenant compte du défilement courant. */
static Rect list_item_rect(int index, float scroll)
{
	const int row = index / LIST_COLS;
	const int col = index % LIST_COLS;

	const float area_w = SCREEN_BOTTOM_W - LIST_MARGIN * 2.0f;
	const float col_w = (area_w - LIST_GAP * (LIST_COLS - 1)) / LIST_COLS;

	Rect rect;
	rect.x = LIST_MARGIN + (float)col * (col_w + LIST_GAP);
	rect.y = GRID_TOP + ((float)row - scroll) * (LIST_ROW_H + LIST_GAP);
	rect.w = col_w;
	rect.h = LIST_ROW_H;
	return rect;
}

int ui_list_at(const App *app, float x, float y)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_LIST) {
		return -1;
	}

	/*
	 * La zone utile s'arrête avant la barre d'onglets. Un élément en cours de
	 * défilement peut déborder par le bas : sans cette limite, il resterait
	 * cliquable par-dessus les onglets, qui deviendraient inatteignables.
	 */
	const float zone_top = GRID_TOP;
	const float zone_bottom = SCREEN_H - GRID_BOTTOM_BAR;

	if (y < zone_top || y >= zone_bottom) {
		return -1;
	}

	for (int i = 0; i < page->entry_count; i++) {
		const Rect rect = list_item_rect(i, app->list_scroll);

		/* On ignore ce qui est entièrement hors de la zone visible. */
		if (rect.y + rect.h < zone_top || rect.y > zone_bottom) {
			continue;
		}

		if (x >= rect.x && x < rect.x + rect.w && y >= rect.y &&
		    y < rect.y + rect.h) {
			return i;
		}
	}
	return -1;
}

int ui_list_columns(void)
{
	return LIST_COLS;
}

int ui_list_rows(void)
{
	return list_visible_rows();
}

float ui_list_max_scroll(const App *app)
{
	const Page *page = app_current_page(app);
	if (page == NULL || page->layout != LAYOUT_LIST) {
		return 0.0f;
	}

	const int rows = list_total_rows(page->entry_count);
	const int visible = list_visible_rows();
	const int extra = rows - visible;

	return (extra > 0) ? (float)extra : 0.0f;
}

/** Dessine un élément de liste. */
static void draw_list_item(const App *app, const ListEntry *entry, int index)
{
	const Rect rect = list_item_rect(index, app->list_scroll);

	/* Rien à faire si l'élément est hors de la zone visible. */
	if (rect.y + rect.h < GRID_TOP - 2.0f ||
	    rect.y > SCREEN_H - GRID_BOTTOM_BAR + 2.0f) {
		return;
	}

	const bool focused = (index == app->list_focus);
	const Page *page = app_current_page(app);
	const ActionFeedbackState feedback =
	    page != NULL ? app_action_feedback(app, page->id, entry->id)
	                 : ACTION_FEEDBACK_NONE;
	const float radius = 8.0f;

	/*
	 * L'élément actif est mis en évidence par son fond et un liseré coloré :
	 * on repère ainsi immédiatement la fenêtre au premier plan.
	 */
	u32 top;
	u32 bottom;
	if (entry->active) {
		top = theme_mix(COL_SURFACE_HI, entry->color, 0.38f);
		bottom = theme_mix(COL_SURFACE_LO, entry->color, 0.20f);
	} else if (focused) {
		top = COL_SURFACE_HI;
		bottom = COL_SURFACE;
	} else {
		top = COL_SURFACE;
		bottom = COL_SURFACE_LO;
	}
	if (feedback == ACTION_FEEDBACK_PENDING) {
		top = theme_mix(top, COL_ACCENT, 0.08f);
	} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
		top = theme_mix(top, COL_OK, 0.12f);
	} else if (feedback == ACTION_FEEDBACK_ERROR) {
		top = theme_mix(top, COL_ERR, 0.12f);
	}

	draw_round_rect_vgrad(rect.x, rect.y, rect.w, rect.h, radius, Z_CARD, top,
	                      bottom);

	if (entry->active || focused || feedback != ACTION_FEEDBACK_NONE) {
		u32 outline_color = theme_alpha(
		    entry->color, entry->active ? 0xDD : 0x77);
		float outline = entry->active ? 1.4f : 1.0f;
		if (feedback == ACTION_FEEDBACK_PENDING) {
			outline_color = theme_alpha(COL_ACCENT, 0xD0);
			outline = 1.4f;
		} else if (feedback == ACTION_FEEDBACK_SUCCESS) {
			outline_color = COL_OK;
			outline = 1.6f;
		} else if (feedback == ACTION_FEEDBACK_ERROR) {
			outline_color = COL_ERR;
			outline = 1.6f;
		}
		draw_round_rect_outline(rect.x, rect.y, rect.w, rect.h, radius,
		                        outline, Z_CONTENT, outline_color);
	}

	/* Bandeau vertical coloré : repère discret, aligné à gauche. */
	if (entry->active) {
		draw_round_rect(rect.x + 3.0f, rect.y + 7.0f, 2.5f, rect.h - 14.0f,
		                1.25f, Z_CONTENT, entry->color);
	}

	const float icon_cx = rect.x + 19.0f;
	const float middle = rect.y + rect.h * 0.5f;

	icons_draw(entry->icon, icon_cx, middle, 17.0f, Z_OVERLAY,
	           entry->active ? COL_WHITE
	                         : theme_mix(entry->color, COL_WHITE, 0.35f));

	/* Deux lignes : l'application, puis le détail qui la précise. */
	const float text_x = rect.x + 32.0f;
	const float text_w = rect.w - 48.0f;

	const bool has_detail = entry->detail[0] != '\0';
	const float label_y =
	    has_detail ? rect.y + 6.0f
	               : middle - TEXT_LINE_PX(TEXT_SMALL) * 0.5f;

	text_draw_clipped(text_x, label_y, Z_OVERLAY, TEXT_SMALL,
	                  entry->active ? COL_WHITE : COL_TEXT, ALIGN_LEFT, text_w,
	                  entry->label);

	if (has_detail) {
		text_draw_clipped(text_x, rect.y + 21.0f, Z_OVERLAY, TEXT_MICRO,
		                  entry->active ? theme_alpha(COL_WHITE, 0xBB)
		                                : COL_TEXT_FAINT,
		                  ALIGN_LEFT, text_w, entry->detail);
	}

	draw_action_feedback(feedback, rect.x + rect.w - 14.0f, middle,
	                     app->uptime);
}

/** Barre de position, à droite, indiquant l'étendue du défilement. */
static void draw_list_scrollbar(const App *app, int count)
{
	const int rows = list_total_rows(count);
	const int visible = list_visible_rows();

	if (rows <= visible) {
		return; /* tout est visible, la barre serait inutile */
	}

	const float track_x = SCREEN_BOTTOM_W - 5.0f;
	const float track_y = GRID_TOP + 2.0f;
	const float track_h = SCREEN_H - GRID_BOTTOM_BAR - GRID_TOP - 4.0f;

	draw_round_rect(track_x, track_y, 3.0f, track_h, 1.5f, Z_CARD,
	                theme_alpha(COL_SURFACE_HI, 0x99));

	const float ratio = (float)visible / (float)rows;
	const float thumb_h = track_h * ratio;
	const float max_scroll = (float)(rows - visible);
	const float progress =
	    (max_scroll > 0.0f) ? app->list_scroll / max_scroll : 0.0f;

	draw_round_rect(track_x, track_y + (track_h - thumb_h) * progress, 3.0f,
	                thumb_h, 1.5f, Z_CONTENT, theme_alpha(COL_ACCENT, 0xCC));
}

/** Dessine la page en mode liste. */
static void draw_list(const App *app, const Page *page)
{
	for (int i = 0; i < page->entry_count; i++) {
		if (page->entries[i].used) {
			draw_list_item(app, &page->entries[i], i);
		}
	}

	draw_list_scrollbar(app, page->entry_count);

	if (page->entry_count == 0) {
		text_draw(SCREEN_BOTTOM_W * 0.5f, SCREEN_H * 0.45f, Z_CONTENT,
		          TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER, tr(STR_NO_APPS));
	}
}

static void draw_title_bar(const App *app)
{
	const Page *page = app_current_page(app);

	draw_rect_vgrad(0.0f, 0.0f, SCREEN_BOTTOM_W, GRID_TOP - 6.0f, Z_CARD,
	                theme_alpha(COL_SURFACE, 0xE6),
	                theme_alpha(COL_SURFACE_LO, 0xB0));

	/*
	 * Pastille de couleur devant le titre : reprend l'accent de la page
	 * courante et sert de repère visuel lors des changements de page.
	 */
	const u32 accent = (app->link == LINK_ONLINE) ? COL_ACCENT : COL_ERR;
	draw_round_rect(GRID_MARGIN_X, 11.0f, 3.0f, 13.0f, 1.5f, Z_CONTENT, accent);

	const char *title = (page != NULL) ? page->title : "Deck3DS";
	text_draw_clipped(GRID_MARGIN_X + 9.0f, 8.0f, Z_CONTENT, TEXT_LARGE, COL_TEXT,
	                  ALIGN_LEFT, 190.0f, title);

	/* Compteur de pages, à droite. */
	if (app->config.page_count > 1) {
		/*
		 * Les valeurs sont bornées par MAX_PAGES, mais le compilateur ne peut
		 * pas le déduire : on les restreint explicitement pour garantir que le
		 * formatage ne soit jamais tronqué.
		 */
		const unsigned current =
		    (unsigned)(app->current_page + 1) % (MAX_PAGES + 1);
		const unsigned total = (unsigned)app->config.page_count % (MAX_PAGES + 1);

		char counter[16];
		snprintf(counter, sizeof(counter), "%u / %u", current, total);
		text_draw(SCREEN_BOTTOM_W - GRID_MARGIN_X, 12.0f, Z_CONTENT, TEXT_SMALL,
		          COL_TEXT_FAINT, ALIGN_RIGHT, counter);
	}

	/*
	 * Trait de séparation en dégradé : plus lumineux au centre, il structure
	 * l'écran sans le cloisonner brutalement.
	 */
	const float y = GRID_TOP - 7.0f;
	const u32 edge = theme_alpha(accent, 0x00);
	const u32 middle = theme_alpha(accent, 0x88);
	C2D_DrawRectangle(0.0f, y, Z_CONTENT, SCREEN_BOTTOM_W * 0.5f, 1.0f, edge,
	                  middle, edge, middle);
	C2D_DrawRectangle(SCREEN_BOTTOM_W * 0.5f, y, Z_CONTENT,
	                  SCREEN_BOTTOM_W * 0.5f, 1.0f, middle, edge, middle, edge);
}

static void draw_tabs(const App *app)
{
	const int count = app->config.page_count;
	if (count <= 0) {
		return;
	}

	for (int i = 0; i < count; i++) {
		const Rect rect = tab_rect(i, count);
		const bool current = (i == app->current_page);
		const Page *page = model_page_at(&app->config, i);

		const float radius = rect.h * 0.5f;

		if (current) {
			/*
			 * Onglet actif : fond plus dense et contour net, pour qu'il se
			 * distingue immédiatement des autres.
			 */
			draw_round_rect_vgrad(rect.x, rect.y, rect.w, rect.h, radius, Z_CARD,
			                      theme_alpha(COL_ACCENT, 0x4A),
			                      theme_alpha(COL_ACCENT, 0x22));
			draw_round_rect_outline(rect.x, rect.y, rect.w, rect.h, radius, 1.2f,
			                        Z_CONTENT, theme_alpha(COL_ACCENT, 0xBB));
		} else {
			draw_round_rect(rect.x, rect.y, rect.w, rect.h, radius, Z_CARD,
			                theme_alpha(COL_SURFACE, 0x99));
		}

		const char *label = (page != NULL) ? page->title : "";
		const u32 fg = current ? COL_WHITE : COL_TEXT_DIM;

		/*
		 * Une icône plutôt qu'un numéro.
		 *
		 * Au-delà de cinq pages, un onglet mesure moins de cinquante pixels :
		 * le titre n'y tient plus, et un numéro n'apprend rien sur le contenu
		 * de la page. Une icône reste lisible et reconnaissable à cette taille.
		 * Quand la place le permet, les deux sont affichés ensemble.
		 */
		const IconId icon = (page != NULL) ? page->icon : ICON_PAGE;
		const float centre_y = rect.y + rect.h * 0.5f;

		if (rect.w >= 74.0f && label[0] != '\0') {
			icons_draw(icon, rect.x + 15.0f, centre_y, 15.0f, Z_OVERLAY, fg);
			text_draw_clipped(
			    rect.x + 26.0f,
			    rect.y + (rect.h - TEXT_LINE_PX(TEXT_MICRO)) * 0.5f, Z_OVERLAY,
			    TEXT_MICRO, fg, ALIGN_LEFT, rect.w - 32.0f, label);
		} else {
			/*
			 * L'icône s'adapte à la largeur disponible : avec le nombre maximal
			 * de pages, un onglet descend sous vingt pixels et une icône de
			 * taille fixe dépasserait de son cadre.
			 */
			float icon_size = 17.0f;
			if (rect.w < 24.0f) {
				icon_size = rect.w * 0.72f;
			}
			icons_draw(icon, rect.x + rect.w * 0.5f, centre_y, icon_size,
			           Z_OVERLAY, fg);
		}
	}

	/* Bouton des réglages, à place fixe pour rester toujours repérable. */
	const Rect settings = settings_rect();
	const float settings_radius = settings.h * 0.5f;

	draw_round_rect(settings.x, settings.y, settings.w, settings.h,
	                settings_radius, Z_CARD, theme_alpha(COL_SURFACE, 0xBB));
	draw_round_rect_outline(settings.x, settings.y, settings.w, settings.h,
	                        settings_radius, 1.0f, Z_CONTENT,
	                        theme_alpha(COL_BORDER, 0x99));
	icons_draw(ICON_GEAR, settings.x + settings.w * 0.5f,
	           settings.y + settings.h * 0.5f, 16.0f, Z_OVERLAY, COL_TEXT_DIM);
}

/** Écran affiché tant qu'aucune configuration n'est disponible. */
static void draw_waiting(const App *app)
{
	const float cx = SCREEN_BOTTOM_W * 0.5f;

	/* Grille fantôme : montre la disposition à venir. */
	for (int slot = 0; slot < GRID_SLOTS; slot++) {
		const Rect rect = slot_rect(slot);

		/* Balayage lumineux, indique une attente active. */
		const float phase = app->uptime * 1.6f - (float)slot * 0.25f;
		float pulse = phase - (float)((int)(phase / 2.0f)) * 2.0f;
		if (pulse > 1.0f) {
			pulse = 2.0f - pulse;
		}
		if (pulse < 0.0f) {
			pulse = 0.0f;
		}

		const u8 alpha = (u8)(0x28 + pulse * 0x30);
		draw_round_rect(rect.x, rect.y, rect.w, rect.h, 9.0f, Z_CARD,
		                theme_alpha(COL_SURFACE, alpha));
		draw_round_rect_outline(rect.x, rect.y, rect.w, rect.h, 9.0f, 1.0f,
		                       Z_CONTENT, theme_alpha(COL_BORDER, 0x77));
	}

	text_draw(cx, 12.0f, Z_OVERLAY, TEXT_BODY, COL_TEXT_DIM, ALIGN_CENTER,
	          app->link == LINK_ONLINE ? tr(STR_RECEIVING_CONFIG)
	                                   : tr(STR_WAITING_PC));

	/*
	 * Pendant une recherche ou une connexion impossible, l'utilisateur doit
	 * pouvoir corriger l'adresse immédiatement. Le bouton est volontairement
	 * large et libellé : une icône seule serait trop discrète sur cet écran.
	 */
	const Rect settings = waiting_settings_rect();
	const float radius = settings.h * 0.5f;
	draw_round_rect(settings.x, settings.y, settings.w, settings.h, radius,
	                Z_CARD, theme_alpha(COL_SURFACE_HI, 0xE8));
	draw_round_rect_outline(settings.x, settings.y, settings.w, settings.h,
	                        radius, 1.0f, Z_CONTENT,
	                        theme_alpha(COL_ACCENT, 0xCC));
	icons_draw(ICON_GEAR, settings.x + 19.0f,
	           settings.y + settings.h * 0.5f, 15.0f, Z_OVERLAY, COL_ACCENT);
	text_draw_clipped(settings.x + 36.0f, settings.y + 7.0f, Z_OVERLAY,
	                  TEXT_SMALL, COL_TEXT, ALIGN_LEFT, settings.w - 44.0f,
	                  tr(STR_SETTINGS));
}

/**
 * Écran tactile en veille.
 *
 * La grille n'a plus de sens : en veille, le moindre contact réveille
 * l'application, aucun bouton n'est donc actionnable. Afficher des commandes
 * inertes serait trompeur, et le rétroéclairage serait dépensé pour rien.
 *
 * L'écran devient donc un panneau d'information sur fond noir : heure, date,
 * dernières notifications et état de la console.
 */
static void draw_standby(const App *app)
{
	/* Noir franc plutôt qu'assombri : l'économie d'énergie est réelle. */
	draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_BG,
	          C2D_Color32(0x00, 0x00, 0x00, 0xFF));

	const float cx = SCREEN_BOTTOM_W * 0.5f;

	/*
	 * Liseré d'alerte : il pulse brièvement à l'arrivée d'une notification, ce
	 * qui se remarque du coin de l'œil sans exiger de lire l'écran.
	 */
	if (app->alert_glow > 0.01f) {
		const float pulse = 0.45f + 0.55f * (0.5f + 0.5f * sinf(app->uptime * 5.0f));
		const u8 alpha = (u8)(app->alert_glow * pulse * 0xCC);
		const u32 glow = theme_alpha(COL_WARN, alpha);

		draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, 2.0f, Z_CONTENT, glow);
		draw_rect(0.0f, SCREEN_H - 2.0f, SCREEN_BOTTOM_W, 2.0f, Z_CONTENT, glow);
		draw_rect(0.0f, 0.0f, 2.0f, SCREEN_H, Z_CONTENT, glow);
		draw_rect(SCREEN_BOTTOM_W - 2.0f, 0.0f, 2.0f, SCREEN_H, Z_CONTENT,
		          glow);
	}

	/* Heure en grand, information la plus recherchée sur un objet posé. */
	const char *clock = (app->state.time[0] != '\0' && app->link == LINK_ONLINE)
	                        ? app->state.time
	                        : app->local_time;

	text_draw(cx, 24.0f, Z_CONTENT, TEXT_HUGE, COL_TEXT, ALIGN_CENTER, clock);

	if (app->local_date[0] != '\0') {
		text_draw_clipped(cx, 24.0f + TEXT_LINE_PX(TEXT_HUGE) + 2.0f, Z_CONTENT,
		                  TEXT_SMALL, COL_TEXT_FAINT, ALIGN_CENTER,
		                  SCREEN_BOTTOM_W - 40.0f, app->local_date);
	}

	draw_rect(30.0f, 88.0f, SCREEN_BOTTOM_W - 60.0f, 1.0f, Z_CONTENT,
	          theme_alpha(COL_BORDER, 0x88));

	/* Deux dernières notifications, avec leur ancienneté. */
	const int shown = (app->state.notification_count < 2)
	                      ? app->state.notification_count
	                      : 2;

	if (shown == 0) {
		text_draw(cx, 118.0f, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_CENTER, tr(STR_NO_NOTIFICATIONS));
	}

	for (int i = 0; i < shown; i++) {
		const float y = 100.0f + (float)i * 40.0f;
		const u32 tint = (i == 0) ? COL_WARN : COL_TEXT_FAINT;

		icons_draw(app->state.notifications[i].icon, 42.0f, y + 12.0f, 14.0f,
		           Z_CONTENT, tint);

		char age[12];
		const int seconds = app->state.notifications[i].age;
		if (seconds < 60) {
			snprintf(age, sizeof(age), "%ds", seconds % 100);
		} else if (seconds < 3600) {
			snprintf(age, sizeof(age), "%dmin", (seconds / 60) % 100);
		} else {
			snprintf(age, sizeof(age), "%dh", (seconds / 3600) % 100);
		}

		text_draw(SCREEN_BOTTOM_W - 30.0f, y, Z_CONTENT, TEXT_MICRO,
		          COL_TEXT_FAINT, ALIGN_RIGHT, age);

		text_draw_clipped(56.0f, y, Z_CONTENT, TEXT_MICRO, tint, ALIGN_LEFT,
		                  SCREEN_BOTTOM_W - 110.0f,
		                  app->state.notifications[i].app);

		text_draw_clipped(56.0f, y + 14.0f, Z_CONTENT, TEXT_SMALL,
		                  (i == 0) ? COL_TEXT : COL_TEXT_DIM, ALIGN_LEFT,
		                  SCREEN_BOTTOM_W - 86.0f,
		                  app->state.notifications[i].title);
	}

	/* Bandeau d'état, en bas. */
	const float info_y = SCREEN_H - 44.0f;
	draw_rect(30.0f, info_y - 10.0f, SCREEN_BOTTOM_W - 60.0f, 1.0f, Z_CONTENT,
	          theme_alpha(COL_BORDER, 0x88));

	/*
	 * Bandeau d'état : intitulé à gauche, jauge et volume à droite.
	 *
	 * La console rapporte un niveau de zéro à cinq, non un pourcentage : la
	 * jauge à segments est donc plus honnête qu'une valeur chiffrée, qui
	 * suggérerait une précision inexistante.
	 */
	if (app->battery_level >= 0) {
		text_draw(34.0f, info_y, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT,
		          ALIGN_LEFT, tr(STR_BATTERY));

		/* La jauge est calée à droite, le volume juste après. */
		const float gauge_w = 5.0f * 7.0f - 2.0f;
		const float charge_w = app->battery_charging ? 16.0f : 0.0f;

		float right = SCREEN_BOTTOM_W - 34.0f;

		if (app->state.volume >= 0) {
			char volume[16];
			snprintf(volume, sizeof(volume), "%u %%",
			         (unsigned)app->state.volume % 101u);

			text_draw(right, info_y, Z_CONTENT, TEXT_MICRO,
			          app->state.muted ? COL_ERR : COL_TEXT_DIM, ALIGN_RIGHT,
			          volume);
			right -= text_width(volume, TEXT_MICRO) + 14.0f;
		}

		const float bx = right - gauge_w - charge_w;
		const float by = info_y + 2.0f;

		if (app->battery_charging) {
			icons_draw(ICON_POWER, right - 8.0f, by + 5.0f, 11.0f, Z_CONTENT,
			           COL_ACCENT);
		}

		for (int i = 0; i < 5; i++) {
			const bool filled = i < app->battery_level;
			draw_round_rect(bx + (float)i * 7.0f, by, 5.0f, 10.0f, 1.5f,
			                Z_CONTENT,
			                filled ? (app->battery_level <= 1 ? COL_ERR
			                                                  : COL_OK)
			                       : theme_alpha(COL_SURFACE_HI, 0xCC));
		}
	} else if (app->state.volume >= 0) {
		/* Sans niveau de batterie, le volume reste seul à droite. */
		char volume[16];
		snprintf(volume, sizeof(volume), "%u %%",
		         (unsigned)app->state.volume % 101u);
		text_draw(SCREEN_BOTTOM_W - 34.0f, info_y, Z_CONTENT, TEXT_MICRO,
		          app->state.muted ? COL_ERR : COL_TEXT_DIM, ALIGN_RIGHT,
		          volume);
	}

	/* Sans cette mention, on pourrait croire l'application figée. */
	text_draw(cx, SCREEN_H - 18.0f, Z_CONTENT, TEXT_MICRO,
	          theme_alpha(COL_TEXT_FAINT, 0x99), ALIGN_CENTER,
	          tr(STR_TOUCH_TO_WAKE));
}

void ui_draw_bottom(const App *app)
{
	/*
	 * En veille, l'écran tactile devient un panneau d'information : aucun
	 * bouton n'est actionnable puisque le moindre contact réveille
	 * l'application.
	 */
	if (app->frame_mode && app->frame_from_idle) {
		draw_standby(app);
		return;
	}

	const u32 top = app->dimmed ? C2D_Color32(0x06, 0x07, 0x0B, 0xFF) : COL_BG_ALT;
	const u32 bottom = app->dimmed ? C2D_Color32(0x03, 0x04, 0x07, 0xFF) : COL_BG;
	draw_rect_vgrad(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_BG, top, bottom);

	if (!app->config_received) {
		draw_waiting(app);
		return;
	}

	draw_title_bar(app);

	const Page *page = app_current_page(app);
	if (page != NULL) {
		if (page->layout == LAYOUT_LIST) {
			draw_list(app, page);
		} else {
			for (int slot = 0; slot < MAX_BUTTONS; slot++) {
				draw_button(app, &page->buttons[slot], slot);
			}
		}
	}

	draw_tabs(app);

	/*
	 * Voile d'assombrissement en veille. L'écran reste lisible mais cesse
	 * d'attirer l'attention, et l'usure de la dalle est limitée.
	 */
	if (app->dimmed) {
		draw_rect(0.0f, 0.0f, SCREEN_BOTTOM_W, SCREEN_H, Z_OVERLAY,
		          C2D_Color32(0x00, 0x00, 0x00, 0x66));
	}
}
