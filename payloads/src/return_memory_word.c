#include <stdlib.h>

#include "depthcharge.h"
#include "str2uint.h"

int main(int argc, char * argv[])
{
    DECLARE_GLOBAL_DATA_VOID_PTR(gd);
    unsigned int *ret_p;

    if (argc < 2) {
        return (int) gd;
    }

    ret_p = (unsigned int *) str2uint(argv[1]);
    return (int) (*ret_p);
}
