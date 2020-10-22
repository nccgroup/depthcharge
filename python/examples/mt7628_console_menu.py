#!/usr/bin/env python3
"""
This example demonstrates how to use the Console API to automate
some device interaction before the Depthcharge API or console
scripts are used.

The target device for this example is an MediaTek MT7628N-based
RAVPower WP-WD008 "Filehub wireless travel router".

Below is an excerpt of the console menu presented before the
U-Boot shell is available.

-----------------------------------------------------------------------------

  U-Boot 1.1.3 (Sep 17 2018 - 18:22:09)

  version:1.0.5
  Board: Ralink APSoC DRAM:  64 MB
  relocate_code Pointer at: 83fac000
  flash manufacture id: c8, device id 40 17
  find flash: GD25Q64B
  Initialize GPIO as flow.
  ljd GPIO as flow.
  *** Warning - bad CRC, using default environment

  ============================================
  Ralink UBoot Version: 4.3.0.0
  --------------------------------------------
  ASIC 7628_MP (Port5<->None)
  DRAM component: 512 Mbits DDR, width 16
  DRAM bus: 16 bit
  Total memory: 64 MBytes
  Flash component: 8 MBytes NOR Flash
  Date:Sep 17 2018  Time:18:22:09
  ============================================
  icache: sets:512, ways:4, linesz:32 ,total:65536
  dcache: sets:256, ways:4, linesz:32 ,total:32768

   ##### The CPU freq = 575 MHZ ####
   estimate memory size =64 Mbytes
  Initialize vs configure module
  Initialize GPIO as flow.
  ljd GPIO as flow.

  Input i key to enter menu: i

  RESET MT7628 PHY!!!!!!
  Initialize GPIO as flow.
  ljd GPIO as flow.
  Enter menu option

  |-------------------------------|
  |         IOVST MAIN MENU       |
  |-------------------------------|
  | 6 Test USB                    |
  | 8 Test ethernet               |
  | B Boot the Kernel             |
  | I Test system params          |
  | U SPIFlash Upgrade            |
  | T SMT test program            |
  | X Update the license          |
  | R Reboot                      |
  | Z Enter Command Line Interface|
  |-------------------------------|
   Please input test item:Z

  MT7628 #

"""

import sys

from depthcharge import Console, log


def read_loop(console):
    state = 'AWAIT_PROMPT'

    log.info('Waiting for menu. Please power on the target.')
    while True:
        line = console.readline()
        if not line:
            continue

        line = line.strip()
        print(line)

        if state == 'AWAIT_PROMPT':
            if 'Input i key to enter' in line:
                console.write('i')
                state = 'SELECT_CLI'
        elif state == 'SELECT_CLI':
            if 'Please input test item' in line:
                console.write('Z')
                console.write('\x03')  # Ctrl-C
                state = 'AWAIT_UBOOT'
        elif state == 'AWAIT_UBOOT':
            if 'MT7628 #' in line:
                state = 'DONE'
        elif state == 'DONE':
            log.info('U-Boot prompt detected!')
            return


if __name__ == '__main__':

    if len(sys.argv) < 2 or '-h' in sys.argv or '--help' in sys.argv:
        print('MT7628 (MediaTek/Ralink) boot menu example')
        print('Usage: <serial port> [baud rate]')
        print('Baud rate defaults to 57600.')
        print()
        sys.exit(1 if len(sys.argv) < 1 else 0)

    uart_device = sys.argv[1]
    try:
        baud_rate = sys.argv[2]
        print(baud_rate)
    except IndexError:
        baud_rate = '57600'

    console = Console(uart_device, baudrate=baud_rate)
    log.note('Opened ' + uart_device + ': ' + baud_rate)

    try:
        read_loop(console)
    except KeyboardInterrupt:
        print('\r', end='')  # Overwrite "^C" on terminal
        log.warning('Interrupted! Exiting.')
        sys.exit(1)

    msg = (
        'You may now run the following command to inspect the platform.\n'
        '  depthcharge-inspect -i {:s}:{:s} -c rp-wd008.cfg [-m term]'
    )

    log.info(msg.format(uart_device, baud_rate))
