/*
 * Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
 * Free software under the GNU GPL v3. See LICENSE for details.
 */

/**
 * @file json.h
 * @brief Parseur JSON en arène statique, sans allocation dynamique.
 *
 * Conçu pour la 3DS : le nombre de tokens est borné à la compilation, aucune
 * allocation n'a lieu à l'exécution et une entrée malformée ou trop grande
 * échoue proprement au lieu de consommer la mémoire.
 *
 * Le parseur travaille sur un tampon que l'appelant possède. Les chaînes ne
 * sont pas copiées : chaque token pointe dans le tampon d'origine.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>

/** Nombre maximal de tokens pour un document. */
#define JSON_MAX_TOKENS 1024

/** Profondeur maximale d'imbrication, garde-fou contre les entrées hostiles. */
#define JSON_MAX_DEPTH 24

typedef enum {
	JSON_UNDEFINED = 0,
	JSON_OBJECT,
	JSON_ARRAY,
	JSON_STRING,
	JSON_NUMBER,
	JSON_BOOL,
	JSON_NULL,
} JsonType;

typedef struct {
	JsonType type;
	int start;  /**< Index du premier caractère dans le tampon. */
	int end;    /**< Index suivant le dernier caractère. */
	int size;   /**< Nombre d'enfants (paires pour un objet). */
	int parent; /**< Index du token parent, -1 pour la racine. */
} JsonToken;

typedef struct {
	const char *buffer;
	size_t length;
	JsonToken tokens[JSON_MAX_TOKENS];
	int count;
	bool ok;
} JsonDoc;

/**
 * Analyse `buffer` (`length` octets) et remplit `doc`.
 * Retourne `false` si le document est invalide, trop profond ou trop grand.
 * `doc->buffer` doit rester valide aussi longtemps que `doc` est consulté.
 */
bool json_parse(JsonDoc *doc, const char *buffer, size_t length);

/** Retourne le token racine, ou NULL si le document est vide ou invalide. */
const JsonToken *json_root(const JsonDoc *doc);

/**
 * Cherche la valeur associée à `key` dans l'objet `object`.
 * Retourne NULL si absent ou si `object` n'est pas un objet.
 */
const JsonToken *json_get(const JsonDoc *doc, const JsonToken *object,
                          const char *key);

/** Retourne l'élément d'index `index` d'un tableau, ou NULL. */
const JsonToken *json_at(const JsonDoc *doc, const JsonToken *array, int index);

/** Nombre d'éléments d'un tableau ou de paires d'un objet, 0 si autre type. */
int json_size(const JsonToken *token);

/**
 * Copie une chaîne dans `dest` (au plus `dest_size - 1` octets, toujours
 * terminée par zéro). Les séquences d'échappement JSON sont interprétées.
 * Retourne `false` si le token n'est pas une chaîne, `dest` restant vide.
 */
bool json_copy_string(const JsonDoc *doc, const JsonToken *token, char *dest,
                      size_t dest_size);

/** Compare le contenu d'un token chaîne à `text`. */
bool json_string_equals(const JsonDoc *doc, const JsonToken *token,
                        const char *text);

/** Lit un entier. Retourne `fallback` si le token n'est pas numérique. */
int json_int(const JsonDoc *doc, const JsonToken *token, int fallback);

/** Lit un flottant. Retourne `fallback` si le token n'est pas numérique. */
float json_float(const JsonDoc *doc, const JsonToken *token, float fallback);

/** Lit un booléen. Retourne `fallback` si le token n'est pas booléen. */
bool json_bool(const JsonDoc *doc, const JsonToken *token, bool fallback);

/* --- Raccourcis pratiques : accès par clé avec valeur de repli --- */

int json_get_int(const JsonDoc *doc, const JsonToken *object, const char *key,
                 int fallback);

bool json_get_bool(const JsonDoc *doc, const JsonToken *object, const char *key,
                   bool fallback);

/**
 * Copie la chaîne associée à `key`. Si la clé est absente ou n'est pas une
 * chaîne, `dest` reçoit une chaîne vide et la fonction retourne `false`.
 */
bool json_get_string(const JsonDoc *doc, const JsonToken *object,
                     const char *key, char *dest, size_t dest_size);
