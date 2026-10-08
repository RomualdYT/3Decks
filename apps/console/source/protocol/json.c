/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

#include "json.h"

#include <string.h>
#include <limits.h>
#include <float.h>
#include <math.h>

/*
 * Analyseur descendant simple. La structure est celle d'un tableau plat de
 * tokens : chaque token connaît son parent, ce qui suffit pour naviguer sans
 * pointeurs ni allocation. Les enfants d'un token occupent nécessairement des
 * indices supérieurs au sien, ce qui rend le parcours linéaire.
 */

typedef struct {
	JsonDoc *doc;
	size_t pos;
	int depth;
} Parser;

static bool parse_value(Parser *p, int parent);

static JsonToken *alloc_token(Parser *p, int parent)
{
	if (p->doc->count >= JSON_MAX_TOKENS) {
		return NULL;
	}

	JsonToken *token = &p->doc->tokens[p->doc->count++];
	token->type = JSON_UNDEFINED;
	token->start = 0;
	token->end = 0;
	token->size = 0;
	token->parent = parent;
	return token;
}

static bool at_end(const Parser *p)
{
	return p->pos >= p->doc->length;
}

static char peek(const Parser *p)
{
	return at_end(p) ? '\0' : p->doc->buffer[p->pos];
}

static void skip_whitespace(Parser *p)
{
	while (!at_end(p)) {
		const char c = p->doc->buffer[p->pos];
		if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
			p->pos++;
		} else {
			break;
		}
	}
}

static bool parse_string(Parser *p, int parent)
{
	/* On entre en pointant sur le guillemet ouvrant. */
	JsonToken *token = alloc_token(p, parent);
	if (token == NULL) {
		return false;
	}

	p->pos++; /* guillemet ouvrant */
	token->type = JSON_STRING;
	token->start = (int)p->pos;

	while (!at_end(p)) {
		const char c = p->doc->buffer[p->pos];

		if (c == '"') {
			token->end = (int)p->pos;
			p->pos++;
			return true;
		}

		if (c == '\\') {
			/* On valide la séquence sans la décoder ici. */
			p->pos++;
			if (at_end(p)) {
				return false;
			}
			const char esc = p->doc->buffer[p->pos];
			switch (esc) {
			case '"':
			case '\\':
			case '/':
			case 'b':
			case 'f':
			case 'n':
			case 'r':
			case 't':
				p->pos++;
				break;
			case 'u':
				p->pos++;
				for (int i = 0; i < 4; i++) {
					if (at_end(p)) {
						return false;
					}
					const char h = p->doc->buffer[p->pos];
					const bool is_hex = (h >= '0' && h <= '9') ||
					                    (h >= 'a' && h <= 'f') ||
					                    (h >= 'A' && h <= 'F');
					if (!is_hex) {
						return false;
					}
					p->pos++;
				}
				break;
			default:
				return false;
			}
			continue;
		}

		/* Les caractères de contrôle nus sont interdits en JSON. */
		if ((unsigned char)c < 0x20) {
			return false;
		}

		p->pos++;
	}

	return false; /* chaîne non terminée */
}

static bool parse_number(Parser *p, int parent)
{
	JsonToken *token = alloc_token(p, parent);
	if (token == NULL) {
		return false;
	}

	token->type = JSON_NUMBER;
	token->start = (int)p->pos;

	if (peek(p) == '-') {
		p->pos++;
	}

	/* JSON number grammar: no leading zero, empty fraction or exponent. */
	if (peek(p) == '0') {
		p->pos++;
	} else {
		if (peek(p) < '1' || peek(p) > '9') return false;
		do { p->pos++; } while (peek(p) >= '0' && peek(p) <= '9');
	}
	if (peek(p) == '.') {
		p->pos++;
		if (peek(p) < '0' || peek(p) > '9') return false;
		do { p->pos++; } while (peek(p) >= '0' && peek(p) <= '9');
	}
	if (peek(p) == 'e' || peek(p) == 'E') {
		p->pos++;
		if (peek(p) == '+' || peek(p) == '-') p->pos++;
		if (peek(p) < '0' || peek(p) > '9') return false;
		do { p->pos++; } while (peek(p) >= '0' && peek(p) <= '9');
	}

	token->end = (int)p->pos;
	return true;
}

static bool parse_literal(Parser *p, int parent, const char *literal,
                          JsonType type)
{
	const size_t len = strlen(literal);
	if (p->pos + len > p->doc->length) {
		return false;
	}
	if (memcmp(p->doc->buffer + p->pos, literal, len) != 0) {
		return false;
	}

	JsonToken *token = alloc_token(p, parent);
	if (token == NULL) {
		return false;
	}

	token->type = type;
	token->start = (int)p->pos;
	token->end = (int)(p->pos + len);
	p->pos += len;
	return true;
}

