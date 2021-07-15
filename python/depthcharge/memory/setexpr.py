# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements SetexprMemoryReader
"""

import re

from math import ceil

from .memcmds import MdMemoryReader
from .reader import MemoryWordReader
from ..operation import Operation


class SetexprMemoryReader(MemoryWordReader):
    """
    The U-Boot ``setexpr`` console command can be used to assign an environment
    variable based upon the result of an expression. The supported expression
    syntax includes a memory dereference operation, which this class leverages
    to provide a :py:class:`~depthcharge.memory.MemoryWordReader` implementation.
    """

    _required = {
        'commands': ['setexpr', 'printenv']  # TODO: Is setexpr without setenv supported?
    }

    _print_re = re.compile(r'(?P<var>[\.a-zA-Z0-9_]+)=(?P<data>[0-9a-fA-F]+)')

    @classmethod
    def rank(cls, **kwargs):
        # Inferior to md. Slow 1-word per access with extra logic
        return MdMemoryReader.rank(**kwargs) // 3

    def _read_word(self, addr: int, size: int, handle_data):
        var  = '.dcse'  # "Depthcharge setexpr" - Uses hidden variable dot prefix
        mode = self._mode[size]
        self._ctx.send_command('setexpr.{:s} {:s} *{:x}'.format(mode, var, addr))
        resp = self._ctx.send_command('print {:s}'.format(var))
        match = self._print_re.match(resp)
        if not match:
            self.log.error('Did not receive expected print output. Got:  ' + resp)
            self._ctx.interrupt()
            raise IOError('Failed to read {:d} byte(s) @ 0x{:08x}'.format(size, addr))

        data = match.group('data')

        # Apparently setexpr.l will happily return 8 bytes when we only asked for 4.
        # It obliges with .b, w., and .s though. Odd.  Hack around this.
        out_size = size
        if len(data) / 2 > size:
            size = ceil(len(data) / 2)

        data_bytes = self._ctx.arch.hexint_to_bytes(data, size)
        handle_data(data_bytes[:out_size])


Operation.register(SetexprMemoryReader)
