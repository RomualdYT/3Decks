#include "extension_state.h"
#include <string.h>
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
