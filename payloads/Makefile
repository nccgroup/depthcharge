ARCH ?= arm

ifeq ($(ARCH), arm)
	CROSS_COMPILE ?= arm-none-eabi-
else ifeq ($(ARCH), aarch64)
	CROSS_COMPILE ?= aarch64-none-elf-
endif

INCLUDE_DIR := include
OUTPUT_DIR  := output

PAYLOADS 	:= $(patsubst src/%.c,%,$(wildcard src/*.c))
ELF_OUTPUT	:= $(PAYLOADS:%=$(OUTPUT_DIR)/$(ARCH)-%.elf)
BINARIES 	:= $(PAYLOADS:%=$(OUTPUT_DIR)/$(ARCH)-%.bin)
ASM_OUTPUT	:= $(PAYLOADS:%=$(OUTPUT_DIR)/$(ARCH)-%.asm)

DEBUG ?= n

CC			:= $(CROSS_COMPILE)gcc
LD			:= $(CROSS_COMPILE)ld
OBJCOPY		:= $(CROSS_COMPILE)objcopy
OBJDUMP		:= $(CROSS_COMPILE)objdump

CFLAGS = \
	-Wall -Wextra \
	-ffreestanding -fPIC -nostdlib \
	-I$(INCLUDE_DIR) \
	-DARCH_$(ARCH)

ifeq (DEBUG,y)
	CFLAGS += -O0
else
	CFLAGS += -O2
endif

# Allow user to append additional flags via CFLAGS_EXTRA
CFLAGS += $(CFLAGS_EXTRA)

all: output/payload.py $(BINARIES) $(ASM_OUTPUT)

output:
	mkdir -p $@
	
output/$(ARCH)-%.elf: src/%.c output
	$(CC) $(CFLAGS) -e main $< -o $@

output/$(ARCH)-%.bin: output/$(ARCH)-%.elf
	$(OBJCOPY) -O binary $< $@

output/$(ARCH)-%.asm: output/$(ARCH)-%.bin
	$(OBJDUMP) -m $(ARCH) -b binary -D $< > $@

output/payload.py: $(BINARIES)
	python3 ./create-payload-src.py output payload.py

clean:
	rm -rf output

.PHONY: clean
