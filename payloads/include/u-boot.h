#ifndef UBOOT_H_
#define UBOOT_H_

#include <stdlib.h>
#include <stdarg.h>

#ifdef ARCH_arm
#   define DECLARE_GLOBAL_DATA_PTR(gd) register volatile global_data_t *gd asm("r9");
#else
#   error "Unsupported architechture"
#endif

typedef struct {
    unsigned long (*get_version)(void);
    int (*getc)(void);
    int (*tstc)(void);
    void (*putc)(const char);
    void (*puts)(const char *);
    int (*printf)(const char *, ...);
    void (*install_hdler)(int, void*, void*);
    void (*free_hdlr)(int);
    void* (*malloc)(size_t);
    void (*free)(void*);
    void (*udelay)(unsigned long);
    unsigned long (*get_timer)(unsigned long);
    int (*vprintf)(const char *, va_list);
    int (*do_reset)(void*, int, int, char * const[]);
    char* (*env_get)(const char *);
    int (*env_set)(const char *, const char *);
    unsigned long (*simple_strtoul)(const char *, char **, unsigned int);
    int (*strict_strtoul)(const char *, unsigned int, unsigned long *);
    long (*simple_strtol)(const char *, char **, unsigned int);
    int (*strcmp)(const char *, const char *);
    unsigned long (*ustrtoul)(const char *, char **, unsigned int);
    unsigned long long (*ustrtoull)(const char *, char **, unsigned int);
} jt_funcs_t;

typedef struct {
    void *bd;
    unsigned long int flags;
    unsigned int baudrate;
    unsigned long clks[4];
    unsigned long padding[21];
    jt_funcs_t *jt;
} global_data_t;

#endif
