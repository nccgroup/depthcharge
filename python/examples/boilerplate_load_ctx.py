#!/usr/bin/env python3
import traceback
from depthcharge import Console, Depthcharge, log

ctx = None

try:
    console = Console('/dev/ttyUSB0', baudrate=115200)
    ctx = Depthcharge.load('my_device.cfg', console)

    # Comment out the above ctx creation and uncomment the following one in
    # order to possibly make more operations available to Depthcharge by allowing
    # it to deploy executable payloads to RAM and reboot/crash the platform.
    #ctx = Depthcharge(console, allow_deploy=True, allow_reboot=True)

    # Perform actions here

except Exception as error:
    log.error(str(error))

    # Shown if DEPTHCHARGE_LOG_LEVEL=debug in environment
    log.debug(traceback.format_exc())

finally:
    # Save any updates or new information to the device config
    if ctx:
        ctx.save('my_device.cfg')
