/* 3Decks — GPL-3.0. Bounded native rendering of extension API v1 cards. */
#include "extension_ui.h"

#include <string.h>

#include "draw.h"
#include "i18n.h"
#include "text.h"

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
