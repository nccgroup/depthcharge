#ifndef __CONFIG_H
#define __CONFIG_H

#include <default_cmds.h>

#ifdef INCLUDE_MEMORY_COMMANDS
#define CONFIG_CMD_MEMORY
#endif

#undef CONFIG_CMD_I2C
#undef CONFIG_CMD_LOADB

#if CONFIG_DOESNT_EXIST
#error Fail here
#endif

#endif
