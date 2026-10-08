#include "stream_chat.h"
#include <string.h>

void stream_chat_parse(const JsonDoc *doc, const JsonToken *root, PcState *state)
{
	const JsonToken *chat = json_get(doc, root, "stream_chat");
	if (!chat || chat->type != JSON_OBJECT) return;
	json_get_string(doc, chat, "status", state->chat_status, sizeof(state->chat_status));
	json_get_string(doc, chat, "channel", state->chat_channel, sizeof(state->chat_channel));
	state->chat_compact = json_get_bool(doc, chat, "compact", false);
	state->chat_timestamps = json_get_bool(doc, chat, "timestamps", false);
	state->chat_count = 0;
	const JsonToken *messages = json_get(doc, chat, "messages");
	if (!messages || messages->type != JSON_ARRAY) return;
	for (int i = 0; i < json_size(messages) && state->chat_count < MAX_CHAT_MESSAGES; i++) {
		const JsonToken *raw = json_at(doc, messages, i);
		if (!raw || raw->type != JSON_OBJECT) continue;
		ChatMessage *message = &state->chat_messages[state->chat_count];
		memset(message, 0, sizeof(*message));
		json_get_string(doc, raw, "id", message->id, sizeof(message->id));
		json_get_string(doc, raw, "author", message->author, sizeof(message->author));
		json_get_string(doc, raw, "text", message->text, sizeof(message->text));
		json_get_string(doc, raw, "color", message->color, sizeof(message->color));
		json_get_string(doc, raw, "time", message->time, sizeof(message->time));
		const JsonToken *badges = json_get(doc, raw, "badges");
		if (badges && badges->type == JSON_ARRAY) {
			for (int b = 0; b < json_size(badges) && message->badge_count < 3; b++) {
				const JsonToken *badge = json_at(doc, badges, b);
				if (!badge || badge->type != JSON_OBJECT) continue;
				const int token = json_get_int(doc, badge, "token", 0);
				if (token > 0) message->badges[message->badge_count++] = (u32)token;
			}
		}
		if (message->id[0] && message->text[0]) state->chat_count++;
	}
}
