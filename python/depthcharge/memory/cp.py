# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements CpCrashMemoryReader and CpMemoryWriter
"""

from ..operation import Operation
from .data_abort import DataAbortMemoryReader
from .stratagem  import StratagemMemoryWriter
from ..hunter.cp import CpHunter


class CpCrashMemoryReader(DataAbortMemoryReader):
    """
    Available only for ARM targets.

    The :py:class:`~.CpCrashMemoryReader` crashes the platform by attempting
    to copy a word from a target read location to a non-writable location,
    resulting in a Data Abort. The read data is extracted from a register
    dump printed by U-Boot when this occurs.

    This is very slow, as it involves 1 reset per-word.

    Refer to the :py:class:`.DataAbortMemoryReader` parent class for
    information about supported keyword arguments.
    """

    _required = {
        'arch': ['ARM', 'AARCH64'],
        'commands': ['cp'],
        'crash_or_reboot': True,
    }

    @classmethod
    def rank(cls, **_kwargs) -> int:
        return 3

    def _trigger_data_abort(self, address: int, **_kwargs):
        mode = 'q' if self._ctx.arch.supports_64bit_data else 'l'
        cmd = 'cp.{:s} {:x} {:x} 1'.format(mode, address, self._crash_addr)
        return self._ctx.send_command(cmd)


class CpMemoryWriter(StratagemMemoryWriter):
    """
    This :py:class:`~.StratagemMemoryWriter` uses the ``cp`` console command
    to write a desired payload to memory using a :py:class:`~depthcharge.Stratagem` built
    by :py:class:`~depthcharge.hunter.CpHunter`.
    """

    _required = {
        'commands': ['cp'],
    }

    _stratagem_spec = Operation._create_stratagem_spec(dst_off=int)
    _stratagem_hunter = CpHunter

    @classmethod
    def rank(cls, **kwargs):
        return 9

    def _write_stratagem(self, wr_addr: int, stratagem, progress):
        def is_aligned(n, src, dst, size):
            return (size % n == 0) and (src % n == 0) and (dst % n == 0)

        for entry in stratagem:
            src_addr = entry['src_addr']
            size     = entry['src_size']
            dst_addr = entry['dst_off'] + wr_addr

            if self._ctx.arch.supports_64bit_data and is_aligned(8, src_addr, dst_addr, size):
                mode = 'q'
                size //= 8
            elif is_aligned(4, src_addr, dst_addr, size):
                mode = 'l'
                size //= 4
            elif is_aligned(2, src_addr, dst_addr, size):
                mode = 'w'
                size //= 2
            else:
                mode = 'b'

            cmd = 'cp.{:s} {:x} {:x} {:x}'.format(mode, src_addr, dst_addr, size)
            self._ctx.send_command(cmd, check=True)
            progress.update(size)


Operation.register(CpCrashMemoryReader, CpMemoryWriter)
