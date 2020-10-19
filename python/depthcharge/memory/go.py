# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements GoMemoryReader
"""

from .reader import MemoryReader, MemoryWordReader
from .. import log
from ..operation import Operation, OperationNotSupported

_START_SENTINEL = b'-:[START]:-'
_END_SENTINEL   = b'-:[|END|]:-'


class _GoMemoryWordReader(MemoryWordReader):
    """
    Helper reader that can be used by GoMemoryReader to discover the
    U-Boot global data structure's jump table (gd->jt).

    This is kept internal and we specifically don't register it for
    use by API users. (Nor will we plan to, unless there's a use-case
    for it beyond bootstrapping GoMemoryReader.)
    """

    # Not actually checked because this is kept internal.
    # Specified just for the sake of clarity.
    _required = {
        'commands': ['go'],
        'payloads': ['RETURN_MEMORY_WORD']
    }

    @classmethod
    def rank(cls, **_kwargs):
        return 0

    def _read_word(self, addr: int, size: int, handle_data):
        (rc, _) = self._ctx.execute_payload('RETURN_MEMORY_WORD', '0x{:08x}'.format(addr))
        data = self._ctx.arch.int_to_bytes(rc)
        return data[:size]


class GoMemoryReader(MemoryReader):
    """
    The GoMemoryReader leverages a simple binary payload that can be invoked with U-Boot's "go"
    command to dump large regions of memory. It writes binary data to the console, allowing
    data to be retrieved more efficiently than with text-based memory access mechanisms
    like :py:class:`~depthcharge.memory.MdMemoryReader`.

    However, in order to use this :py:class:`~depthcharge.memory.MemoryReader`,
    a memory write primitive is required to deploy its executable payloads,
    and the "go" command needs to be present. (*Hint: Technically, only a write primitive
    is strictly necessary if one can modify the U-Boot command table "linker list" to direct
    a command's function pointer to a makeshift "go" command implementation. ;)* )

    """

    _required = {
        'commands': ['go'],
        'payloads': ['RETURN_MEMORY_WORD', 'READ_MEMORY'],
        'gd': True,
        'gd_jt': True
    }

    @classmethod
    def rank(cls, **kwargs):
        # Loading a payload incurs quite a bit of overhead.
        # This is only worthwhile for larger amounts of data.
        data_len = kwargs.get('data_len', 0)
        if data_len   >= 65536:
            return 90

        if data_len >= 16384:
            return 75

        if data_len >= 4096:
            return 25

        return 5

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

        # Fallback reader - We'll check for a better one later.
        # Init is too early to make a determiniation because we're created
        # early in the Depthcharge.__init__() amongst other MemoryReaders
        self._fallback = _GoMemoryWordReader(ctx, **kwargs)

        # Use fallback until we have the jump table address needed
        # by the READ_MEMORY payload.
        self._jt_addr = None

    def _setup(self, _addr, _data):
        msg = '({:s}) '.format(self.name)
        try:
            self._jt_addr = self._ctx._gd['jt']['address']
            msg += 'Using payload-based read implementation'
            self._ctx.deploy_payload('READ_MEMORY')
        except KeyError:
            msg += 'U-Boot jump table location unknown. Using fallback reader.'
            try:
                # Attempt to use a better (faster) memory read operation if we have it.
                self._fallback = self._ctx._memrd.default(exclude=self)
            except OperationNotSupported:
                # Just use the word reader
                self._ctx.deploy_payload('RETURN_MEMORY_WORD')

        log.debug(msg)

    def _read(self, addr: int, size: int, handle_data):
        if self._jt_addr is not None:
            blocksize = 16384
            read_op = self._normal_read
        else:
            blocksize = 1024
            read_op = self._fallback_read

        offset = 0
        while offset < size:
            n_left = size - offset
            to_read = n_left if n_left < blocksize else blocksize
            read_op(addr + offset, to_read, handle_data)
            offset += to_read

    def _fallback_read(self, addr, size, handle_data):
        """
        Helper function to read memory in search of gd and gt->jt, using the
        "best" available memory read operation we have available.
        """
        data = self._fallback.read(addr, size)
        handle_data(data)

    def _normal_read(self, addr: int, size: int, handle_data):
        """
        Normal, faster binary payload-based read.
        """
        log.debug('Normal read of {:d} bytes @ 0x{:08x}'.format(size, addr))
        self._ctx.execute_payload('READ_MEMORY',
                                  '0x{:08x}'.format(self._jt_addr),
                                  '0x{:08x}'.format(addr),
                                  '0x{:08x}'.format(size),
                                  read_response=False)

        resp = self._ctx.console.read_raw()
        if not resp.endswith(_START_SENTINEL):
            raise ValueError('Did not receive expected start sentinel')

        self._ctx.console.write('\n')

        data = self._ctx.console.read_raw()
        endpos = data.rfind(_END_SENTINEL)
        if endpos > 0:
            self.log.debug('Found end sentinel @ byte {:d}'.format(endpos))
        else:
            raise ValueError('Did not receive expected end sentinel')
        data = data[:endpos]

        # U-Boot's drivers/serial/serial-uclass.c, _serial_putc() maps
        # NL -> CR-NL (akin to ONLCR), which we don't want.
        handle_data(data.replace(b'\r\n', b'\n'))


# Register declared Operation
Operation.register(GoMemoryReader)
