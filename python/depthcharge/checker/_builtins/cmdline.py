# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# Lines with links are just going to be long.
# flake8: noqa = E501

"""
Built-in SecurityRisk definitions associated with exposure of U-Boot command-line.
This submodule is not intended for direct usage; these items are loaded by the parent subpackage.
"""

from textwrap import dedent

from .. import SecurityImpact


_BUILTIN_DEFS = (
    ('CONFIG_CMDLINE', True, {
        'impact': SecurityImpact.ATTACK_SURFACE,

        'summary':
            'U-Boot console exposes large attack surface to attackers with physical access',

        'description': dedent("""\
            The U-Boot command-line traditionally exposes highly privileged commands to an
            unauthenticated user. Given physical access to a system's corresponding I/O interface
            (e.g. UART), an unauthorized user can perform any of the exposed actions.

            A majority of standard U-Boot commands can be abused to read/write memory or execute
            arbitrary code. However, this tool is not exhaustive and does not cover
            the breadth of standard and vendor-specific commands that can present security risks.

            Consider this a very significant  attack surface warranting further investigation,
            even if Depthcharge does not report any specific commands, for lack of knowledge of
            definitions.
         """),

        'recommendation': dedent("""\
            Disable CONFIG_CMDLINE and instead implement `board_run_command()` if this
            functionality is not required in production systems. (Refer to usbarmory.c in the
            latest upstream U-Boot source code for an example.)

            Otherwise, identify the minimum required number operations needed to support the
            business case for this functionality and limit enabled commands to this subset.
            Before allowing access to this reduced functionality, consider requiring that the
            operator authenticate to the device via a cryptographic challenge-response mechanism
            based upon device-unique secrets. Refer to the *Authenticated Access* section of
            the following paper for more information on this scheme.

            <https://research.nccgroup.com/wp-content/uploads/2020/02/NCC-Group-Whitepaper-Microcontroller-Readback-Protection-1.pdf>
        """),
    }),

    ('CONFIG_CMD_BDI', True, {
        'summary': 'bdinfo console command provides useful information to attackers',

        'impact': SecurityImpact.INFO_LEAK,

        'description': dedent("""\
            The bdinfo command displays board-specific information including the memory addresses
            of various regions and data structures. This can be leveraged to inform and automate
            attacks.

            *Reference* - Depthcharge usage of `bdinfo` output:
                <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.html#depthcharge.Depthcharge.uboot_global_data>

        """),

        'recommendation': 'Disable the `bdinfo` command via `CONFIG_CMD_BDI`\n',
    }),

    ('CONFIG_CMD_CRC32', True, {
        'summary': 'The crc32 console command can be abused to read and tamper with code and data in RAM',
        'impact': SecurityImpact.RD_MEM | SecurityImpact.WR_MEM,

        'description': dedent("""
            The `crc32` U-Boot console command can be performed over arbitrary lengths. In lieu of
            memory commands such as `md`, `crc32` can be used to read arbitrary memory contents
            a few bytes at a time, in conjunction with a simple lookup table.

            Furthermore, because this command allows the checksum to be written to an arbitrary
            memory location, this command can be abused as an arbitrary write primitive that
            allows an attacker with console access to patch running code. A description of
            how this can be (ab)used in practice is presented in the Depthcharge documentation:

            * <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.hunter.html#depthcharge.hunter.ReverseCRC32Hunter>
            * <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.CRC32MemoryWriter>
            * <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.CRC32MemoryReader>

        """),

        'recommendation': dedent("""\
            Disable the `crc32` command via `CONFIG_CMD_CRC32`.

            If platform requirements appear necessitate this command, re-evaluate the requirements to
            determine if a cryptographic hash function represents a better alternative.
            CRC32 is not resistant to malicious tampering. A cryptographic hash function (e.g.
            SHA-2, SHA-3) is better suited if the checksum is relied upon for anything other than
            detecting random failures.

            If CRC32 absolutely must be used, patch the implementation to remove its ability to write
            to arbitrary memory locations. Also, restrict the operation to multiples of fixed block
            sizes (e.g. 1024) to mitigate its misuse as a read primitive.
        """),
    }),

    ('CONFIG_CMD_I2C', True, {
        'summary': 'The i2c console command can be abused to read and tamper with code and data in RAM',
        'impact': SecurityImpact.RD_MEM | SecurityImpact.WR_MEM,

        'description': dedent("""
            Provided physical access to a platform, an attacker can attach a custom I2C peripheral
            device to a bus that acts as a sort of data proxy. This peripheral, in conjunction with
            an enabled I2C bus, allows the console `i2c` command to be abused as an arbitrary
            memory read-write primitive. The following references present this in more detail.

            * <https://research.nccgroup.com/2020/07/22/depthcharge>
            * <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.I2CMemoryReader>
            * <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.I2CMemoryWriter>
        """),

        'recommendation': dedent("""\
            Disable the `i2c` command via `CONFIG_CMD_I2C`.

            Perform I2C device accesses through a dedicated driver. Treat all data retrieved from
            the bus as being untrusted and warranting strict validation.
        """)

    }),

    ('CONFIG_CMD_ITEST', True, {
        'summary': 'The itest console command can be abused as an arbitrary memory read primitive',
        'impact': SecurityImpact.RD_MEM,

        'description': dedent("""\
            The U-Boot console's itest command allows two integer values to be compared using
            operators including `==`, `!=`, `<`, `<=`, `>`, `>=`. It also allows values at
            specified memory locations to be dereference prior to comparison using a C-like
            `*<address>` syntax. As such, this can be used as an arbitrary memory read primitive
            by testing the value at a location against a series of literal integer values.

            Depthcharges implements an memory reader using a `itest` and a binary search:
                <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.ItestMemoryReader>
        """),

        'recommendation': dedent("""
            Remove the `itest` command by disabling CONFIG_CMD_ITEST and perform necessary
            evaluations programmatically. Otherwise, patch the `itest` implementation to
            remove its pointer dereference capability.
        """),
    }),

    ('CONFIG_CMD_GO', True, {
        'summary': 'The go console command allows unsigned code to be executed',
        'impact': SecurityImpact.EXEC,

        'description': dedent("""\
            The U-Boot console's `go` command is designed to support bare metal "stand-alone programs"
            that make use of functions exported by U-Boot's the jump table.  This command calls a
            function at the specified address, assuming a `main()`-like function prototype. It does
            not perform any verification prior to execution.

            As such, inclusion of this command may pose a security risk when included in production
            firmware images that implement a verified/authenticated boot flow.

            References:

            * <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/doc/README.standalone>
        """),

        'recommendation': 'Disable the `go` command via `CONFIG_CMD_GO`.\n'

    }),

    ('CONFIG_CMD_LOADB', True, {
        'summary':
            'The loadb, loadx, and loady console commands can be used to tamper with code/data in RAM',

        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            The `loadb`, `loadx`, and `loady` allow binary files to be loaded into memory via
            kermit, xmodem, amd ymodem, respectively. Although these commands are traditionally
            included in configurations intended for development, their inclusion in production
            firmware can pose a security risk.

            Provided access to the U-Boot console, an attacker can leverage these commands to
            patch running program memory as well as load tampered OS images for later execution. If
            `CONFIG_MTD_NOR_FLASH` is enabled, these commands may also be used to tamper with the
            contents of non-volatile storage.
        """),

        'recommendation': dedent('Disable these console commands via `CONFIG_CMD_LOADB`.\n')
    }),

    ('CONFIG_CMD_LOADS', True, {
        'summary': 'The loads console command can be used to tamper with code/data in RAM or flash',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""
            The `loads` S-Record files to be loaded via a serial interface, decoded, and written
            to a specified memory location. Although this command supports development activities,
            its inclusion in production firmware can pose a security risk.

            Provided access to the U-Boot console, an attacker can leverage this command
            to patch running program memory as well as load tampered OS images
            for later execution. If `CONFIG_MTD_NOR_FLASH` is enabled, it may
            also be used to modify the contents of non-volatile storage.
        """),

        'recommendation': dedent('Disable this console command via `CONFIG_CMD_LOADS`.\n')
    }),

    ('CONFIG_CMD_MEMORY', True, {
        'summary':
            'The memory family of console commands can be abused to read and tamper with RAM contents',

        'impact': SecurityImpact.RD_MEM | SecurityImpact.WR_MEM,

        'description': dedent("""\
            The CONFIG_CMD_MEMORY option enables a family of commands designed to provide
            the operator with the ability to read from and write to arbitrary memory locations.
            While this provide significant utility during engineering and development, their
            inclusion in production builds can undermine security objectives.

            The `mm`, `nm`, `mw`, `cp` command can be abused to arbitrarily read and modify memory.
            Overwriting function pointers (e.g. command handlers) can execution to be redirected to
            attacker-supplied code.

            Note that `mw` and `nm` display current memory contents when prompting for a change,
            allowing them to also be be used as memory read operations.

            The `cp` command can be abused as an arbitrary read by triggering an exception on
            platforms that do not support non-word-aligned accesses and then parsing crash dump
            contents. Alternatively, targeted memory can be copied to an otherwise accessible
            location (e.g. locations containing displayed string contents).

            Although this command does not allow arbitrary data to be supplied directly, it still
            serves as an arbitrary write primitive given that one can copy selected regions of
            memory read by this command, with byte-level granularity.

            The `cmp` command can be abused as an arbitrary read primitive using a binary search
            and region containing attacker controlled values.

            Refer to the Depthcharge memory access abstractions for example implementations.
                <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.CpMemoryWriter>

        """),

        'recommendation': dedent("""\
            Disable memory operation commands by disabling CONFIG_CMD_MEMORY.

            For most production firmware releases, addresses operated on (e.g. image loading
            locations) should either be fixed or obtained from cryptographically authenticated data
            (e.g. FIT images). Consider deviations from this guideline as potential red flags.
        """),
    }),

    ('CONFIG_CMD_MTEST', True, {
        'summary': 'The mtest console command can be abused as an arbitrary memory write primitive',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""
            The U-Boot `mtest` console command performs a simple memory test involving repeated
            writes and readbacks of a specified pattern. If left enabled in production firmware
            images, this command can be leveraged by a local/physical attacker as a means to
            tamper with data and running program memory in RAM, through successive invocations
            with the desired payload word as the pattern and a single iteration.
        """),

        'recommendation': dedent("""\
            Disable this command via `CONFIG_CMD_MTEST`.

            If boot-time memory tests are required, implement these such that a local or physical
            attacker cannot control the specific data and addresses used for the test.
        """),
    }),

    ('CONFIG_CMD_RANDOM', True, {
        'summary': 'The random console command can be abused as an arbitrary memory write primitive',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            The `random` U-Boot console command can be used to write a specified amount of random
            data to target memory location. The command takes an optional seed argument, which
            may be used to set the state of the PRNG. This command is commonly used during
            engineering and development efforts to perform memory test operations that
            involved writing and reading back random patterns.

            Given access to a U-Boot console, an attacker can leverage this command to tamper
            with data and running program memory, one or two bytes at a time. This can be
            achieved by precomputing a lookup table for the PRNG in order to determine the
            seed values required to generate the desired write data.
        """),

        'recommendation': 'Disable this command via CONFIG_CMD_RANDOM.\n',
    }),

    ('CONFIG_CMD_SETEXPR', True, {
        'summary': 'The setexpr console command can be abused as an arbitrary memory read primitive',
        'impact': SecurityImpact.RD_MEM,

        'description': dedent("""\
            The `setexpr` U-Boot console command allows environment variables to be assigned
            based upon the result of an evaluated expression. The supported syntax includes
            a memory dereference option (`*<address>`), which can be leveraged to read
            arbitrary memory contents.

            An example is included in Depthcharge:
                <https://depthcharge.readthedocs.io/en/latest/api/depthcharge.memory.html#depthcharge.memory.SetexprMemoryReader>
        """),

        'recommendation': dedent("""\
            Disable the `setexpr` command via `CONFIG_CMD_SETEXPR`.

            Otherwise, perform evaluations programmatically or patch the
            implementation to remove its pointer dereference functionality.
        """),
    }),

)

# Copy config key into identifier fields
for entry in _BUILTIN_DEFS:
    entry[2]['identifier'] = entry[0]


# TODO: Additional commands whose inclusion in authenticated boot flows can pose risk.
#
# At some point we hit really hit diminishing returns here  As many commands, by design,
# facilitate raw memory/flash/filesystem access.  Flooding the users with noise is
# not productive.
#
# Moving forward, we'll probably want a nicer way to bundle these up into some concise
# lists of configuration commands to consider disabling?
#
#   CONFIG_CMD_FDT
#   CONFIG_CMD_HASH
#   CONFIG_CMD_LOOPW
#   CONFIG_CMD_ONENAND
#   CONFIG_CMD_NAND
#   CONFIG_CMD_EXT* , JFFS, UBIFS, BTRFS, YAFFS etc
#   CONFIG_CMD_EEPROM
#   CONFIG_CMD_BOOTZ, BOOTI
