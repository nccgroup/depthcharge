#ifndef DEPTHCHARGE_H__
#define DEPTHCHARGE_H__

#define UNUSED(var) do { (void) var; } while (0)

#ifdef ARCH_arm
#   define DECLARE_GLOBAL_DATA_VOID_PTR(gd) \
        register volatile void *gd asm("r9")
#elif ARCH_aarch64
#   define DECLARE_GLOBAL_DATA_VOID_PTR(gd) \
        register volatile void *gd asm("x18")
#else
#   error "Unsupported architechture"
#endif

#endif
