# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
This module provides memory read and write operations for the U-Boot
commands specifically intended for memory display or modification.

See: <https://www.denx.de/wiki/publish/DULG/to-delete/UBootCmdGroupMemory.html>
"""

import re

from .reader import MemoryReader, MemoryWordReader
from .writer import MemoryWordWriter

from ..operation import Operation, OperationFailed

# Match prompt (address/data) for mm and nm commands
_MM_NM_RE = re.compile(r'(?P<addr>[0-9a-fA-F]+)\s*:\s(?P<data>[0-9a-fA-F]+)\s*?\s*')


def _verify_mm_nm_resp(obj, resp, expected_addr, cmd, op):
    """
    Helper function used for validating mm and nm repsonses
    """
    match = _MM_NM_RE.match(resp)

    if not match:
        obj.log.error('Did not receive expected {:s} prompt. Got: {:s}'.format(cmd, resp))
        obj._ctx.interrupt()
        raise IOError('Failed to start {:s}-based memory {:s}'.format(cmd, op))

    prompt_addr = int(match.group('addr'), 16)
    if expected_addr != prompt_addr:
        msg = 'Got {:s} prompt with address={:08x}, expected {:08x}'
        obj.log.error(msg.format(cmd, prompt_addr, expected_addr))
        obj._ctx.interrupt()
        raise IOError('Failed to start {:s}-based memory {:s}'.format(cmd, op))

    return (match.group('addr'), match.group('data'))


class MdMemoryReader(MemoryReader):
    """
    Reads memory using the U-Boot console command `md` (memory display),
    which outputs a textual hex dump.
    """

    _required = {
        'commands': ['md']
    }

    # TODO: inspect md help text or U-Boot version to determine quirks/flavor
    # I've seen a few that require [.b, .w., .l] with spaces, I think?

    # Match md[.b, .w, .l] output without strict formatting expectations
    # and wait for bug reports to determine how poor of a decision this was.
    _mdre = re.compile(r"""
        ^
        (?P<addr>[0-9a-fA-F]{8,}):\s+       # Address prefix
        (?P<data>([0-9a-fA-F]+\s)+)         # Data words
        \s+.{1,16}                          # ASCII representation
    """, re.VERBOSE)

    @classmethod
    def rank(cls, **kwargs):
        # Favor this for smaller amounts of data, and then less so
        # as the data grows.

        data_len = kwargs.get('data_len', 0)
        if data_len <= 256:
            return 95

        if data_len <= 1024:
            return 75

        if data_len <= 4095:
            return 65

        if data_len <= 16384:
            return 50

        return 35

    def _read(self, addr: int, size: int, handle_data):

        if self._ctx.arch.supports_64bit_data and size >= 8 and addr % 8 == 0:
            mode = '.q'
            count = (size // 8) if size % 8 == 0 else (size // 8) + 1
        elif size >= 4 and addr % 4 == 0:
            mode = '.l'
            count = (size // 4) if size % 4 == 0 else (size // 4) + 1
        elif size >= 2 and addr % 2 == 0:
            mode = '.w'
            count = (size // 2) if size % 2 == 0 else (size // 2) + 1
        else:
            mode = '.b'
            count = size

        endianness = self._ctx.arch.endianness

        cmd = 'md{:s} {:x} {:x}'.format(mode, addr, count)
        self._ctx.send_command(cmd, read_response=False)

        # Seeing \r prefixed on each line in MT7628 builds dated
        # U-Boot 1.1.3 (Sep 17 2018 - 18:22:09)
        #
        # Wow, been a while since versions other than YYYY.MM, no?
        #
        # Anyway, that's the point of lstripping this junk.
        #
        line = self._ctx.console.readline().lstrip()
        line = self._ctx.console.strip_echoed_input(cmd, line)
        if line == '':
            line = self._ctx.console.readline().lstrip()

        self._ctx._check_response_for_error(line)
        n_read = 0

        while line not in ('', self._ctx.prompt):
            match = self._mdre.match(line)
            if match is None:
                raise OperationFailed('Failed to parse line: ' + line)

            words = match.group('data').strip().split()

            for word in words:
                data = int.to_bytes(int(word, 16), len(word) // 2, endianness)
                end_idx = len(data) if (size - n_read) > len(data) else (size - n_read)
                handle_data(data[:end_idx])
                n_read += end_idx

            line = self._ctx.console.readline().lstrip()


class MmMemoryReader(MemoryWordReader):
    """
    Reads memory contents using the U-Boot console's `mm` (*memory modify*) command,
    which provides an interactive interface for viewing and modifying memory.

    This implementation leverages the fact that the current state is displayed,
    but not modified, if no change is provided for the currently displayed word.
    """

    _required = {
        'commands': ['mm']
    }

    @classmethod
    def rank(cls, **kwargs):
        # MdMemoryReader is always a better option
        return MdMemoryReader.rank(**kwargs) // 2

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)
        self._setup_requested = False
        self._perform_setup = False

    def _setup(self, addr, size):
        if self._perform_setup:
            self._setup_requested = False
            mode = self._mode[size]
            resp = self._ctx.send_command('mm.{:s} {:x}'.format(mode, addr))
            (_, data) = _verify_mm_nm_resp(self, resp, addr, 'mm', 'read')
        else:
            # Defer this until the actual _read_word() call because
            # the nm prompt contains the current data at the selected address
            self._setup_requested = True
            data = None

        self._perform_setup = False
        return data

    def _read_word(self, addr: int, size: int, handle_data):
        if self._setup_requested:
            # Will pick up our first data word when we start. The
            # data is in the response to our first command.
            self._perform_setup = True
            data = self._setup(addr, size)
        else:
            # Empty line implies "no change to current value"
            self._ctx.console.write('\n')
            resp = self._ctx.console.read().lstrip()
            (_, data) = _verify_mm_nm_resp(self, resp, addr, 'mm', 'read')

        data_bytes = self._ctx.arch.hexint_to_bytes('0x' + data, size)
        handle_data(data_bytes)

    def _teardown(self):
        # Exit the mm subprompt
        self._ctx.interrupt()


class MmMemoryWriter(MemoryWordWriter):
    """
    Writes memory using the U-Boot console command `mm`, which
    provides an interactive interface for viewing and modifying memory.
    """

    _required = {'commands': ['mm']}

    @classmethod
    def rank(cls, **kwargs):
        # 1-word at at a time through interactive prompts
        data_len = kwargs.get('data_len', 0)
        if data_len > 64:
            return 25

        return 35

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)
        self._curr_word_size = None
        self._update_word_size = False

    def _setup(self, addr, data):
        if self._update_word_size:
            word_size = len(data)
            mode = self._mode[word_size]  # Will result in exception for invalid size
            self._curr_word_size = word_size
        else:
            mode = self._mode[self._word_size]
            self._curr_word_size = self._word_size

        resp = self._ctx.send_command('mm.{:s} {:x}'.format(mode, addr))
        _verify_mm_nm_resp(self, resp, addr, 'mm', 'write')

        self._update_word_size = False

    def _write_word(self, addr, data, **_kwargs):

        # We expect to see this condition if we're winding down and writing the
        # remaining data that's not divisible by our current word size
        if len(data) != self._curr_word_size:
            # Break back into the console
            self._teardown()

            # Restart using the request word size
            self._update_word_size = True
            self._setup(addr, data)

        # Send next word to mm prompt
        data_as_int = int.from_bytes(data, self._ctx.arch.endianness)
        data_input = '{:x}\n'.format(data_as_int)
        self._ctx.console.write(data_input)

        # Read response, which should be the next prompt.
        # Strip off echoed output from our console.write()
        resp = self._ctx.console.read()
        resp = self._ctx.console.strip_echoed_input(data_input, resp)
        if resp.startswith(data_input):
            resp = resp[len(data_input):]

        # mm auto-increments the address
        _verify_mm_nm_resp(self, resp, addr + len(data), 'mm', 'write')

    def _teardown(self):
        self._curr_word_size = self._word_size
        self._ctx.interrupt()


class MwMemoryWriter(MemoryWordWriter):
    """
    Write data to memory using the U-Boot console `mw` (memory fill) command,
    one word at a time.
    """
    _required = {'commands': ['mw']}

    @classmethod
    def rank(cls, **kwargs):
        # 1-word per invocation
        data_len = kwargs.get('data_len', 0)
        if data_len > 64:
            return 35

        return 40

    def _write_word(self, addr, data, **_kwargs):
        mode = self._mode[len(data)]
        data_as_int = int.from_bytes(data, self._ctx.arch.endianness)

        cmd = 'mw.{:s} {:x} {:x}'.format(mode, addr, data_as_int)
        self._ctx.send_command(cmd, check=True)


class NmMemoryReader(MemoryWordReader):
    """
    Reads memory using U-Boot's interactive `nm` (memory modify, constant address) command,
    one word at a time.

    This leverages the fact that no change is made to the currently shown word
    if no replacement is provided.
    """
    _required = {
        'commands': ['nm']
    }

    @classmethod
    def rank(cls, **kwargs):
        # Pretty much the same
        return MmMemoryReader.rank(**kwargs)

    def _read_word(self, addr: int, size: int, handle_data):
        mode = self._mode[size]
        resp = self._ctx.send_command('nm.{:s} {:x}'.format(mode, addr))

        (_, data) = _verify_mm_nm_resp(self, resp, addr, 'nm', 'read')
        data_bytes = self._ctx.arch.hexstr_to_int(data, size)
        handle_data(data_bytes)

        self._ctx.interrupt()


class NmMemoryWriter(MemoryWordWriter):
    """
    Writes memory using U-Boot's interactive `nm` (memory modify, constant
    address) command, one word at a time.
    """

    _required = {'commands': ['nm']}

    @classmethod
    def rank(cls, **kwargs):
        # Pretty much the same
        return MmMemoryWriter.rank(**kwargs)

    def _write_word(self, addr, data, **_kwargs):
        mode = self._mode[len(data)]
        resp = self._ctx.send_command('nm.{:s} {:x}'.format(mode, addr))

        # nm is "constant address" --
        # No increment will occur with each successive prompt
        _verify_mm_nm_resp(self, resp, addr, 'nm', 'write')

        data_as_int = int.from_bytes(data, self._ctx.arch.endianness)
        data_input = '{:x}\n'.format(data_as_int)
        self._ctx.console.write(data_input)

        resp = self._ctx.console.read()
        resp = self._ctx.console.strip_echoed_input(data_input, resp)

        _verify_mm_nm_resp(self, resp, addr, 'nm', 'write')

        self._ctx.interrupt()

    def _teardown(self):
        self._ctx.interrupt()

# TODO: class MtestMemoryWriter


# Register declared Operation
Operation.register(MdMemoryReader, MmMemoryReader,
                   MmMemoryWriter, MwMemoryWriter,
                   NmMemoryWriter, NmMemoryWriter)
