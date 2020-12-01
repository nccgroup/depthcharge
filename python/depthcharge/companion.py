# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Support for devices running the Depthcharge "Companion" firmware
"""

import os
import serial

from . import log


class Companion:
    """
    A Companion object represents a handle to a device running the
    Depthcharge Companion Firmware. This firmware implments a proxy by which the Depthcharge host
    library can perform desired operations (e.g. target memory access).

    A connection to the Companion device is established when this class's constructor is invoked.
    The USB-Serial connection to the device is configured using the *device* and *baudrate*
    parameters.

    Additional keyword parameters, listed below, can be used to configure the Companion device
    firmware.

    Currently, the Companion suport is limited to I2C peripheral functionality.
    With some simple additions here and in the firmware, it should be capable of acting as
    a peripheral device on other simple buses (e.g. SPI) as well.
    This API will update along with official additions to the firmware.

    The :py:meth:`get_capabilities()` and :py:meth:`get_version()` methods can be used to
    determine what functionality is supported by the companion device.

    **Constructor Keyword Arguments**

    * *i2c_bus* - I2C bus index within U-Boot environment.
      Corresponds to ``i2c dev [n]`` console commands. Defaults to *i2c_bus=0*.

    * *i2c_addr* - I2C address that device should respond to.
      May be set later via :py:meth:`set_i2c_addr()`. Default: *i2c_bus=0x78* (A reserved address)

    * *i2c_speed* - I2C bus speed, in Hz. May be set later via :py:meth:`set_i2c_speed()`.
      Default: *i2c_speed=100000*

    """

    _cmd = {
        'get_version':          0x00,
        'get_capabilities':     0x01,

        'i2c_get_addr':         0x08,
        'i2c_set_addr':         0x09,
        'i2c_get_speed':        0x0a,
        'i2c_set_speed':        0x0b,
        'i2c_get_subaddr_len':  0x0c,
        'i2c_set_subaddr_len':  0x0d,
        'i2c_get_mode_flags':   0x0e,
        'i2c_set_mode_flags':   0x0f,
        'i2c_set_read_buffer':  0x10,
        'i2c_get_write_buffer': 0x11,
    }

    _status_ok = b'\00'

    def __init__(self, device='/dev/ttyACM0', baudrate=115200, **kwargs):
        self._i2c_addr  = kwargs.pop('i2c_addr', 0x78)
        self._i2c_speed = kwargs.pop('i2c_speed', 100_000)
        self._i2c_bus   = kwargs.pop('i2c_bus', 0)

        if not isinstance(self._i2c_addr, int):
            raise TypeError('Invalid I2C address: ' + str(self._i2c_addr))

        if not 0 <= self._i2c_addr <= 0xff:
            raise ValueError('Invalid I2C address: ' + str(self._i2c_addr))

        if not isinstance(self._i2c_speed, int):
            raise TypeError('Invalid I2C speed: ' + str(self._i2c_speed))

        if self._i2c_speed <= 0:
            raise ValueError('Invalid I2C speed: ' + str(self._i2c_speed))

        if not isinstance(self._i2c_bus, int):
            raise TypeError('Invalid I2C bus: ' + str(self._i2c_bus))

        if self._i2c_speed < 0:
            raise ValueError('Invalid I2C bus: ' + str(self._i2c_bus))

        self._ser = serial.Serial(port=device, baudrate=baudrate, **kwargs)

        #  These two items are populated by the following calls
        self._fw_version = None
        self._fw_capabilities = None

        self.firmware_verison(cached=False)
        self.firmware_capabilities(cached=False)

        dbg_msg = 'Opened Companion @ {:s}: Firmware Version {:s}. Capabilities:'
        dbg_msg = dbg_msg.format(device, self._fw_version)
        for cap in self._fw_capabilities:
            have_cap = 'Yes' if self._fw_capabilities[cap] else 'No'
            dbg_msg += os.linesep + ' ' * 8 + cap + ': ' + have_cap

        log.note(dbg_msg)

        if self._fw_capabilities.get('i2c_periph', False):
            self.set_i2c_addr(self._i2c_addr)
            self.set_i2c_speed(self._i2c_speed)

    def firmware_verison(self, cached=True) -> str:
        """
        Retrieve firmware version from device.

        If *cached=True*, a previously read value will be returned.
        Otherwise it will be read from the Companion device.
        """
        if cached and self._fw_version is not None:
            return self._fw_version

        resp = self.send_cmd('get_version', b'', 4)
        version = '{:d}.{:d}.{:d}'.format(resp[0], resp[1], resp[2])
        extra = resp[3]

        if extra != 0:
            version += '-{:02d}'.format(extra)

        self._fw_version = version
        return version

    def firmware_capabilities(self, cached=True) -> dict:
        """
        Query the companion firmware capabilities and return a dict indicating
        which features are present.

        If *cached=True*, previously obtained capabilities will be returned.
        Otherwise they will be read from the Companion device.

        Keys represent capabilities and the corresponding boolean value denotes
        whether or not that capability is present on the Companion device.
        """
        if cached and self._fw_capabilities is not None:
            return self._fw_capabilities

        caps = {}
        resp = self.send_cmd('get_capabilities', b'', 4)
        capraw = int.from_bytes(resp, 'little')

        caps['i2c_periph'] = (capraw & (1 << 0)) != 0
        caps['spi_periph'] = (capraw & (1 << 1)) != 0

        self._fw_capabilities = caps
        return caps

    def _require_i2c_support(self):
        if not self._fw_capabilities['i2c_periph']:
            raise NotImplementedError('This firmware does not implement I2C peripheral functionality')

    def i2c_bus(self) -> int:
        """
        Zero-indexed I2C bus number the companion device is associated with.
        """
        return self._i2c_bus

    def i2c_addr(self, cached=True) -> int:
        """
        Retrieve the I2C device address that the Companion responds to.

        If *cached=True*, the value stored host-side will be returned.
        Otherwise it will be read from the device.
        """
        self._require_i2c_support()

        if cached and self._i2c_addr is not None:
            return self._i2c_addr

        resp = self.send_cmd('i2c_get_addr', b'', 1)
        self._i2c_addr = resp[0]
        return self._i2c_addr

    def set_i2c_addr(self, addr: int):
        """
        Set the I2C device address that the Depthcharge Companion firmware
        responds to. Valid range: 0x00 - 0x7f
        """
        self._require_i2c_support()

        if addr not in range(0, 0x80):
            raise ValueError('Invalid address: 0x{:02x}'.format(addr))

        log.note('Setting Companion I2C device address to 0x{:02x}'.format(addr))
        self.send_cmd('i2c_set_addr', addr.to_bytes(1, 'big'), 1, self._status_ok)

        self._i2c_addr = addr

    def i2c_speed(self, cached=True) -> int:
        """
        Retrieve the I2C bus clock rate the device is configured for, in Hz.

        If *cached=True*, the value stored host-side will be returned.
        Otherwise it will be read from the device.
        """
        self._require_i2c_support()

        if cached and self._i2c_speed is not None:
            return self._i2c_speed

        speed = self.send_cmd('i2c_get_speed', b'', 4)
        self._i2c_speed = int.from_bytes(speed, 'little')
        return self._i2c_speed

    def set_i2c_speed(self, speed: int) -> int:
        """
        Configure the device for the specified I2C bus clock rate.

        Refer to reference manual of the device you're running the Depthcharge
        Companion firmware on for supported bus clock speeds.
        """
        self._require_i2c_support()
        if speed not in range(1, (1 << 32)):
            err = 'Speed outside of supported range: {:d} Hz'.format(speed)
            raise ValueError(err)

        log.note('Setting Companion I2C bus speed to {:d} Hz'.format(speed))

        self.send_cmd('i2c_set_speed', speed.to_bytes(4, 'little'), 1, self._status_ok)
        self._i2c_speed = speed

    def i2c_write_buffer(self) -> bytes:
        """
        Retrieve the contents of the I2C data write buffer

        This represents data written by a target SoC (bus controller) to our
        peripheral device. Within the context U-Boot shenanigans, this is
        data retrieved from the memory space of the target SoC.

        Different firmware implementations are free to use either separate read
        and write buffers, as well as a single, shared buffer.  Do not assume
        that this call will return the same data that was written by a
        preceding call to :py:meth:`set_i2c_read_buffer()`.
        """
        self._require_i2c_support()
        return self.send_cmd('i2c_get_write_buffer', b'', range(0, 33))

    def set_i2c_read_buffer(self, data: bytes):
        """
        Set up the contents of the I2C data read buffer.

        This is the data that the target SoC (bus controller) will read
        from our peripheral device into its memory space.

        Different firmware implementations are free to use either separate read
        and write buffers, as well as a single, shared buffer.  Do not assume
        that :py:meth:`i2c_write_buffer()` will return the value written by this call.
        """
        self._require_i2c_support()

        # Although enforced silently in firmware, give feedback
        # to the user here.
        if len(data) > 32:
            raise ValueError('I2C data buffer exceeds maximum size of 32 bytes')

        self.send_cmd('i2c_set_read_buffer', data, 1, self._status_ok)

    def send_cmd(self, cmd_str: str, data: bytes,
                 expected_resp_size: int = -1, expected_resp=None) -> bytes:
        """
        Send a raw command to the Companion device and return its response.
        This can be used when adding new features and custom functionality to the Companion
        firmware.

        If non-default values for *expected_resp* and *expected_resp_size*, an:py:exc:`IOError`
        will be raised if the device's resonse contents or size (respectively) do not match the
        provided expected values.

        :py:exc:`ValueError` and :py:exc:`TypeError` exceptions are raised when invalid
        arguments are provided.
        """
        try:
            cmd = self._cmd[cmd_str.lower()]
        except KeyError:
            raise ValueError('Invalid command: ' + cmd_str)

        cmd = int(cmd).to_bytes(1, 'big')
        if len(data) > 64:
            raise ValueError(cmd_str + ' / Data payload is too large.')

        size = len(data).to_bytes(1, 'big')

        request = cmd + size + data
        self._ser.write(request)

        header = self._ser.read(2)

        if header[0] != cmd[0]:
            err = cmd_str + ' / Sent cmd=0x{:02}, got response for cmd=0x{:02}'
            raise IOError(cmd, err.format(header[0]))

        size = header[1]
        if size > 64:
            err = cmd_str + ' / Received bogus payload size from device: 0x{:02x}'
            raise IOError(err.format(size))

        if expected_resp is not None:
            if isinstance(expected_resp_size, int)  and size != expected_resp_size:
                err = cmd_str + ' / Expected {:d}-byte response, got {:d}-byte payload.'
                raise IOError(err.format(expected_resp_size, size))

            if isinstance(expected_resp_size, range) and size not in expected_resp_size:
                err = cmd_str + ' / Expected {:d} to {:d} byte response, got {:d}-byte payload.'
                raise IOError(err.format(expected_resp_size.start, expected_resp_size.stop - 1, size))

        data = self._ser.read(size)
        if len(data) != size:
            err = cmd_str + ' / Requested {:d} bytes, got {:d}'
            raise IOError(err.format(len(data), size))

        if expected_resp is not None and expected_resp != data:
            err = cmd_str + ' / Expected response = {:s}, got {:s}'
            raise IOError(err.format(expected_resp.hex(), data.hex()))

        return data

    def close(self):
        """
        Close the connection to the Companion device.
        No further instance methods should be invoked following this call.
        """
        self._ser.close()
