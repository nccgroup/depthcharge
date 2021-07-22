# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Provides MemoryWriter base class
"""

from ..operation import Operation


class MemoryWriter(Operation):
    """
    This base class extends :py:class:`~depthcharge.Operation`
    to provide memory :py:meth:`write()` and :py:meth:`write_from_file()` methods.
    The constructor takes a single :py:class:`~depthcharge.Depthcharge` context
    object, as well as an optional *block_size* keyword argument.

    The *block_size* values can be used to override the number of bytes
    written at a time. The default value is 128, but some subclasses
    override this with a more appropriate default or do not respect
    this value. You probably don't want or need to change this.

    """

    def _setup(self, addr, data):
        """
        Subclasses should override this method to perform any necessary setup
        activities (e.g. "configure Companion device") .

        The :py:class:`~.MemoryWriter` base class implementation is a no-op.
        """
        # No-op base implementation

    def _teardown(self):
        """
        Subclasses should override this method to perform any necessary clean-up
        activities (e.g. "exit sub-prompt").

        The :py:class:`~.MemoryWriter` base class implementation is a no-op.
        """
        # No-op base implementation

    def __init__(self, ctx, **kwargs):
        block_size = int(kwargs.pop('block_size', 128))

        super().__init__(ctx, **kwargs)

        # Used by write() to iterate over a payload in fixed-size chunks.
        # Status progress is update in increments of this size.
        self._block_size = block_size

        # Allow the API user to override this at call-time
        self._allow_block_size_override = True

    def _describe_op(self, addr, data):
        """
        Return a string (suitable for logging) that describes the write
        operation that would be performed with the provided arguments.
        """
        s = '({:s}) Writing {:d} bytes @ 0x{:08x}'
        return s.format(self.name, len(data), addr)

    def _write(self, addr: int, data: bytes, **kwargs):
        """
        Subclasses of :py:class:`~depthcharge.memory.writer.MemoryWriter` must
        implement this method to perform the actual write operation.
        """
        raise NotImplementedError('Bug: MemoryWriter subclass does not implement _write().')

    def write(self, addr: int, data: bytes, **kwargs):
        """
        Write *data* to the specified address (*addr*).

        Specify a *show_progress=False* keyword argument to disable the progress
        bar printed during the write operation.
        """

        if self._allow_block_size_override:
            block_size = kwargs.get('block_size', self._block_size)
        else:
            block_size = self._block_size

        size = len(data)

        desc = '({:s}) Writing {:d} bytes @ 0x{:08x}'.format(self.name, size, addr)
        show = kwargs.get('show_progress', True)
        progress = self._ctx.create_progress_indicator(self, size, desc, unit='B', show=show)

        # Run any setup operations
        if not kwargs.get('suppress_setup', False):
            self._setup(addr, data)

        try:
            for offset in range(0, size, block_size):
                to_write = block_size
                if (size - offset) < block_size:
                    to_write = (size - offset)

                data_slice = data[offset:offset + to_write]
                self._write(addr + offset, data_slice, **kwargs)
                progress.update(to_write)
        finally:
            if not kwargs.get('suppress_teardown', False):
                self._teardown()
            self._ctx.close_progress_indicator(progress)

    def write_from_file(self, addr: int, filename: str, **kwargs):
        """
        Open the file specified via *filename* and write its contents to
        the address indicated by *addr*.

        Specify a *show_progress=False* keyword argument to disable the progress
        bar printed during the write operation.
        """

        with open(filename, 'rb') as infile:
            data = infile.read()
            self.write(addr, data, **kwargs)


class MemoryWordWriter(MemoryWriter):
    """
    A MemoryWordWriter is a specific type of :py:class:`~.MemoryWriter` that
    can only operate on byte, word, long-word, and potentially quad-word sized
    data. The constructor takes a single :py:class:`~depthcharge.Depthcharge`
    context object.

    Subclasses must implement :py:meth:`_write_word`. This parent class will
    take care of invoking this method as needed to perform arbitrary-sized
    writes.
    """

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)
        self._mode       = self._ctx.arch.word_sizes()
        self._word_size  = self._ctx.arch.word_size
        self._block_size = self._word_size
        self._allow_block_size_override = False

    def _write_word(self, addr: int, data: bytes, **kwargs):
        """
        Subclasses of :py:class:`~depthcharge.memory.MemoryWordWriter` must
        implement this method to perform the actual word-write operation.
        """
        raise NotImplementedError('Subclass bug: _write_word() not implemented')

    def _write(self, addr: int, data: bytes, **kwargs):
        size = len(data)
        assert size <= self._block_size

        i = 0

        # Write byte-by-byte until we're word-aligned.
        while not self._ctx.arch.is_word_aligned(addr + i):
            self._write_word(addr + i, data[i:i + 1])
            i += 1

        while i < size:
            remaining = size - i
            if remaining >= 8 and self._ctx.arch.supports_64bit_data:
                to_write = 8
            elif remaining >= 4:
                to_write = 4
            elif remaining >= 2:
                to_write = 2
            else:
                to_write = 1

            self._write_word(addr + i, data[i:i + to_write])
            i += to_write
