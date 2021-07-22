#include "depthcharge.h"
#include "u-boot.h"
#include "str2ulong.h"

unsigned long main(int argc, char *argv[])
{
    int status;
    jt_funcs_t *jt;
    unsigned long jt_ul;
    unsigned long mem_addr, mem_len;

    if (argc != 4) {
        return 1;
    }

    jt_ul = str2ulong(argv[1]);
    if (jt_ul == 0) {
        return 2;
    }
    jt = (jt_funcs_t*) jt_ul;

    status = jt->strict_strtoul(argv[2], 0, &mem_addr);
    if (status != 0) {
        jt->printf("Invalid memory address: %s\n", argv[1]);
        return 3;
    }

    status = jt->strict_strtoul(argv[3], 0, &mem_len);
    if (status != 0) {
        jt->printf("Invalid memory length: %s\n", argv[2]);
        return 4;
    }

    jt->puts("-:[START]:-");
    jt->getc();

    unsigned int i;
    volatile char * addr = (volatile char *) mem_addr;

    for (i = 0; i < mem_len; i++) {
        jt->putc(addr[i]);
    }

    jt->puts("-:[|END|]:-");

    return 0;
}
