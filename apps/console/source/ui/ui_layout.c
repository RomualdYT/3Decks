#include "ui_bottom_internal.h"

Rect slot_rect(int slot)
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


/**
 * Emplacement du bouton des réglages.
 *
 * Il occupe une place fixe à droite de la barre : toujours accessible, il ne
 * dépend pas du nombre de pages et reste au même endroit quelle que soit la
 * configuration.
 */
Rect settings_rect(void)
{
	Rect rect;
	rect.w = SETTINGS_TAB_W;
	rect.h = TAB_H - 4.0f;
	rect.x = SCREEN_BOTTOM_W - GRID_MARGIN_X - rect.w;
	rect.y = SCREEN_H - GRID_BOTTOM_BAR + 4.0f;
	return rect;
}

/** Bouton explicite affiché quand aucune page n'est encore disponible. */
Rect waiting_settings_rect(void)
{
	Rect rect;
	rect.w = 148.0f;
	rect.h = 28.0f;
	rect.x = (SCREEN_BOTTOM_W - rect.w) * 0.5f;
	rect.y = SCREEN_H - rect.h - 4.0f;
	return rect;
}

/* Geometry is shared by rendering and touch detection. With crowded decks,
 * use icons only rather than shrinking the other pages to fit a title. */
Rect tab_rect(int index, int page_count, int current_page)
{
	const int count = page_count < 1 ? 1 : page_count;
	const float area = SCREEN_BOTTOM_W - GRID_MARGIN_X * 2.0f - SETTINGS_TAB_W - 6.0f;
	const float gap = 3.0f;
	const float inactive = count <= 6 ? 30.0f : (area - gap * (count - 1)) / count;
	float active = count <= 6 ? area - (inactive + gap) * (count - 1) : inactive;
	if (active > 88.0f) active = 88.0f;
	const float width = active + (inactive + gap) * (count - 1);
	float x = GRID_MARGIN_X + (area - width) * 0.5f;
	for (int i = 0; i < index; i++) x += (i == current_page ? active : inactive) + gap;
	return (Rect){x, SCREEN_H - GRID_BOTTOM_BAR + 4.0f,
	              index == current_page ? active : inactive, TAB_H - 4.0f};
}

int ui_tab_at(float x, float y, int page_count, int current_page)
{
	for (int i = 0; i < page_count; i++) {
		const Rect rect = tab_rect(i, page_count, current_page);
		if (x >= rect.x && x < rect.x + rect.w && y >= rect.y - 4.0f && y < SCREEN_H) return i;
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

/** Nombre de rangées entièrement visibles. */
int list_visible_rows(void)
{
	const float zone = SCREEN_H - GRID_TOP - GRID_BOTTOM_BAR;
	return (int)((zone + LIST_GAP) / (LIST_ROW_H + LIST_GAP));
}

/** Nombre total de rangées nécessaires pour `count` éléments. */
int list_total_rows(int count)
{
	return (count + LIST_COLS - 1) / LIST_COLS;
}

/** Emplacement d'un élément, en tenant compte du défilement courant. */
Rect list_item_rect(int index, float scroll)
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
