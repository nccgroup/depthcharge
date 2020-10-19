#!/usr/bin/env python3
import os
import re

from depthcharge import Depthcharge, Console, OperationFailed, log
from depthcharge.monitor import Monitor

def setup():
    # Optional: Launch a console monitor so we can
    # keep an eye on the underlying operations. We
    # use a terminal-based monitor here.
    mon = Monitor.create('term')

    # Connect to the target device's serial port
    console = Console('/dev/ttyUSB0', baudrate=115200, monitor=mon)

    # Create and return an initialized Depthcharge context
    return Depthcharge(console, arch='arm', allow_deploy=True, allow_reboot=True)

    # Alternatively, create it from a previously created device config file
    # This will allow Depthcharge to skip any "inspection" steps.
    #return Depthcharge.load('my_device.cfg', console)

def get_buses(ctx):
    buses = []

    resp = ctx.send_command('i2c bus')
    for line in resp.splitlines():
        match = re.match(r'Bus (\d+)', line)
        if match:
            busno = int(match.group(1))
            log.note('Available: Bus {:d}'.format(busno))
            buses.append(busno)

    return buses

def find_devices(ctx, buses):
    results = []
    for bus in buses:
        log.note('Probing bus {:d}'.format(bus))
        try:

            cmd = 'i2c dev {:d}'.format(bus)
            # Raise an exception on error via check=True
            ctx.send_command(cmd, check=True)

            # This may fail for buses (or pinmux settings) that are configured
            # appropriately. Thus, we drop check=True and just look results
            resp = ctx.send_command('i2c probe')


            match = re.match(r'Valid chip addresses: ([0-9a-fA-F\t ]+)', resp)
            if not match:
                # A failing bus will spew failures for a while. Keep trying
                # to interrupt it (Ctrl-C) until we know we're back at a prompt.
                log.warning('No devices or bus failing. Waiting for prompt.')
                ctx.interrupt(timeout=120)
                continue

            for addr in match.group(1).split():
                addr = int(addr, 16)
                log.info('Found device: Bus={:d}, Address=0x{:02x}'.format(bus, addr))
                results.append((bus, addr))

        except OperationFailed as error:
            log.error('Command failed: ' + cmd + os.linesep + str(error))

    return results

if __name__ == '__main__':
    # Attach to the device and get a Depthcharge context
    ctx = setup()

    log.info('Identifying available I2C buses.')
    buses = get_buses(ctx)

    log.info('Probing I2C buses for devices. This may take some time.')
    # We'll just log results as we go, rather than use the return value
    find_devices(ctx, buses)
