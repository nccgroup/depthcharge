# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements ItestCrashRegisterReader
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class ItestCrashRegisterReader(DataAbortRegisterReader):
    """
    This is a :py:class:`~.DataAbortRegisterReader` that uses the ``itest``
    console command to trigger the Data Abort used to read registers.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['itest'],
        'crash_or_reboot': True,
    }

    # This is by intent; we are not using another memory reader.
    # pylint: disable=method-hidden
    def _trigger_data_abort(self):
        cmd = 'itest.l *{:x} == 0'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


Operation.register(ItestCrashRegisterReader)
