#ifndef STRCMP_H__
#define STRCMP_H__

int strcmp(const char *s1, const char *s2) {
    while (s1 != '\0' && s2 != '\0') {
        if (s1 != s2) {
            return *s1 - *s2;
        }
        s1++; s2++;
    }
    return *s1 - *s2;
}

#endif
