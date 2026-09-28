#pragma once
#include <stdlib.h>
/* libctru's aligned allocation, backed by the host allocator for transport tests. */
static inline void *memalign(size_t alignment, size_t size)
{
    void *result = NULL;
    return posix_memalign(&result, alignment, size) == 0 ? result : NULL;
}
