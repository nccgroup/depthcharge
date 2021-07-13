# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Functionality for interacting with a U-Boot console.
"""

import os
import re
import time

import serial

from . import log
from .monitor import Monitor
from .string import str_to_property_keyval


class Console:
    """
    This class encapsulates a serial console interface and provides higher level
    functionality for interacting with a U-Boot console.

    The *device* argument are required to configure the serial console connection.
    Default, but not necessarily correct, values will be used if these are not provided.
    Note that the baudrate can either be specified as part of the *device* string
    or as an additional *baudrate=<value>* keyword argument.

    The *prompt* parameter specifies the U-Boot prompt string that should
    be used to detect when the interactive console is ready to accept input.
    If left as ``None``, Depthcharge will attempt to later determine this using
    the :py:meth:`discover_prompt()` method.

    If you wish to view or capture data sent and received using this console,
    provide a :py:class:`~depthcharge.monitor.Monitor` instance as the *monitor* parameter.

    By default, the underlying serial console is initialized with a 150 ms timeout.
    Lowering this will speed up some operations (e.g. dumping memory via console
    operations), but setting it too low might cause Depthcharge to time out before a
    device has had a chance to finish responding with output from an operation.

    The timeout be changed by providing a float value (in seconds) as a *timeout* keyword argument
    or by setting a *DEPTHCHARGE_CONSOLE_TIMEOUT* environment variable. The latter takes precedence.

    On some systems, you may find that sending too much data at a U-Boot console
    will cause the target device's UART FIFO to fill, dropping characters. You
    can find an example of this here: <https://twitter.com/sz_jynik/status/1414989128245067780>

    If you wish to introduce intra-character delay to console input, provide an *intrachar* keyword
    argument or DEPTHCHARGE_CONSOLE_INTRACHAR environment variable. (The latter takes presence.)
    This floating point value, in seconds, is the minimum amount of time that shall be
    inserted between successive bytes. Realistically, the value will be larger because
    this mode of operation will send each byte with a single write() + flush(),
    incurring non-negligible overhead.  You may set a value of 0 to incur only this
    implicit overhead, with no additional sleep()-based delay.
    """
    def __init__(self, device='/dev/ttyUSB0:115200', prompt=None, monitor=None, **kwargs):

        if 'timeout' not in kwargs:
            kwargs['timeout'] = 0.150

        timeout_env = os.getenv('DEPTHCHARGE_CONSOLE_TIMEOUT')
        if timeout_env is not None:
            timeout_env = float(timeout_env)
            kwargs['timeout'] = timeout_env

        self._intrachar = None
        if 'intrachar' in kwargs:
            self._intrachar = kwargs.pop('intrachar')

        intrachar_env = os.getenv('DEPTHCHARGE_CONSOLE_INTRACHAR')
        if intrachar_env is not None:
            self._intrachar = float(intrachar_env)

        # Parse device string and merge its entries into the provided kwargs,
        # giving priority to the items in the device string.
        device, device_args = str_to_property_keyval(device)
        for arg in list(device_args.keys()):

            # Special case - baudrate allowed without 'baudrate=' syntax
            # for convenience.
            if isinstance(device_args[arg], bool):
                try:
                    kwargs['baudrate'] = int(arg)
                    device_args.pop(arg)
                except ValueError:
                    pass

            else:
                try:
                    kwargs[arg] = int(device_args[arg])
                except ValueError:
                    kwargs[arg] = device_args[arg]

        # If, when Depthcharge is trying to detect a prompt at the console,
        # we see a match for this regular expression, we will enter a
        # loop in which we attempt to reboot the platform.
        #
        # It's a bit of "undocumented magic" that I use myself, but am not
        # really sure about whether other people will find it useful.
        #
        # TODO: Document this as an opt-in behavior in API docs.
        #       (More feedback and mulling over this required.)
        #
        self._reboot_re = kwargs.pop('reboot_re', None)
        self._reboot_cmd = kwargs.pop('reboot_cmd', 'reboot || shutdown -r now')

        if self._reboot_re:
            self._reboot_re = re.compile(self._reboot_re)
            msg = (
                'Using regular expression for reboot match trigger: '
                + self._reboot_re.pattern + '\n'
                + '    Will use this command: ' + self._reboot_cmd
            )
            log.note(msg)

        # We're going to pass this off to the Serial constructor in a moment.
        if 'baudrate' not in kwargs:
            self._baudrate = 115200
            kwargs['baudrate'] = self._baudrate
        else:
            self._baudrate = kwargs.get('baudrate')

        # Store Serial constructor arguments for later reopen()
        self._dev = device
        self._kwargs = kwargs

        self._ser = serial.Serial(port=self._dev, **kwargs)
        self._encoding = 'latin-1'

        self.monitor = monitor if monitor is not None else Monitor()
        self.prompt  = prompt

        self.interrupt_ind = '<INTERRUPT>'

    @property
    def device(self):
        """
        Device or interface used to communicate with console on target device.
        """
        return self._dev

    @property
    def baudrate(self):
        """
        Serial console's baud rate configuration.
        """
        return self._baudrate

    def send_command(self, cmd: str, read_response=True) -> str:
        """
        Send the provided command (`cmd`) to the attached U-Boot console.

        If `read_response` is `True`, the response is returned. Otherwise,
        `None` is returned and no attempt to read the response data is made.

        If one does not plan to use the response, keep `read_response`
        set to `True` and simply ignore the return value; this will ensure
        response data is removed from underlying buffers.
        """
        self._ser.flush()

        if not cmd.endswith('\n'):
            cmd += '\n'

        self.write(cmd)
        self._ser.flush()

        if read_response:
            resp = self.read()
            resp = self.strip_echoed_input(cmd, resp)

            # We expect this
            if resp.endswith(self.prompt):
                resp = resp[:-len(self.prompt)]

            return resp

        return None

    def interrupt(self, interrupt_str='\x03', timeout=30.0):
        """
        Attempt to interrupt U-Boot and retrieve a console prompt.

        By default, the character associated traditionally with Ctrl-C is sent to interrupt U-Boot.

        If trying to do this at boot-time (within the autoboot grace period),
        note that a specific "Stop String" may be required.

        Refer to U-Boot's doc/README.autoboot regarding the
        `CONFIG_AUTOBOOT_KEYED` and `CONFIG_AUTOBOOT_STOP_STR` configuration
        options for more information.
        """
        self._ser.flush()

        if self.prompt is None or len(self.prompt) == 0:
            log.note('No user-specified prompt provided. Attempting to determine this.')
            return self.discover_prompt(interrupt_str, timeout)

        ret = ''
        t_start = time.time()
        now = t_start
        while (now - t_start) < timeout:
            self.write(interrupt_str)
            self._ser.flush()

            response = self.read()
            ret += response
            if response.endswith(self.prompt):
                return ret

            now = time.time()
        raise TimeoutError('Timed out while attempting to return to U-Boot console prompt')

    def discover_prompt(self, interrupt_str='\x03', timeout=30.0, count=10):
        """
        Attempt to deduce the U-Boot prompt string by repeatedly attempting to interrupt its
        execution by sending *interrupt_str* until *count* consecutive prompt strings are observed.
        """
        t_start = time.time()
        now = t_start

        ret = ''
        candidate = ''
        candidate_count = 0

        while (now - t_start) < timeout:
            self.write(interrupt_str)
            self._ser.flush()

            response = self.read().replace(self.interrupt_ind, '')
            ret += response
            response = response.lstrip().splitlines()

            # We want to see the same thing repeated <count> times,
            # with no other output emitted in between
            if len(response) != 1:
                candidate = ''
                candidate_count = 0
                continue
            response = response[0]

            if candidate in ('', candidate):
                candidate = response
                candidate_count += 1

                if candidate_count >= count:
                    # Is this prompt indicative of a state we don't want to be in?
                    # (e.g. Linux shell)
                    #
                    # If so, attempt to issue 'reboot' command.
                    response_stripped = response.strip()
                    if self._reboot_re is not None and self._reboot_re.match(response_stripped):
                        candidate = ''
                        candidate_count = 0
                        msg = 'Attempting reboot. Matched reboot regex: ' + response_stripped
                        log.note(msg)
                        self.write(self._reboot_cmd + '\n')
                        self._ser.flush()

                    if candidate_count > 0:
                        log.note('Identified prompt: ' + response)
                        self.prompt = response
                        return ret
            else:
                candidate = ''
                candidate_count = 0

            now = time.time()

        raise TimeoutError('Timed out while attempting to identify U-Boot console prompt')

    def readline(self, update_monitor=True) -> str:
        """
        Read and return one line from the serial console.

        If `update_monitor` is `True`, this data is recorded by any attached
        :py:class:`~depthcharge.monitor.Monitor`.
        """
        data = self._ser.readline()
        if update_monitor:
            self.monitor.read(data)
        return data.decode(self._encoding)

    def read(self, readlen=64, update_monitor=True) -> str:
        """
        Read the specified number of characters (`readlen`) from the serial console.

        If `update_monitor` is `True`, this data is recorded by any attached
        :py:class:`~depthcharge.monitor.Monitor`.
        """
        raw_data = self.read_raw(readlen, update_monitor=update_monitor)
        ret_str  = raw_data.decode(self._encoding)
        return ret_str.replace('\r\n', '\n')

    def read_raw(self, readlen=64, update_monitor=True) -> bytes:
        """
        Read and return `readlen` bytes of raw data from the serial console.

        If `update_monitor` is `True`, this data is recorded by any attached
        :py:class:`~depthcharge.monitor.Monitor`.
        """
        ret = b''
        data = None

        # serial.Serial.read_until() enforces the read timeout at the
        # granularity of the entire payload, rather than a read() timeout.
        # This causes us to time out when reading large responses.
        while data != b'':
            data = self._ser.read(readlen)
            ret += data

        if update_monitor:
            self.monitor.read(ret)

        return ret

    def write(self, data: str, update_monitor=True):
        """
        Write the provided string (`data)` to the serial console.

        If `update_monitor` is `True`, this data is recorded by any attached
        :py:class:`~depthcharge.monitor.Monitor`.
        """
        self.write_raw(data.encode(self._encoding), update_monitor=update_monitor)

    def write_raw(self, data: bytes, update_monitor=True):
        """
        Write the provided raw data bytes to the serial console.

        If `update_monitor` is `True`, this data is recorded by any attached
        :py:class:`~depthcharge.monitor.Monitor`.
        """
        if self._intrachar is None:
            self._ser.write(data)
        else:
            for b in data:
                # A value of 0 will induce only the overhead of a per-byte
                # write() + flush()... which is quite substantial.
                if self._intrachar > 0:
                    time.sleep(self._intrachar)

                self._ser.write(b.to_bytes(1, 'little'))
                self._ser.flush()

        if update_monitor:
            self.monitor.write(data)

    def close(self, close_monitor=True):
        """
        Close the serial console connection.

        After this method is called, no further operations on this object
        should be perform, with the exception of :py:meth:`reopen()`.

        If *close_monitor* is ``True`` and a monitor is attached,
        it will be closed as well.
        """
        if self.monitor is not None and close_monitor:
            self.monitor.close()

        self._ser.close()

    def reopen(self):
        """
        Re-open a closed console connection with the same settings it was originally
        created with. After this function returns successfully, the object may
        be used again.
        """
        self._ser = serial.Serial(port=self._dev, **self._kwargs)

    @staticmethod
    def strip_echoed_input(input_str: str, output: str) -> str:
        """
        Remove echoed input (`input_str`) from data read from a serial console
        (`output`) and return the stripped string.
        """
        input_str = input_str.rstrip()
        if output[:len(input_str)] == input_str:
            return output[len(input_str):].lstrip()
        return output
