#include <stdlib.h>

#include "depthcharge.h"
#include "str2ulong.h"

unsigned long main(int argc, char * argv[])
{
    DECLARE_GLOBAL_DATA_VOID_PTR(gd);
    unsigned long *ret_p;

    if (argc < 2) {
        return (unsigned long) gd;
    }

    ret_p = (unsigned long *) str2ulong(argv[1]);
    return (*ret_p);
}
