#include "text_cache.h"
#include <stdint.h>
#include <string.h>

static size_t home_slot(unsigned face, const char *key)
{
    uint32_t hash = (2166136261u ^ face) * 16777619u; /* FNV-1a */
    for (const unsigned char *p = (const unsigned char *)key; *p; p++)
        hash = (hash ^ *p) * 16777619u;
    return hash % TEXT_CACHE_SLOTS;
}

void text_cache_reset(TextCache *cache)
{
    memset(cache, 0, sizeof(*cache));
}

bool text_cache_cacheable(const char *key)
{
    return key && *key && strlen(key) < TEXT_CACHE_KEY_MAX;
}

bool text_cache_has_room(const TextCache *cache)
{
    return cache->count < TEXT_CACHE_CAPACITY;
}

int text_cache_find(const TextCache *cache, unsigned face, const char *key)
{
    if (!text_cache_cacheable(key)) return -1;
    for (size_t i = 0, slot = home_slot(face, key); i < TEXT_CACHE_SLOTS;
         i++, slot = (slot + 1) % TEXT_CACHE_SLOTS) {
        const TextCacheSlot *entry = &cache->slots[slot];
        if (!entry->used) return -1;
        if (entry->face == face && !strcmp(entry->key, key)) return (int)slot;
    }
    return -1;
}

int text_cache_insert(TextCache *cache, unsigned face, const char *key)
{
    if (!text_cache_cacheable(key) || !text_cache_has_room(cache)) return -1;
    size_t slot = home_slot(face, key);
    while (cache->slots[slot].used) {
        if (cache->slots[slot].face == face && !strcmp(cache->slots[slot].key, key)) return -1;
        slot = (slot + 1) % TEXT_CACHE_SLOTS;
    }
    TextCacheSlot *entry = &cache->slots[slot];
    strcpy(entry->key, key);
    entry->face = face;
    entry->used = true;
    cache->count++;
    return (int)slot;
}