static bool parse_object(Parser *p, int parent)
{
	JsonToken *token = alloc_token(p, parent);
	if (token == NULL) {
		return false;
	}

	const int self = p->doc->count - 1;
	token->type = JSON_OBJECT;
	token->start = (int)p->pos;
	p->pos++; /* accolade ouvrante */

	skip_whitespace(p);
	if (peek(p) == '}') {
		p->doc->tokens[self].end = (int)p->pos;
		p->pos++;
		return true;
	}

	for (;;) {
		skip_whitespace(p);
		if (peek(p) != '"') {
			return false; /* une clé est toujours une chaîne */
		}
		if (!parse_string(p, self)) {
			return false;
		}

		skip_whitespace(p);
		if (peek(p) != ':') {
			return false;
		}
		p->pos++;

		skip_whitespace(p);
		if (!parse_value(p, self)) {
			return false;
		}

		p->doc->tokens[self].size++;

		skip_whitespace(p);
		const char c = peek(p);
		if (c == ',') {
			p->pos++;
			continue;
		}
		if (c == '}') {
			p->doc->tokens[self].end = (int)p->pos;
			p->pos++;
			return true;
		}
		return false;
	}
}

static bool parse_array(Parser *p, int parent)
{
	JsonToken *token = alloc_token(p, parent);
	if (token == NULL) {
		return false;
	}

	const int self = p->doc->count - 1;
	token->type = JSON_ARRAY;
	token->start = (int)p->pos;
	p->pos++; /* crochet ouvrant */

	skip_whitespace(p);
	if (peek(p) == ']') {
		p->doc->tokens[self].end = (int)p->pos;
		p->pos++;
		return true;
	}

	for (;;) {
		skip_whitespace(p);
		if (!parse_value(p, self)) {
			return false;
		}

		p->doc->tokens[self].size++;

		skip_whitespace(p);
		const char c = peek(p);
		if (c == ',') {
			p->pos++;
			continue;
		}
		if (c == ']') {
			p->doc->tokens[self].end = (int)p->pos;
			p->pos++;
			return true;
		}
		return false;
	}
}

static bool parse_value(Parser *p, int parent)
{
	if (p->depth >= JSON_MAX_DEPTH) {
		return false;
	}

	skip_whitespace(p);
	if (at_end(p)) {
		return false;
	}

	bool ok;
	p->depth++;

	switch (peek(p)) {
	case '{':
		ok = parse_object(p, parent);
		break;
	case '[':
		ok = parse_array(p, parent);
		break;
	case '"':
		ok = parse_string(p, parent);
		break;
	case 't':
		ok = parse_literal(p, parent, "true", JSON_BOOL);
		break;
	case 'f':
		ok = parse_literal(p, parent, "false", JSON_BOOL);
		break;
	case 'n':
		ok = parse_literal(p, parent, "null", JSON_NULL);
		break;
	default:
		ok = parse_number(p, parent);
		break;
	}

	p->depth--;
	return ok;
}

bool json_parse(JsonDoc *doc, const char *buffer, size_t length)
{
	doc->buffer = buffer;
	doc->length = length;
	doc->count = 0;
	doc->ok = false;

	if (buffer == NULL || length == 0) {
		return false;
	}

	Parser parser = {.doc = doc, .pos = 0, .depth = 0};

	if (!parse_value(&parser, -1)) {
		doc->count = 0;
		return false;
	}

	/* Seuls des blancs peuvent suivre la valeur racine. */
	skip_whitespace(&parser);
	if (!at_end(&parser)) {
		doc->count = 0;
		return false;
	}

	doc->ok = true;
	return true;
}

const JsonToken *json_root(const JsonDoc *doc)
{
	if (!doc->ok || doc->count == 0) {
		return NULL;
	}
	return &doc->tokens[0];
}

static int token_index(const JsonDoc *doc, const JsonToken *token)
{
	if (token == NULL) {
		return -1;
	}
	const ptrdiff_t index = token - doc->tokens;
	if (index < 0 || index >= doc->count) {
		return -1;
	}
	return (int)index;
}

int json_size(const JsonToken *token)
{
	if (token == NULL) {
		return 0;
	}
	if (token->type != JSON_OBJECT && token->type != JSON_ARRAY) {
		return 0;
	}
	return token->size;
}

