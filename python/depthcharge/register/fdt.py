# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements FDTCrashRegisterReader
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class FDTCrashRegisterReader(DataAbortRegisterReader):
    """
    This is a :py:class:`~.DataAbortRegisterReader` that uses the ``fdt``
    console command to trigger the Data Abort used to read registers.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['fdt'],
        'crash_or_reboot': True,
    }

    @classmethod
    def rank(cls, **_kwargs):
        # Seems to taint quite a bit
        return 15

    # This is by intent; we are not using another memory reader.
    # pylint: disable=method-hidden
    def _trigger_data_abort(self):
        cmd = 'fdt addr {:x}'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


Operation.register(FDTCrashRegisterReader)
