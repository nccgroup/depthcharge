#include "depthcharge.h"
#include "u-boot.h"
#include "str2uint.h"

int main(int argc, char *argv[])
{
    int status;
    jt_funcs_t *jt;
    unsigned int jt_u;
    unsigned long mem_addr, mem_len;

    if (argc != 4) {
        return 1;
    }

    jt_u = str2uint(argv[1]);
    if (jt_u == 0) {
        return 2;
    }
    jt = (jt_funcs_t*) jt_u;

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
