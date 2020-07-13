#ifndef SKPR_H__
#define SKPR_H__

#define UNUSED(var) do { (void) var; } while (0)

#ifdef ARCH_arm
#   define DECLARE_GLOBAL_DATA_VOID_PTR(gd) \
        register volatile void *gd asm("r9")
#else
#   error "Unsupported architechture"
#endif

#endif