/**
 * Longueur d'un token, en tenant compte du fait qu'un conteneur englobe ses
 * enfants : on saute donc l'intégralité du sous-arbre.
 */
static int skip_subtree(const JsonDoc *doc, int index)
{
	const JsonToken *token = &doc->tokens[index];
	int remaining = 0;

	if (token->type == JSON_OBJECT) {
		remaining = token->size * 2; /* clé + valeur */
	} else if (token->type == JSON_ARRAY) {
		remaining = token->size;
	}

	int cursor = index + 1;
	for (int i = 0; i < remaining; i++) {
		if (cursor >= doc->count) {
			break;
		}
		cursor = skip_subtree(doc, cursor);
	}
	return cursor;
}

const JsonToken *json_get(const JsonDoc *doc, const JsonToken *object,
                          const char *key)
{
	const int self = token_index(doc, object);
	if (self < 0 || object->type != JSON_OBJECT || key == NULL) {
		return NULL;
	}

	int cursor = self + 1;
	for (int i = 0; i < object->size; i++) {
		if (cursor >= doc->count) {
			return NULL;
		}

		const JsonToken *key_token = &doc->tokens[cursor];
		const int value_index = cursor + 1;
		if (value_index >= doc->count) {
			return NULL;
		}

		if (json_string_equals(doc, key_token, key)) {
			return &doc->tokens[value_index];
		}

		cursor = skip_subtree(doc, value_index);
	}

	return NULL;
}

const JsonToken *json_at(const JsonDoc *doc, const JsonToken *array, int index)
{
	const int self = token_index(doc, array);
	if (self < 0 || array->type != JSON_ARRAY) {
		return NULL;
	}
	if (index < 0 || index >= array->size) {
		return NULL;
	}

	int cursor = self + 1;
	for (int i = 0; i < index; i++) {
		if (cursor >= doc->count) {
			return NULL;
		}
		cursor = skip_subtree(doc, cursor);
	}

	if (cursor >= doc->count) {
		return NULL;
	}
	return &doc->tokens[cursor];
}

/** Décode une séquence \\uXXXX en UTF-8. Retourne le nombre d'octets écrits. */
static size_t decode_unicode(const char *hex, char *dest, size_t dest_room)
{
	unsigned int code = 0;
	for (int i = 0; i < 4; i++) {
		const char c = hex[i];
		code <<= 4;
		if (c >= '0' && c <= '9') {
			code |= (unsigned int)(c - '0');
		} else if (c >= 'a' && c <= 'f') {
			code |= (unsigned int)(c - 'a' + 10);
		} else if (c >= 'A' && c <= 'F') {
			code |= (unsigned int)(c - 'A' + 10);
		} else {
			return 0;
		}
	}

	if (code < 0x80) {
		if (dest_room < 1) {
			return 0;
		}
		dest[0] = (char)code;
		return 1;
	}
	if (code < 0x800) {
		if (dest_room < 2) {
			return 0;
		}
		dest[0] = (char)(0xC0 | (code >> 6));
		dest[1] = (char)(0x80 | (code & 0x3F));
		return 2;
	}

	if (dest_room < 3) {
		return 0;
	}
	dest[0] = (char)(0xE0 | (code >> 12));
	dest[1] = (char)(0x80 | ((code >> 6) & 0x3F));
	dest[2] = (char)(0x80 | (code & 0x3F));
	return 3;
}

bool json_copy_string(const JsonDoc *doc, const JsonToken *token, char *dest,
                      size_t dest_size)
{
	if (dest == NULL || dest_size == 0) {
		return false;
	}

	dest[0] = '\0';
	if (token == NULL || token->type != JSON_STRING) {
		return false;
	}

	size_t out = 0;
	const size_t limit = dest_size - 1;

	for (int i = token->start; i < token->end && out < limit; i++) {
		const char c = doc->buffer[i];

		if (c != '\\') {
			const unsigned char lead = (unsigned char)c;
			const size_t bytes = lead < 0x80 ? 1 : lead < 0xe0 ? 2 : lead < 0xf0 ? 3 : 4;
			if (bytes > limit - out || bytes > (size_t)(token->end - i)) break;
			memcpy(dest + out, doc->buffer + i, bytes);
			out += bytes;
			i += (int)bytes - 1;
			continue;
		}

		/* Séquence d'échappement : le parseur a déjà validé la forme. */
		if (i + 1 >= token->end) {
			break;
		}
		i++;

		switch (doc->buffer[i]) {
		case 'n':
			dest[out++] = '\n';
			break;
		case 't':
			dest[out++] = '\t';
			break;
		case 'r':
			dest[out++] = '\r';
			break;
		case 'b':
			dest[out++] = '\b';
			break;
		case 'f':
			dest[out++] = '\f';
			break;
		case '"':
			dest[out++] = '"';
			break;
		case '\\':
			dest[out++] = '\\';
			break;
		case '/':
			dest[out++] = '/';
			break;
		case 'u': {
			if (i + 4 >= token->end) {
				i = token->end;
				break;
			}
			const size_t written =
			    decode_unicode(doc->buffer + i + 1, dest + out, limit - out);
			if (written == 0) {
				/* Pas la place ou séquence invalide : on s'arrête proprement. */
				i = token->end;
				break;
			}
			out += written;
			i += 4;
			break;
		}
		default:
			break;
		}
	}

	dest[out] = '\0';
	return true;
}

