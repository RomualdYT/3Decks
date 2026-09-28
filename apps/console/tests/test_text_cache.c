#include "text_cache.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static TextCache cache;

int main(void)
{
    text_cache_reset(&cache);
    assert(text_cache_find(&cache, "Volume") == -1);
    const int volume = text_cache_insert(&cache, "Volume");
    assert(volume >= 0 && text_cache_find(&cache, "Volume") == volume);
    assert(text_cache_insert(&cache, "Volume") == -1);
    assert(text_cache_find(&cache, "volume") == -1);
    const int accent = text_cache_insert(&cache, "Fenêtres");
    assert(accent >= 0 && accent != volume && text_cache_find(&cache, "Fenêtres") == accent);

    assert(!text_cache_cacheable(NULL) && !text_cache_cacheable(""));
    char key[TEXT_CACHE_KEY_MAX + 1];
    memset(key, 'k', TEXT_CACHE_KEY_MAX - 1); key[TEXT_CACHE_KEY_MAX - 1] = 0;
    assert(text_cache_cacheable(key));
    memset(key, 'k', TEXT_CACHE_KEY_MAX); key[TEXT_CACHE_KEY_MAX] = 0;
    assert(!text_cache_cacheable(key) && text_cache_insert(&cache, key) == -1);
    assert(text_cache_find(&cache, key) == -1);

    /* Every stored key stays reachable until the table reports it is full. */
    int inserted = 2;
    for (int i = 0; text_cache_has_room(&cache); i++) {
        snprintf(key, sizeof(key), "%d:%02d", i / 60, i % 60);
        assert(text_cache_insert(&cache, key) >= 0);
        inserted++;
    }
    assert(inserted == TEXT_CACHE_CAPACITY);
    assert(text_cache_insert(&cache, "late") == -1);
    for (int i = 0; i < TEXT_CACHE_CAPACITY - 2; i++) {
        snprintf(key, sizeof(key), "%d:%02d", i / 60, i % 60);
        assert(text_cache_find(&cache, key) >= 0);
    }
    assert(text_cache_find(&cache, "Volume") == volume && text_cache_find(&cache, "absent") == -1);

    text_cache_reset(&cache);
    assert(text_cache_find(&cache, "Volume") == -1 && text_cache_has_room(&cache));
    puts("text cache: lookups, UTF-8 keys, length limit, full table and reset passed");
}
