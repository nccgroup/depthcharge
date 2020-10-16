# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements FDTCrashRegisterReader
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class CpCrashRegisterReader(DataAbortRegisterReader):
    """
    This is a :py:class:`~.DataAbortRegisterReader` that uses the ``cp``
    console command to trigger the Data Abort used to read registers.
    """

    _required = {
        'arch': 'ARM',
        'commands': ['cp'],
        'crash_or_reboot': True,
    }

    @classmethod
    def rank(cls, **_kwargs):
        return 10

    # This is by intent; we are not using another memory reader.
    # pylint: disable=method-hidden
    def _trigger_data_abort(self):
        cmd = 'cp.l {addr:x} {addr:x} 1'.format(addr=self._crash_addr)
        return self._ctx.send_command(cmd)


Operation.register(CpCrashRegisterReader)
