# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements I2CMemoryReader and I2CMemoryWriter
"""

import re

from .reader import MemoryReader
from .writer import MemoryWriter

from .. import log
from ..operation import Operation


def _get_i2c_bus_state(ctx) -> tuple:
    """
    Query and return the current I2C (bus #, speed).
    """

    resp = ctx.send_command('i2c dev')
    match = re.search('bus is (?P<busno>[0-9]+)', resp)
    if match:
        busno = int(match.group('busno'))
    else:
        busno = None
        log.error('Failed to determine current I2C bus')
        log.debug('Device replied with: ' + resp)

    resp = ctx.send_command('i2c speed')
    match = re.search('speed=(?P<speed>[0-9]+)', resp)
    if match:
        speed = int(match.group('speed'))
    else:
        speed = None
        log.error('Failed to determine current I2C bus speed')
        log.debug('Device replied with: ' + resp)

    return (busno, speed)


def _restore_i2c_bus_state(ctx, state: tuple):
    """
    Restore previously saved I2C bus configuration.
    """

    busno, speed = state

    if speed is not None:
        ctx.send_command('i2c speed {:d}'.format(speed), check=True)

    if busno is not None:
        ctx.send_command('i2c dev  {:d}'.format(busno), check=True)


class I2CMemoryReader(MemoryReader):
    """
    The I2CMemoryReader leverages a Depthcharge :py:class:`~depthcharge.Companion` device to
    achieve a memory read operation using U-Boot's `i2c write` console command.

    As shown below, this command writes data from the SoC memory space to a peripheral device on a
    platform's I2C bus. By directing the I2C write to a device that we control (and have attached to
    the bus), these memory contents can be relayed back to the host-side Depthcharge code.

    .. image:: ../../images/i2c-read.png
        :align: center

    """

    _required = {
        'companion': True,
        'commands': ['i2c']
    }

    _usage_err = 'U-Boot responded to I2C command with usage text.\n' + \
                 ' ' * 6 + \
                 'Does it not support the subcommands we are using? ' + \
                 '(See TODO in memreader.py, I2CReader)'

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)
        self._backup_state = (None, None)

    # TODO - Need to check version or "i2c help" output to avoid exploding on older versions.
    #
    # We need the following subcommands...
    #   dev     added in U-Boot-1_2_0 (~2006-11) @ bb99ad6d8257bf828f150d40f507b30d80a4a7ae
    #   read    added in 2010-06-rc1 @ 652e53546b23c25f80756287eaf607b713afdc87
    #   write   added in 2013.01-rc1 @ ff5d2dce1e8b24e9f4d85db3906c5d2e25b0cedf
    #    " -s   added in 2015.04-rc3 @ ed16f14689b98c1ec98c9f30b92b8edea9d2d60c
    #
    # v0.1.0 of the companion firmware currently requires the bulk write (-s) operation
    #
    def _validate_response(self, resp, expected=''):
        resp = resp.strip()
        if resp != expected:
            if 'Usage:' in resp:
                raise ValueError(self._usage_err)

            raise ValueError('Unexpected response:\n' + resp)

    @classmethod
    def rank(cls, **kwargs):
        # Requires companion device and is very slow
        return 2

    def _setup(self, addr, size):
        self._backup_state = _get_i2c_bus_state(self._ctx)

        bus_num = self._ctx.companion.i2c_bus()
        cmd = 'i2c dev {:d}'.format(bus_num)
        resp = self._ctx.send_command(cmd)

        # This has been the command output since at least 2011.
        # Should be good enough to use as a success check
        expected = 'Setting bus to {:d}'.format(bus_num)
        self._validate_response(resp, expected)

        bus_speed = self._ctx.companion.i2c_speed()
        cmd = 'i2c speed {:d}'.format(bus_speed)
        resp = self._ctx.send_command(cmd)
        expected = 'Setting bus speed to {:d} Hz'.format(bus_speed)
        self._validate_response(resp, expected)

    def _teardown(self):
        _restore_i2c_bus_state(self._ctx, self._backup_state)

    # A read is performed by having U-Boot write the contents
    # of a memory location to our fake I2C peripheral .
    def _read(self, addr: int, size: int, handle_data):

        i2c_addr = self._ctx.companion.i2c_addr()
        fmt = 'i2c write 0x{:08x} 0x{:02x} 0 0x{:02x} -s'

        while size > 0:
            # FIXME: want 32, but we're losing a byte to a subaddress
            #        and picking up a NACK? Seems like the Kinetis TwoWire
            #        is hittin a 32-bit limit, perhaps to conform to some
            #        implicit Arduino API limitations re: 32-byte buffers.
            to_read = 31 if size > 31 else size
            cmd = fmt.format(addr, i2c_addr, to_read)
            resp = self._ctx.send_command(cmd)
            self._validate_response(resp)

            data = self._ctx.companion.i2c_write_buffer()
            if len(data) != to_read and len(data) != (to_read + 1):
                # FIXME: +1 is an extra byte coming in on the I2C stop
                # condition or our NACK?
                err = 'Expected {:d} bytes of data, got {:d}'
                raise IOError(err.format(to_read, len(data)))

            # Neeed to trim extra junk per above
            handle_data(data[0:to_read])

            addr += to_read
            size -= to_read


class I2CMemoryWriter(MemoryWriter):
    """
    The I2CMemoryWriter operates in concert with a Depthcharge :py:class:`~depthcharge.Companion` device to
    achieve a memory write operation using U-Boot's `i2c read` console command. The following
    diagram depicts its high-level operation.


    The `i2c read` command copies data retrieved from a peripheral device into a specified SoC
    memory region. Because we control what the Companion device will respond to read requests with,
    we can effective deploy arbitrary payloads to selected addresses in the target SoC's memory space.

    .. image:: ../../images/i2c-write.png
        :align: center

    """

    _required = {
        'companion': True,
        'commands': ['i2c']
    }

    _usage_err = 'U-Boot responded to I2C command with usage text.\n' + \
                 ' ' * 6 + \
                 'Does it not support the subcommands we are using? ' + \
                 '(See TODO in memwriter.py, I2CWriter)'

    @classmethod
    def rank(cls, **kwargs):
        # Requires companion device and is very slow
        return 2

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

        # This is dictacted by Companion firmware restrictions,
        # courtesy of (arbitrary?) Arduino library limitations.
        self._block_size = 32

        self._backup_state = (None, None)

    def _validate_response(self, resp, expected=''):
        resp = resp.strip()
        if resp != expected:
            if 'Usage:' in resp:
                raise ValueError(self._usage_err)

            raise ValueError('Unexpected response:\n' + resp)

    def _setup(self, addr, data):
        self._backup_state = _get_i2c_bus_state(self._ctx)

        bus_num = self._ctx.companion.i2c_bus()
        cmd = 'i2c dev {:d}'.format(bus_num)
        resp = self._ctx.send_command(cmd)

        # This has been the command output since at least 2011.
        # Should be good enough to use as a success check
        expected = 'Setting bus to {:d}'.format(bus_num)
        self._validate_response(resp, expected)

        bus_speed = self._ctx.companion.i2c_speed()
        cmd = 'i2c speed {:d}'.format(bus_speed)
        resp = self._ctx.send_command(cmd)
        expected = 'Setting bus speed to {:d} Hz'.format(bus_speed)
        self._validate_response(resp, expected)

    def _teardown(self):
        _restore_i2c_bus_state(self._ctx, self._backup_state)

    # A memory write is performed by reading out payload from out
    # companion device, into the target's memory space
    def _write(self, addr: int, data: bytes, **kwargs):
        i2c_addr = self._ctx.companion.i2c_addr()
        fmt = 'i2c read 0x{:02x} 0 0x{:02x} 0x{:08x}'
        to_write = len(data)

        self._ctx.companion.set_i2c_read_buffer(data)

        cmd = fmt.format(i2c_addr, to_write, addr)
        resp = self._ctx.send_command(cmd)
        self._validate_response(resp)


# Register declared Operations
Operation.register(I2CMemoryReader, I2CMemoryWriter)
