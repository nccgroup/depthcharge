# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Provides MemoryReader base class
"""

import os

from .. import log
from ..operation import Operation


class MemoryReader(Operation):
    """
    This base class extends :py:class:`~depthcharge.Operation` to provide
    memory :py:meth:`read()` and :py:meth:`read_to_file()` methods.  The
    constructor takes a single :py:class:`~depthcharge.Depthcharge` context
    object.
    """

    def _setup(self, addr, size):
        """
        Subclasses should override this method to perform any necessary setup
        activities (e.g. "configure Companion device") .

        The :py:class:`~.MemoryReader` base class implementation is a no-op.
        """
        # No-op base implementation

    def _teardown(self):
        """
        Subclasses should override this method to perform any necessary clean-up
        activities (e.g. "exit sub-prompt").

        The :py:class:`~.MemoryReader` base class implementation is a no-op.
        """
        # No-op base implementation

    def _describe_op(self, addr, size):
        """
        Return a string (suitable for logging) that describes the write
        operation that would be performed with the provided arguments.

        Note that this description is included in progress bars,
        so it should be relatively short.

        The default string formats the provided *addr* and *size*
        arguments:

        ``'({reader_name:s}) Reading {size:d} bytes @ 0x{addr:08x}'``

        *Example:*

        ``(CRC32MemoryReader) Reading 128 bytes @ 0xff784140``

        """
        s = '({:s}) Reading {:d} bytes @ 0x{:08x}'
        return s.format(self.name, size, addr)

    def _read(self, addr: int, size: int, handle_data):
        """
        Subclasses of :py:class:`~depthcharge.memory.reader.MemoryReader` must
        implement this method to perform the actual read operation.

        This method does not return a value, but instead should pass data to
        the provided ``handle_data()`` handler. This will take care of either
        buffering the data in memory or writing it to disk, depending upon
        which API function was invoked.
        """
        raise NotImplementedError('Subclass does not implement required method _read()')

    def read(self, addr: int, size: int, **kwargs) -> bytes:
        """
        Read *size* bytes from the specified address (*addr*) and
        return data as a ``bytes`` object.

        Specify a *show_progress=False* keyword argument to disable the progress
        bar printed during the read operation.

        This method will return partial output and present a warning  if interrupted
        by a *KeyboardInterrupt* exception.
        """
        ret = bytearray()

        if not kwargs.get('suppress_setup', False):
            self._setup(addr, size)

        desc = self._describe_op(addr, size)
        show = kwargs.get('show_progress', True)
        progress = self._ctx.create_progress_indicator(self, size, desc, unit='B', show=show)

        def _update_progress(data: bytes):
            ret.extend(data)
            progress.update(len(data))

        try:
            self._read(addr, size, _update_progress)
        except KeyboardInterrupt:
            msg = 'Read operation interrupted. {:d} / {:d} bytes read.'
            log.warning(msg.format(len(ret), size))
        finally:
            self._ctx.close_progress_indicator(progress)

        if not kwargs.get('suppress_teardown', False):
            self._teardown()

        return bytes(ret)

    # I'm really not super stoked about the code duplication here, but
    # combining this with read(), while still handling progress updates for
    # each _read() and KeyboardInterrupt just makes for even more code...
    def read_to_file(self, addr: int, size: int, filename: str, **kwargs):
        """
        Read *size* bytes from memory (located at *addr*) and stream data to
        a file specified via *filename*.

        Specify a *show_progress=False* keyword argument to disable the
        progress bar printed during the read operation.

        If interrupted by a *KeyboardInterrupt* exception, this method will
        finish writing any received data, cleanly close the file, and
        present a warning about a partial read.
        """

        if not kwargs.get('suppress_setup', False):
            self._setup(addr, size)

        desc = self._describe_op(addr, size)
        show = kwargs.get('show_progress', True)
        progress = self._ctx.create_progress_indicator(self, size, desc, unit='B', show=show)

        try:
            with open(filename, 'wb') as outfile:
                def _update_progress(data: bytes):
                    outfile.write(data)
                    progress.update(len(data))
                try:
                    self._read(addr, size, _update_progress)
                except KeyboardInterrupt:
                    outfile.flush()
                    num_written = os.fstat(outfile.fileno()).st_size
                    msg = 'Read operation interrupted. {:d} / {:d} bytes read.'
                    log.warning(msg.format(num_written, size))

        finally:
            self._ctx.close_progress_indicator(progress)

        if not kwargs.get('suppress_teardown'):
            self._teardown()


class MemoryWordReader(MemoryReader):
    """
    A MemoryWordReader is a specific type of :py:class:`~.MemoryReader` that
    can only operate on byte, word, long-word, and potentially quad-word sized
    data. The constructor takes a single :py:class:`~depthcharge.Depthcharge`
    context object.

    Subclasses must implement :py:meth:`_read_word`. This parent class will
    take care of invoking this method as needed to perform arbitrary-sized
    reads.
    """

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)
        self._mode      = self._ctx.arch.word_sizes()
        self._word_size = self._ctx.arch.word_size

    def _read_word(self, addr: int, size: int, handle_data):
        """
        Subclasses of :py:class:`~depthcharge.memory.reader.MemoryWordReader` must
        implement this method to perform the actual word-read operation.

        This method does not return a value, but instead should pass data to
        the provided ``handle_data()`` handler. This will take care of either
        buffering the data in memory or writing it to disk, depending upon
        which API function was invoked.
        """
        raise NotImplementedError('Bug: not implemented by subclass')

    def _read(self, addr: int, size: int, handle_data):
        word_size = self._word_size

        remaining = size
        while remaining >= word_size:
            self._read_word(addr, word_size, handle_data)
            addr += word_size
            remaining -= word_size

        while remaining > 0:
            if self._ctx.arch.supports_64bit_data and remaining >= 8:
                to_read = 8
            elif remaining >= 4:
                to_read = 4
            elif remaining >= 2:
                to_read = 2
            else:
                to_read = 1

            # Re-start if we need to drop to a smaller word size
            # (A number of commands operate in a continuation mode
            #  so long as we keep reading the same sized word.)
            if to_read < word_size:
                word_size = to_read
                self._teardown()
                self._setup(addr, word_size)

            self._read_word(addr, to_read, handle_data)
            addr += to_read
            remaining -= to_read
