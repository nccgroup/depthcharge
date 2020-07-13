# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements CpHunter
"""

from importlib import import_module

from .. import log
from ..operation import OperationNotSupported
from ..stratagem import Stratagem, StratagemCreationFailed

from .hunter import Hunter
from ..progress import Progress


def _lcss(data: bytes, target: bytes) -> tuple:
    """
    Longest common substring implementation per pseudocode found at:

    <https://en.wikipedia.org/wiki/Longest_common_substring_problem>

    Returns (data index, target_index, common substring)
    """

    table = {}
    longest_loc = None
    longest_substr = 0

    for i in range(1, len(data) + 1):
        for j in range(1, len(target) + 1):

            if data[i-1] == target[j-1]:
                curr_len = table.get((i-1, j-1), 0) + 1
                table[(i, j)] = curr_len

                if curr_len > longest_substr:
                    longest_substr = curr_len
                    longest_loc = (i, j)

    if longest_substr < 1:
        raise ValueError('No common substring found for: ' + str(target))

    di, ti = longest_loc
    return (di - curr_len, ti - curr_len, curr_len)


class CpHunter(Hunter):
    """
    The CpHunter class searches for a series of ``cp`` command invocations that can
    be performed to result in the desired payload.

    """

    def find(self, target, start=-1, end=-1, **kwargs):
        """
        CpHunter does not implement this method.
        Raises :py:exc:`.OperationNotSupported`.
        """
        raise OperationNotSupported

    def finditer(self, target, start=-1, end=-1, **kwargs):
        """
        CpHunter does not implement this method.
        Raises :py:exc:`.OperationNotSupported`.
        """
        raise OperationNotSupported

    def build_stratagem(self, target_payload: bytes, start=-1, end=-1, **kwargs):
        """
        Produce a :py:class:`~depthcharge.Strategem` for use with
        :py:class:`~depthcharge.writer.CpMemoryWriter`. This implementation attempts to reduce the total
        number of cp operations by searching for common substrings.
        """

        # Prefer longer data ranges
        data_ranges = sorted(self._split_data_offsets(), key=len, reverse=True)
        workload = [range(0, len(target_payload))]

        # Use dynamic import to avoid creating circular static imports
        cp_writer = import_module('..memory.cp', 'depthcharge.memory')

        stratagem = Stratagem(cp_writer.CpMemoryWriter)
        desc = 'Creating CpMemoryWriter Stratagem'
        show = kwargs.get('show_progress', True)
        progress = Progress.create(len(target_payload), desc=desc, show=show)

        while workload:
            # Target work
            twork = workload.pop(0)
            log.debug('Current work: [{:d}, {:d})'.format(twork.start, twork.stop))

            tslice = target_payload[twork.start:twork.stop]

            fail = 0

            for r in data_ranges:
                try:
                    dslice = self._data[r.start:r.stop]

                    # Don't run the entire LCSS for just 1 byte...
                    if len(tslice) == 1:
                        src_off = dslice.index(tslice[0])
                        entry = {
                            'src_addr': self._address + r.start + src_off,
                            'src_size': 1,
                            'dst_off':  twork.start,
                        }

                        stratagem.append(entry)
                        progress.update(1)
                        log.debug('src[{:d}] -> dst[{:d}]'.format(r.start + src_off, twork.start))
                        continue

                    # Otherwise search for longest common substring
                    di, ti, size = _lcss(dslice, tslice)

                    di += r.start
                    ti += twork.start

                    entry = {
                        'src_addr': self._address + di,
                        'src_size': size,
                        'dst_off':  ti,
                    }

                    stratagem.append(entry)
                    progress.update(size)
                    log.debug('Found substr len={:d}: src={:d}, dst={:d}'.format(size, di, ti))

                    # Carve out any remaning work
                    if twork.start < ti:
                        msg = 'Enqueued work: [{:d}, {:d})'
                        log.debug(msg.format(twork.start, ti))
                        workload.append(range(twork.start, ti))

                    if (ti + size) < twork.stop:
                        msg = 'Enqueued work: [{:d}, {:d})'
                        log.debug(msg.format(ti + size, twork.stop))
                        workload.append(range(ti + size, twork.stop))

                    # Start any new work at longer data ranges
                    break

                except ValueError as e:
                    fail += 1
                    if fail == len(data_ranges):
                        progress.close()
                        raise StratagemCreationFailed(str(e))

        progress.close()
        return stratagem
