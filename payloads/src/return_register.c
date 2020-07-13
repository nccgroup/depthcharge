#include "depthcharge.h"

#ifdef ARCH_arm

#define ASSIGN_REGVAL(retval, reg) do { \
    asm("mov %0, " # reg : "=r" (retval) : /* No C Input */ : ); \
} while(0)


/*
 * go-retreg:  Return the specified register value
 *
 * Assumed Input arguments:
 *      r0: argc
 *      r1: argv
 *
 * Return value in r0
 */
int main(int argc, char * argv[])
{
    register int r0 asm("r0");

    if (argc < 2) {
        ASSIGN_REGVAL(r0, r9);
        return r0;
    }

    /* Coerce the compiler into using only r0 when computing jump table
     * offsets for the following switch...case */
    asm("ldr  %0, [%1, #4]\n\t"
        "ldrb %0, [%0]\n\t"
        "sub  %0, %0, #0x61"
        : "=r" (r0)
        : "r"  (argv)
    );

    switch (r0) {
        case 0:
            // NOP
            break;
        case 1:
            ASSIGN_REGVAL(r0, r1);
            break;
        case 2:
            ASSIGN_REGVAL(r0, r2);
            break;
        case 3:
            ASSIGN_REGVAL(r0, r3);
            break;
        case 4:
            ASSIGN_REGVAL(r0, r4);
            break;
        case 5:
            ASSIGN_REGVAL(r0, r5);
            break;
        case 6:
            ASSIGN_REGVAL(r0, r6);
            break;
        case 7:
            ASSIGN_REGVAL(r0, r7);
            break;
        case 8:
            ASSIGN_REGVAL(r0, r8);
            break;
        case 9:
            // Fall-through.  r9 (Contains global data pointer)
        default:
            ASSIGN_REGVAL(r0, r9);
            break;
        case 10:
            ASSIGN_REGVAL(r0, r10);
            break;
        case 11:
            ASSIGN_REGVAL(r0, r11);
            break;
        case 12:
            ASSIGN_REGVAL(r0, r12);
            break;
        case 13:
            ASSIGN_REGVAL(r0, sp);
            break;
        case 14:
            ASSIGN_REGVAL(r0, lr);
            break;
        case 15:
            ASSIGN_REGVAL(r0, pc);
            break;
        case 16:
            asm volatile ("mrs %0, cpsr" : "=r" (r0) : );
            break;
    };

    return r0;
}

#else
#   error "go-regrd: Unsupported architecthure"
#endif
