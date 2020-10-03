#!/usr/bin/env python3
#
# Simple demo script that retrieves a device tree binary and kernel
# from NAND and saves them to files

# (The U-Boot variables used here are specific to a particular platform.)

import os
import traceback

from depthcharge import Console, Depthcharge, log


def validate_requirements(ctx):
    REQUIRED_CMDS = ('nand',)

    log.note('Checking for required target commands.')
    cmds = ctx.commands()
    for cmd in REQUIRED_CMDS:
        if cmd not in cmds:
            msg = 'Command not present in target environment: ' + cmd
            raise ValueError(msg)

    REQUIRED_VARS = ('loadaddr',
                     'dtbimage', 'dtb_offset', 'dtb_size',
                     'image', 'kernel_offset', 'kernel_size')

    log.note('Checking for required target environment variables.')
    env = ctx.environment()
    for var in REQUIRED_VARS:
        if var not in env:
            msg = 'Variable not present in target environment: ' + var
            raise ValueError(msg)

    return env


def read_nand_to_file(ctx, filename: str, name: str,
                      load_addr: int, nand_addr: int, size: int):

    # Copy NAND contents to ${loadaddr}
    cmd = 'nand read 0x{loadaddr:x} 0x{nand_addr:x} 0x{size:x}'
    cmd = cmd.format(loadaddr=load_addr,
                     nand_addr=nand_addr,
                     size=size)

    log.info('Copying ' + name + ' to RAM buffer')
    resp = ctx.send_command(cmd, check=True)
    log.note('Device response: ' + resp.strip())

    log.info('Reading RAM buffer to file: ' + filename)
    ctx.read_memory_to_file(load_addr, size, filename)


if __name__ == '__main__':
    config_file = 'my_device.cfg'
    ctx = None

    try:
        console = Console('/dev/ttyUSB0', baudrate=115200)

        if os.path.exists(config_file):
            ctx = Depthcharge.load(config_file, console, allow_deploy=True, allow_reboot=True)
        else:
            ctx = Depthcharge(console, allow_deploy=True, allow_reboot=True)

        # Check for the presence of commands and variables we'll use
        env = validate_requirements(ctx)

        # While technically unneccessary to convert enviornment variables to
        # integers here, only to then convert them back to strings when used
        # in a command, this affords a chance to confirm they are valid values
        # before we attempt to use them.
        read_nand_to_file(ctx, 'kernel.bin', env['image'],
                          int(env['loadaddr'], 0),
                          int(env['kernel_offset'], 0),
                          int(env['kernel_size'], 0))

        read_nand_to_file(ctx, 'dtb.bin', env['dtbimage'],
                          int(env['loadaddr'], 0),
                          int(env['dtb_offset'], 0),
                          int(env['dtb_size'], 0))

    except Exception as error:
        log.error(str(error))

        # Shown if DEPTHCHARGE_LOG_LEVEL=debug in environment
        log.debug(traceback.format_exc())

    finally:
        # Save gathered information to a device configuration file
        if ctx:
            ctx.save('my_device.cfg')