bool json_string_equals(const JsonDoc *doc, const JsonToken *token,
                        const char *text)
{
	if (token == NULL || token->type != JSON_STRING || text == NULL) {
		return false;
	}

	const size_t len = strlen(text);
	const size_t token_len = (size_t)(token->end - token->start);

	/*
	 * Comparaison directe quand aucune séquence d'échappement n'est présente,
	 * ce qui est le cas courant pour les clés du protocole.
	 */
	if (token_len != len) {
		return false;
	}
	return memcmp(doc->buffer + token->start, text, len) == 0;
}

static bool token_to_double(const JsonDoc *doc, const JsonToken *token,
                           double *out)
{
	if (token == NULL || token->type != JSON_NUMBER) {
		return false;
	}

	int i = token->start;
	const int end = token->end;
	bool negative = false;

	if (i < end && (doc->buffer[i] == '-' || doc->buffer[i] == '+')) {
		negative = doc->buffer[i] == '-';
		i++;
	}

	double value = 0.0;
	while (i < end && doc->buffer[i] >= '0' && doc->buffer[i] <= '9') {
		value = value * 10.0 + (double)(doc->buffer[i] - '0');
		i++;
	}

	if (i < end && doc->buffer[i] == '.') {
		i++;
		double scale = 0.1;
		while (i < end && doc->buffer[i] >= '0' && doc->buffer[i] <= '9') {
			value += (double)(doc->buffer[i] - '0') * scale;
			scale *= 0.1;
			i++;
		}
	}

	if (i < end && (doc->buffer[i] == 'e' || doc->buffer[i] == 'E')) {
		i++;
		bool exp_negative = false;
		if (i < end && (doc->buffer[i] == '-' || doc->buffer[i] == '+')) {
			exp_negative = doc->buffer[i] == '-';
			i++;
		}

		int exponent = 0;
		while (i < end && doc->buffer[i] >= '0' && doc->buffer[i] <= '9') {
			exponent = exponent * 10 + (doc->buffer[i] - '0');
			i++;
			if (exponent > 308) {
				break; /* borne pour éviter une boucle inutile */
			}
		}

		double factor = 1.0;
		for (int e = 0; e < exponent; e++) {
			factor *= 10.0;
		}
		value = exp_negative ? value / factor : value * factor;
	}

	*out = negative ? -value : value;
	return true;
}

int json_int(const JsonDoc *doc, const JsonToken *token, int fallback)
{
	double value;
	if (!token_to_double(doc, token, &value) || !isfinite(value) ||
	    value < INT_MIN || value > INT_MAX) {
		return fallback;
	}
	return (int)value;
}

float json_float(const JsonDoc *doc, const JsonToken *token, float fallback)
{
	double value;
	if (!token_to_double(doc, token, &value) || !isfinite(value) ||
	    value < -FLT_MAX || value > FLT_MAX) {
		return fallback;
	}
	return (float)value;
}

bool json_bool(const JsonDoc *doc, const JsonToken *token, bool fallback)
{
	if (token == NULL || token->type != JSON_BOOL) {
		return fallback;
	}
	return doc->buffer[token->start] == 't';
}

int json_get_int(const JsonDoc *doc, const JsonToken *object, const char *key,
                 int fallback)
{
	return json_int(doc, json_get(doc, object, key), fallback);
}

bool json_get_bool(const JsonDoc *doc, const JsonToken *object, const char *key,
                   bool fallback)
{
	return json_bool(doc, json_get(doc, object, key), fallback);
}

bool json_get_string(const JsonDoc *doc, const JsonToken *object,
                     const char *key, char *dest, size_t dest_size)
{
	return json_copy_string(doc, json_get(doc, object, key), dest, dest_size);
}
