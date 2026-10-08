#pragma once
#include "json.h"
#include "model.h"
void stream_chat_parse(const JsonDoc *doc, const JsonToken *root, PcState *state);
