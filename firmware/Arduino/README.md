This directory provides a Makefile-based build for Arduino firmware.

# Make-based build

To build the firmware for a supported target platform, invoke make with:

1. The path to the `ardunio-builder` program included with the Arduino IDE. 
2. The target platform name, as shown in the output for `make help`.

Item 1 can be done using an `ARDUINO_BUILDER` environment variable,
or by specifying it in the `make` invocation. Both are shown below, for a build
of firmware targeting the Teensy3.6 platform.

```
$ export ARDUINO_BUILDER=/path/to/arduino-builder
$ make teensy36
```

```
$ make ARDUINO_BUILDER=/path/to/arduino-builder teensy36
```

The `arduino-builder` program, included with all modern Arduino-based
environments, is used to support this. However, this program does not appear
to be installed to users' `$PATH` when the Arduino IDE is installed. This
may be for the best, given that different Arduino environments (e.g. official
vs Energia) ship their own `arduino-builder` program. You must use the program
corresponding to the relevant build environment.

If your Arduino preferences are stored in a directory other than the default
`$HOME/arduino15` directory, you must also specify the full path to this
directory via `ARDUINO_USER_DIR`.


# IDE-based build

If you instead prefer to use the Arduino IDE, you'll need to copy or symlink
the `Depthcharge` library (the entire directory) to your personal
`Arduino/libraries` directory.

Then, open the target-specific ino file in the Arduino IDE.

# Directories

* The `Depthcharge` directory contains the core firmware functionality as a "library."
* Directories in the form `Depthcharge-<target>` contain the top-level and
  platform-specific, ino files. These are intended to be minimalist 
  implementations that simply initialize peripherals and invoke a
  `Depthcharge::Companion` instance's `processEvents()` method.
* A `builds/` directory is created to store build artifacts.
