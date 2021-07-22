# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
This module provides data abort-baed register reads atop of memory read and write
U-Boot commands specifically intended for memory display or modification.

See: <https://www.denx.de/wiki/publish/DULG/to-delete/UBootCmdGroupMemory.html>
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class MdCrashRegisterReader(DataAbortRegisterReader):
    """
    A :py:class:`.DataAbortRegisterReader` that uses the ``md.l`` console command
    to trigger a Data Abort.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['md'],
        'crash_or_reboot': True,
    }

    @classmethod
    def rank(cls, **_kwargs):
        # Preferred read-only Data Abort
        return 21

    def _trigger_data_abort(self):
        cmd = 'md.l {:x} 1'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


class MmCrashRegisterReader(DataAbortRegisterReader):
    """
    A :py:class:`.DataAbortRegisterReader` that uses the ``mm.l`` console command
    to trigger a Data Abort.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['mm'],
        'crash_or_reboot': True,
    }

    def _trigger_data_abort(self):
        cmd = 'mm.l {:x}'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


class MwCrashRegisterReader(DataAbortRegisterReader):
    """
    A :py:class:`.DataAbortRegisterReader` that uses the ``mm.l`` console command
    to trigger a Data Abort.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['mm'],
        'crash_or_reboot': True,
    }

    def _trigger_data_abort(self):
        cmd = 'mw.l {:x} 0'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


class NmCrashRegisterReader(DataAbortRegisterReader):
    """
    A :py:class:`.DataAbortRegisterReader` that uses the ``nm.l`` console command
    to trigger a Data Abort.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['nm'],
        'crash_or_reboot': True,
    }

    def _trigger_data_abort(self):
        cmd = 'nm.l {:x}'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


Operation.register(
    MdCrashRegisterReader,
    MmCrashRegisterReader,
    MmCrashRegisterReader,
    NmCrashRegisterReader,
)
