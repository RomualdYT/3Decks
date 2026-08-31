/* 3Decks — GPL-3.0. Bounded native rendering of extension API v1 cards. */
#include "extension_ui.h"

#include <string.h>

#include "draw.h"
#include "i18n.h"
#include "text.h"

void extension_state_parse(const JsonDoc *doc, const JsonToken *root,
                           PcState *state)
{
	const JsonToken *array = json_get(doc, root, "extension_panels");
	if (array && array->type == JSON_ARRAY) {
		state->extension_panel_count = 0;
		for (int i = 0; i < json_size(array) && i < MAX_PAGES; i++) {
			const JsonToken *item = json_at(doc, array, i);
			if (!item || item->type != JSON_OBJECT) continue;
			ExtensionPanel *panel = &state->extension_panels[state->extension_panel_count];
			memset(panel, 0, sizeof(*panel));
			json_get_string(doc, item, "page", panel->page, sizeof(panel->page));
			if (!panel->page[0]) continue;
			json_get_string(doc, item, "title", panel->title, sizeof(panel->title));
			char status[16];
			json_get_string(doc, item, "status", status, sizeof(status));
			panel->status = strcmp(status, "error") == 0 ? 3 :
			                strcmp(status, "warning") == 0 ? 2 :
			                strcmp(status, "ok") == 0 ? 1 : 0;
			const JsonToken *cards = json_get(doc, item, "cards");
			if (cards && cards->type == JSON_ARRAY) {
				for (int c = 0; c < json_size(cards) && c < MAX_EXTENSION_CARDS; c++) {
					const JsonToken *raw = json_at(doc, cards, c);
					if (!raw || raw->type != JSON_OBJECT) continue;
					ExtensionCard *card = &panel->cards[panel->count++];
					json_get_string(doc, raw, "label", card->label, sizeof(card->label));
					json_get_string(doc, raw, "value", card->value, sizeof(card->value));
					json_get_string(doc, raw, "detail", card->detail, sizeof(card->detail));
					card->progress = json_get_int(doc, raw, "progress", -1);
					if (card->progress < 0 || card->progress > 100) card->progress = -1;
				}
			}
			state->extension_panel_count++;
		}
	}
	array = json_get(doc, root, "extension_buttons");
	if (array && array->type == JSON_ARRAY) {
		state->extension_button_count = 0;
		for (int i = 0; i < json_size(array) && i < MAX_EXTENSION_BUTTONS; i++) {
			const JsonToken *raw = json_at(doc, array, i);
			if (!raw || raw->type != JSON_OBJECT) continue;
			ExtensionButtonState *button = &state->extension_buttons[state->extension_button_count++];
			json_get_string(doc, raw, "page", button->page, sizeof(button->page));
			json_get_string(doc, raw, "id", button->id, sizeof(button->id));
			button->active = json_get_bool(doc, raw, "active", false);
			button->available = json_get_bool(doc, raw, "available", false);
		}
	}
}

const ExtensionButtonState *extension_button_state(const PcState *state,
                                                   const char *page,
                                                   const char *button)
{
	for (int i = 0; i < state->extension_button_count; i++) {
		const ExtensionButtonState *entry = &state->extension_buttons[i];
		if (strcmp(entry->page, page) == 0 && strcmp(entry->id, button) == 0)
			return entry;
	}
	return NULL;
}

void extension_dashboard_draw(const App *app)
{
	const Page *page = app_current_page(app);
	const ExtensionPanel *panel = NULL;
	for (int i = 0; page && i < app->state.extension_panel_count; i++) {
		if (strcmp(app->state.extension_panels[i].page, page->id) == 0) {
			panel = &app->state.extension_panels[i];
			break;
		}
	}
	if (!panel) {
		text_draw(200, 105, Z_CONTENT, TEXT_BODY, COL_TEXT_DIM, ALIGN_CENTER,
		          tr(STR_EXTENSION_WAITING));
		return;
	}
	const u32 accent = panel->status == 3 ? COL_ERR : panel->status == 2 ? COL_WARN : COL_ACCENT;
	draw_round_rect(12, 36, 376, 28, 9, Z_CARD, theme_alpha(accent, 0x20));
	draw_circle(25, 50, 3, Z_CONTENT, accent);
	text_draw_clipped(36, 42, Z_CONTENT, TEXT_SMALL, COL_TEXT, ALIGN_LEFT, 338, panel->title);
	for (int i = 0; i < panel->count; i++) {
		const ExtensionCard *card = &panel->cards[i];
		const float x = 12.0f + (i % 2) * 194.0f;
		const float y = 72.0f + (i / 2) * 82.0f;
		draw_round_rect_vgrad(x, y, 182, 74, 9, Z_CARD, COL_SURFACE, COL_SURFACE_LO);
		text_draw_clipped(x + 10, y + 7, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM, ALIGN_LEFT, 162, card->label);
		text_draw_clipped(x + 10, y + 24, Z_CONTENT, TEXT_TITLE, accent, ALIGN_LEFT, 162, card->value);
		text_draw_clipped(x + 10, y + 49, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM, ALIGN_LEFT, 162, card->detail);
		if (card->progress >= 0) draw_progress(x + 10, y + 66, 162, 3, card->progress / 100.0f, Z_CONTENT, COL_SURFACE_HI, accent);
	}
}
