#ifndef STR2UINT_H__
#define STR2UINT_H__

#include <stdbool.h>
#include "strlen.h"

static inline unsigned int str2uint_hex(const char *s)
{
    unsigned int value = 0;

    while (*s) {
        value <<= 4;

        unsigned int c = *s;
        if (c >= '0' && c <= '9') {
            c -= '0';
        } else if (c >= 'a' && c <= 'f') {
            c = c - 'a' + 10;
        } else if (c >= 'A' && c <= 'F') {
            c = c - 'A' + 10;
        } else {
            return 0;
        }

        value += c;
        s++;
    }

    return value;
}

static inline unsigned int str2uint_dec(const char *s)
{
    unsigned int value = 0;

    while (*s) {
        value *= 10;

        unsigned int c = *s;
        if (c >= '0' && c <= '9') {
            c -= '0';
        } else {
            return 0;
        }

        value += c;
        s++;
    }

    return value;
}

// Simple string to unsigned int conversion with an atoi-esque lack of proper
// input validation and overflow checks. Returns 0 on invalid input and will
// overflow if input exceeds the size of an unsigned int.
static inline unsigned int str2uint(const char *s)
{
    size_t len = strlen(s);
    if (len > 2 && s[0] == '0' && s[1] == 'x') {
        s += 2;
        return str2uint_hex(s);
    }
    return str2uint_dec(s);
}


#endif
