# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements CRC32CrashRegisterReader
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class CRC32CrashRegisterReader(DataAbortRegisterReader):
    """
    This is a :py:class:`~.DataAbortRegisterReader` that uses the ``crc32``
    console command to trigger the Data Abort used to read registers.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['crc32'],
        'crash_or_reboot': True
    }

    # This is by intent; we are not using another memory reader.
    # pylint: disable=method-hidden
    def _trigger_data_abort(self):
        cmd = 'crc32 {addr:x} 0 {addr:x}'.format(addr=self._crash_addr)
        return self._ctx.send_command(cmd)


Operation.register(CRC32CrashRegisterReader)
