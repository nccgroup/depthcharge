BUILDS := builds

# User is responsible for setting ARDUINO_BUILDER

ARDUINO_USER_DIR ?= $(realpath $(HOME)/.arduino15)/
ARDUINO_INSTALL_DIR := $(dir $(realpath $(shell which $(ARDUINO_BUILDER))))

COMMON_ARGS := \
	-core-api-version=10810 \
	-hardware $(ARDUINO_INSTALL_DIR)hardware \
	-hardware $(ARDUINO_USER_DIR)packages \
	-tools $(ARDUINO_INSTALL_DIR)tools-builder \
	-tools $(ARDUINO_INSTALL_DIR)hardware/tools/avr \
	-tools $(ARDUINO_USER_DIR)packages \
	-built-in-libraries $(ARDUINO_INSTALL_DIR)libraries \
	-libraries $(realpath .) 
	-warnings=all \

ifneq (VERBOSE,)
	COMMON_ARGS += -verbose
endif


help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@echo "  teensy36    Teensy 3.6 (https://www.pjrc.com/store/teensy36.html)"
	@echo "  clean       Clean build files"
	@echo ""
	@if [ -z "$(ARDUINO_BUILDER)" ]; then\
		echo "Builder: Not specified - set via environment variable or Make argument."; \
		echo "         This should be the full path to the arduino-builder program"; \
		echo "         included with the Arduino IDE."; \
	else \
		echo "Builder: $(ARDUINO_BUILDER)"; \
	fi
	@echo ""

all: teensy36

$(BUILDS):
	@mkdir -p "$@"

builder_check: $(BUILDS)
	@if [ -z "$(ARDUINO_BUILDER)" ]; then \
		echo "Error: ARDUINO_BUILDER variable not specified." >&2; \
		echo "  This should be the full path to the arduino-builder program" >&2; \
		echo "  provided with the Arduino IDE." >&2; \
		echo "" >&2; \
		exit 1; \
	elif [ -f $(ARDUINO_BUILDER) -a -d $(ARDUINO_INSTALL_DIR) ]; then \
		echo "Found $(ARDUINO_BUILDER) in $(ARDUINO_INSTALL_DIR)"; \
	else \
		echo "Cannot find $(ARDUINO_BUILDER)" >&2; \
		echo "ARDUINO_INSTALL_DIR=$(ARDUINO_INSTALL_DIR)" >&2; \
		exit 1; \
	fi

teensy36: Depthcharge-Teensy3.6/Depthcharge-Teensy3.6.ino builder_check
	@mkdir -p $(ARDUINO_USER_DIR)/packages
	@mkdir -p $(BUILDS)/$@
	$(ARDUINO_BUILDER) -compile \
		$(COMMON_ARGS) \
		-build-path $(BUILDS)/$@ -build-cache $(BUILDS)/$@ \
		-fqbn=teensy:avr:teensy36:usb=serial,speed=180,opt=o2std,keys=en-us \
		$<

clean:
	rm -rfv $(BUILDS)

.PHONY: clean 
