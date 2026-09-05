#pragma once
#include "json.h"
#include "model.h"
void extension_state_parse(const JsonDoc *doc, const JsonToken *root, PcState *state);
