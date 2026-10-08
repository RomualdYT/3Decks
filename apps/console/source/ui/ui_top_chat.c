#include "ui_top_chat.h"
#include "draw.h"
#include "icons.h"
#include "chat_badges.h"
#include "i18n.h"
#include "text.h"
#include "theme.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
	char id[65];
	bool compact;
	char lines[2][257];
	int count;
} MessageLayout;
static MessageLayout s_layouts[MAX_CHAT_MESSAGES];

static const MessageLayout *layout(const ChatMessage *message, int index, bool compact)
{
	MessageLayout *item = &s_layouts[index];
	if (!strcmp(item->id, message->id) && item->compact == compact) return item;
	memset(item, 0, sizeof(*item));
	snprintf(item->id, sizeof(item->id), "%s", message->id);
	item->compact = compact;
	const float scale = compact ? TEXT_SMALL : TEXT_BODY;
	const char *input = message->text;
	for (int line = 0; line < 2 && *input; line++) {
		const char *begin = input;
		size_t used = 0, space = 0;
		while (input[used] && used < 252) {
			const unsigned char c = (unsigned char)input[used];
			const size_t bytes = c < 0x80 ? 1 : c < 0xE0 ? 2 : c < 0xF0 ? 3 : 4;
			if (used + bytes > strlen(input)) break;
			memcpy(item->lines[line] + used, input + used, bytes);
			item->lines[line][used + bytes] = '\0';
			if (text_width(item->lines[line], scale) > 354) { item->lines[line][used] = '\0'; break; }
			if (input[used] == ' ') space = used;
			used += bytes;
		}
		if (input[used] && space > 0) { used = space; item->lines[line][used] = '\0'; }
		input += used;
		while (*input == ' ') input++;
		item->count++;
		if (line == 1 && *input) {
			// Clipping adds an ellipsis without splitting a UTF-8 glyph.
			snprintf(item->lines[line], sizeof(item->lines[line]), "%s", begin);
		}
	}
	return item;
}

static StringId status(const char *value)
{
	if (!strcmp(value, "connected")) return STR_CHAT_CONNECTED;
	if (!strcmp(value, "disabled")) return STR_CHAT_DISABLED;
	if (!strcmp(value, "connecting") || !strcmp(value, "reconnecting")) return STR_CHAT_CONNECTING;
	if (!strcmp(value, "authorization_required") || !strcmp(value, "awaiting_authorization")) return STR_CHAT_AUTHORIZE;
	if (!strcmp(value, "client_id_required") || !strcmp(value, "channel_required")) return STR_CHAT_SETUP;
	return STR_CHAT_UNAVAILABLE;
}

void ui_top_chat_input(App *app, u32 *down)
{
	if (app_effective_dashboard(app) != DASH_STREAM_CHAT) return;
	if (*down & KEY_X) {
		app->chat_paused = !app->chat_paused;
		app->chat_offset = 0;
		if (app->state.chat_count > 0) snprintf(app->chat_anchor, sizeof(app->chat_anchor), "%s", app->state.chat_messages[app->state.chat_count - 1].id);
	}
	if (*down & KEY_Y) { app->chat_paused = false; app->chat_offset = 0; }
	if (app->chat_paused) {
		if ((*down & KEY_UP) && app->chat_offset < MAX_CHAT_MESSAGES - 1) app->chat_offset++;
		if ((*down & KEY_DOWN) && app->chat_offset > 0) app->chat_offset--;
		*down &= ~(KEY_UP | KEY_DOWN);
	}
}

void ui_top_chat_draw(const App *app)
{
	const PcState *state = &app->state;
	const u32 accent = C2D_Color32(0xBD, 0xA4, 0xFF, 0xFF);
	draw_round_rect(12, 36, 376, 196, 9, Z_CARD, COL_SURFACE);
	icons_draw(ICON_CHAT, 27, 49, 13, Z_CONTENT, accent);
	char title[32];
	snprintf(title, sizeof(title), "%s%s", state->chat_channel[0] ? "#" : "", state->chat_channel[0] ? state->chat_channel : "Twitch");
	text_draw_clipped(39, 42, Z_CONTENT, TEXT_SMALL, accent, ALIGN_LEFT, 180, title);
	text_draw_clipped(378, 43, Z_CONTENT, TEXT_MICRO, !strcmp(state->chat_status, "connected") ? COL_OK : COL_TEXT_DIM, ALIGN_RIGHT, 145, tr(status(state->chat_status)));
	draw_rect(22, 61, 356, 1, Z_CONTENT, theme_alpha(COL_TEXT_DIM, 0x18));
	if (state->chat_count == 0) {
		icons_draw(ICON_CHAT, 200, 110, 26, Z_CONTENT, accent);
		text_draw_clipped(200, 140, Z_CONTENT, TEXT_BODY, COL_TEXT, ALIGN_CENTER, 350, tr(!strcmp(state->chat_status, "connected") ? STR_CHAT_WAITING : status(state->chat_status)));
		text_draw_clipped(200, 164, Z_CONTENT, TEXT_SMALL, COL_TEXT_DIM, ALIGN_CENTER, 350, tr(STR_CHAT_SETTINGS));
	} else {
		int end = state->chat_count - 1;
		if (app->chat_paused) {
			end = 0; /* If the anchor expired, keep the oldest available message. */
			for (int i = 0; i < state->chat_count; i++) if (!strcmp(state->chat_messages[i].id, app->chat_anchor)) { end = i; break; }
			end -= app->chat_offset;
			if (end < 0) end = 0;
		}
		const float scale = state->chat_compact ? TEXT_SMALL : TEXT_BODY;
		const float line_h = TEXT_LINE_PX(scale) + 1;
		float total = 0;
		int start = end;
		for (int i = end; i >= 0; i--) {
			const MessageLayout *item = layout(&state->chat_messages[i], i, state->chat_compact);
			const float height = 15 + item->count * line_h + 5;
			if (total + height > 145) break;
			total += height;
			start = i;
		}
		float y = 65;
		for (int i = start; i <= end; i++) {
			const ChatMessage *message = &state->chat_messages[i];
			const MessageLayout *item = layout(message, i, state->chat_compact);
			unsigned rgb = 0xBDA4FF;
			if (message->color[0] == '#' && strlen(message->color) == 7) rgb = (unsigned)strtoul(message->color + 1, NULL, 16);
			const u32 color = C2D_Color32((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255, 255);
			float author_x = 22;
			if (state->chat_timestamps) { text_draw(22, y, Z_CONTENT, TEXT_MICRO, COL_TEXT_FAINT, ALIGN_LEFT, message->time); author_x += 36; }
			for (int b = 0; b < message->badge_count; b++) {
				if (chat_badges_draw(message->badges[b], author_x, y, 12, Z_CONTENT)) author_x += 15;
			}
			text_draw_clipped(author_x, y, Z_CONTENT, TEXT_MICRO, color, ALIGN_LEFT, 376 - author_x, message->author);
			y += 14;
			for (int line = 0; line < item->count; line++) {
				text_draw_clipped(22, y, Z_CONTENT, scale, COL_TEXT, ALIGN_LEFT, 354, item->lines[line]);
				y += line_h;
			}
			y += 6;
		}
	}
	draw_rect(22, 212, 356, 1, Z_CONTENT, theme_alpha(COL_TEXT_DIM, 0x18));
	text_draw_clipped(22, 218, Z_CONTENT, TEXT_MICRO, COL_TEXT_DIM, ALIGN_LEFT, 354, tr(app->chat_paused ? STR_CHAT_PAUSED : STR_CHAT_CONTROLS));
}
