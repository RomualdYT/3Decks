#pragma once
#include <stdbool.h>
#include <stddef.h>

/*
 * Fixed-size string index for parsed text. It only maps a label to a slot: the
 * caller owns the parsed data stored at that slot. Nothing is allocated and a
 * full table is reported rather than evicted, so the caller can reset it
 * together with the glyph buffer the slots refer to.
 */
#define TEXT_CACHE_SLOTS 256
#define TEXT_CACHE_KEY_MAX 96
/* Keeping the table at most 3/4 full bounds the length of every probe. */
#define TEXT_CACHE_CAPACITY (TEXT_CACHE_SLOTS * 3 / 4)

typedef struct {
    char key[TEXT_CACHE_KEY_MAX];
    bool used;
} TextCacheSlot;

typedef struct {
    TextCacheSlot slots[TEXT_CACHE_SLOTS];
    size_t count;
} TextCache;

void text_cache_reset(TextCache *cache);
/* Non-empty and short enough to be stored as a key. */
bool text_cache_cacheable(const char *key);
bool text_cache_has_room(const TextCache *cache);
/* Slot holding `key`, or -1 when absent or not cacheable. */
int text_cache_find(const TextCache *cache, const char *key);
/*
 * Stores an absent, cacheable `key` and returns its slot. Returns -1 when the
 * key is present, not cacheable or the table has no room.
 */
int text_cache_insert(TextCache *cache, const char *key);
