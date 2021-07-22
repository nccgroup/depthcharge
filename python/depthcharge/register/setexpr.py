# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements SetExprCrashRegisterReader
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class SetexprCrashRegisterReader(DataAbortRegisterReader):
    """
    This is a :py:class:`~.DataAbortRegisterReader` that uses the ``setexpr``
    console command to trigger the Data Abort used to read registers.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['setexpr'],
        'crash_or_reboot': True,
    }

    # This is by intent; we are not using another memory reader.
    # pylint: disable=method-hidden
    def _trigger_data_abort(self):
        cmd = 'setexpr.l _ *{:x}'.format(self._crash_addr)
        return self._ctx.send_command(cmd)


Operation.register(SetexprCrashRegisterReader)
