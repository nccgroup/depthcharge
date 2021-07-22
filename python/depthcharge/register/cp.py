# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements CpCrashRegisterReader
"""

from ..operation import Operation
from .data_abort import DataAbortRegisterReader


class CpCrashRegisterReader(DataAbortRegisterReader):
    """
    This is a :py:class:`~.DataAbortRegisterReader` that uses the ``cp``
    console command to trigger the Data Abort used to read registers.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['cp'],
        'crash_or_reboot': True,
    }

    @classmethod
    def rank(cls, **_kwargs):
        return 10

    # This is by intent; we are not using another memory reader.
    # pylint: disable=method-hidden
    def _trigger_data_abort(self):
        if self._ctx.arch.name == 'AARCH64':
            # Using the same value for source/dest does not appear to work,
            # perhaps due to the change to use memcpy() in U-Boot 2017.01
            # (c2538421b28424b9705865e838c5fba19c9dc651).
            #
            # Adding this as a special case for AARCH64, as this was confirmed
            # to work with the default crash_addr. (Granted, it too is probably
            # relying on a SoC-specific memory map.)
            cmd = 'cp.q 0 {:x} 1'.format(self._crash_addr)
        else:
            cmd = 'cp.l {addr:x} {addr:x} 1'.format(addr=self._crash_addr)

        return self._ctx.send_command(cmd)


Operation.register(CpCrashRegisterReader)
