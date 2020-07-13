# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Provides :py:class:`depthcharge.memory.MemoryWriter` operations implemented atop of ye
olde file transfer protocols from Age of Modems (e.g., kermit, xmodem, etc).
"""

import os
import subprocess
import tempfile

from .writer import MemoryWriter
from ..operation import Operation, OperationFailed, OperationNotSupported


class _LoadMemoryWriter(MemoryWriter):
    """
    Private base class used to implement Load<protocol>-based writers.

    Kicks off U-boot side of things and then launches the corresponding
    external process to perform the desired data transfer.
    """

    @classmethod
    def rank(cls, **kwargs):
        # These all incur overhead that's not worthwhile with little data.
        data_len = kwargs.get('data_len', 0)
        if data_len <= 256:
            return 35

        if data_len <= 1024:
            return 55

        if data_len <= 4095:
            return 75

        if data_len <= 16384:
            return 85

        return 95

    def _write(self, _addr, _data, **kwargs):
        raise OperationNotSupported(self, 'Not used by _LoadMemoryWriter')

    def _run_subprocess(self, addr, filename):
        """
        Subclass must implement this to invoke their corresponding program.

        If the program does not succeed, a
        :py:class:`subprocess.CalledProcessError` must be raised.

        No value needs to be returned upon success.
        """
        raise NotImplementedError

    def _send_command(self, addr: int):
        cmd = '{} 0x{:08x}'.format(self._required['commands'][0], addr)
        return self._ctx.send_command(cmd, check=True)

    def write(self, addr: int, data: bytes, **kwargs):
        f = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        f.write(data)
        f.close()
        self.write_from_file(addr, f.name)
        os.remove(f.name)

    def write_from_file(self, addr: int, filename: str, **kwargs):
        self._send_command(addr)
        self._ctx.console.close(close_monitor=False)

        try:
            self._run_subprocess(addr, filename, **kwargs)
        except subprocess.CalledProcessError as failure:
            err  = '{:s} failed with status {:d}'.format(failure.cmd[0], failure.returncode)
            if failure.stderr:
                err += ': ' + failure.stderr

            raise OperationFailed(self, err)

        finally:
            # Even if we failed, try to return to a known state
            self._ctx.console.reopen()
            self._ctx.interrupt()


class LoadbMemoryWriter(_LoadMemoryWriter):
    """
    This is a :py:class:`~depthcharge.memory.MemoryWriter` implemented atop of the
    `ckermit` program, which implements the Kermit protocol. It can be used to load data into memory
    using U-Boot's ``loadb`` command.

    The ckermit package appears to have been dropped from some recent Linux distributions.
    Source code can be obtained from http://www.kermitproject.org.  We've found that in order to build it
    with *make linux*, ``ckucmd.c`` needs to have an ``_IO_file_flags`` macro defined due to ckermit's
    decision to access private data members of libc ``FILE`` structures. 😬
    """

    @classmethod
    def rank(cls, **kwargs):
        # kermit is a bit slower than other options
        return super().rank(**kwargs) - 10

    _required = {
        'commands': ['loadb'],
        'host_programs': ['ckermit'],
    }

    def _run_subprocess(self, addr: int, filename: str):
        kermit = self._req['host_programs']['ckermit']
        args = [
            kermit,
            '-i',
            '-l', self._ctx.console.device,
            '-b', str(self._ctx.console.baudrate),
            '-m', 'none',
            '-C', 'set carrier-watch off,set prefixing all',
            '-s', filename
        ]

        return subprocess.run(args, check=True)


class LoadxMemoryWriter(_LoadMemoryWriter):
    """
    This is a :py:class:`~depthcharge.memory.MemoryWriter` implemented atop of the `sx` program,
    which implements XMODEM protocol. It can be used to load data into memory using U-Boot's
    ``loadx`` command.
    """

    _required = {
        'commands': ['loadx'],
        'host_programs': ['sx'],
    }

    def _run_subprocess(self, addr: int, filename: str):
        with open(self._ctx.console.device, 'w+b', buffering=0) as port_io:
            xmodem = self._req['host_programs']['sx']
            args = [xmodem, filename]
            ret = subprocess.run(args, stdin=port_io, stdout=port_io, check=True)
        return ret


class LoadyMemoryWriter(_LoadMemoryWriter):
    """
    This is a :py:class:`~depthcharge.memory.MemoryWriter` implemented atop of the `sb` program,
    which implements YMODEM protocol. It can be used to load data into memory using U-Boot's
    ``loady`` command.
    """

    _required = {
        'commands': ['loady'],
        'host_programs': ['sb'],
    }

    def _run_subprocess(self, addr: int, filename: str):
        with open(self._ctx.console.device, 'w+b', buffering=0) as port_io:
            ymodem = self._req['host_programs']['sb']
            args = [ymodem, filename]
            ret = subprocess.run(args, stdin=port_io, stdout=port_io, check=True)

        return ret


# Register declared Operations
Operation.register(LoadbMemoryWriter, LoadxMemoryWriter, LoadyMemoryWriter)
