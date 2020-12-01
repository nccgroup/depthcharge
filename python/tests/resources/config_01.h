#ifndef __CONFIG_H
#define __CONFIG_H

#include <default_cmds.h>

#define CONFIG_CMD_MEMORY
#undef CONFIG_CMD_I2C
#undef CONFIG_CMD_LOADB

#if CONFIG_DOESNT_EXIST
#error Fail here
#endif

#endif
