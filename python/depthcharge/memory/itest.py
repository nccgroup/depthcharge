# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements ItestMemoryReader
"""

from .reader import MemoryWordReader
from ..operation import Operation


class ItestMemoryReader(MemoryWordReader):
    """
    This :py:class:`~depthcharge.memory.MemorReader` implementation that uses
    the `itest` U-Boot command as an byte-wise memory read operation.

    By design, this command allows two values to be compared using the
    operators `-eq`, `-ne`, `-lt`, `-gt`, `-le`, `-ge`, `==`, `!=`,
    `<>`, `<`, `>`, `<=`, and `>=`. It also allows addresses to be dereferenced in these comparisons
    using a C-like `*<address>` syntax.

    Although the `itest` command cannot read a value directory, a binary search using the above
    operators can be used to determine the value at a specified memory location, with a byte-level
    granularity.
    """
    _required = {
        'commands': ['itest', 'echo']
    }

    @classmethod
    def rank(cls, **kwargs):
        # Slow, performs binary search in [0, 255] per byte
        return 25

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

        # We always want to use the single-byte mode of itest,
        # regardless of the largest word size available
        self._word_size = 1

    def _check_value(self, addr, value, operator='<'):
        cmd = 'if itest.b *{:x} {:s} {:x};then echo 1;fi'
        resp = self._ctx.send_command(cmd.format(addr, operator, value))
        return resp != ''

    def _read_word(self, addr: int, size: int, handle_data):
        assert size == 1

        if self._check_value(addr, 0x00, '=='):
            handle_data(b'\x00')
            return

        if self._check_value(addr, 0xff, '=='):
            handle_data(b'\xff')
            return

        min_val = 0x00
        max_val = 0xff

        while max_val != min_val:
            val = (min_val + max_val + 1) // 2
            if self._check_value(addr, val, '<'):
                max_val = val - 1
            else:
                min_val = val

        handle_data(max_val.to_bytes(1, 'big'))


# Register declared Operations
Operation.register(ItestMemoryReader)
