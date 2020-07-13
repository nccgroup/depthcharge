#ifndef STRLEN_H__
#define STRLEN_H__

#include <stdlib.h>

static inline size_t strlen(const char *s)
{
    size_t ret = 0;
    while (*s++) {
        ret++;
    }
    return ret;
}

#endif
