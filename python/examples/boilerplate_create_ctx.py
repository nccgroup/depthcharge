#!/usr/bin/env python3
import traceback
from depthcharge import Console, Depthcharge, log

ctx = None

try:
    console = Console('/dev/ttyUSB0', baudrate=115200)
    ctx = Depthcharge(console)

    # Comment out the above ctx creation and uncomment the following one in
    # order to possibly make more operations available to Depthcharge by allowing
    # it to deploy executable payloads to RAM and reboot/crash the platform.
    #ctx = Depthcharge(console, allow_deploy=True, allow_reboot=True)

    # Perform actions here via API calls on ctx handle

except Exception as error:
    log.error(str(error))

    # Shown if DEPTHCHARGE_LOG_LEVEL=debug in environment
    log.debug(traceback.format_exc())

finally:
    # Save gathered information to a device configuration file
    if ctx:
        ctx.save('my_device.cfg')
