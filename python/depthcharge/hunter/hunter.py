# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Defines the Hunter base class.
"""

from ..progress import Progress
from ..stratagem import StratagemNotRequired


class HunterResultNotFound(Exception):
    """
    It may be the case that a Hunter cannot find or produce a result.
    :py:exc:`HunterResultNotFound` is raised to indicate in this situation and provides more context
    within its message text.

    In general, potential reasons this exception may be thrown include:

    * The requested item is not present in the provided data.
    * Provided parameters overconstrained the search.
      Relaxing constraints may be necessary to yield a result.

    """


class _GappedRangeIter:
    """
    Not part of the Depthcharge API - do not use external to this file.

    Iterator for ranges, skipping non-overlapping gaps.
    """
    def __init__(self, full_range, gaps):
        self.start = full_range.start
        self.stop  = full_range.stop

        self.i     = self.start
        self.gaps  = gaps

        # This assumes non-overlapping gaps, which we do not enforce.
        # TODO: Add a check here and reject overlapping gaps or coalesce gaps up front.
        self.length = self.stop - self.start
        for gap in gaps:
            self.length -= len(gap)

    def __iter__(self):
        return self

    def __len__(self):
        return self.length

    def __next__(self):
        gap_resolved = False
        while not gap_resolved:
            prev_i = self.i

            for gap in self.gaps:
                if self.i in gap:
                    self.i = gap.stop
                    break

            # We're done when there's no changes
            gap_resolved = (prev_i == self.i)

        if self.i >= self.stop:
            raise StopIteration

        ret = self.i
        self.i += 1
        return ret


class Hunter:
    """
    The :py:class:`.Hunter` class provides a foundation upon which specific Hunter implementations can be built.

    It provides default :py:meth:`find()` and :py:meth:`finditer()` implementations, and defines
    a fallback :py:meth:`.build_stratagem()` implementation that raises
    :py:exc:`~depthcharge.StratagemNotRequired`.

    A Hunter subclass implementation can either:

    1. Implement a private :py:meth:`_search_at()` and allow the base implementation to do the rest.
    2. Override these methods entirely.

    When adding a new Hunter, the former is preferable because offset validation logic,
    support for gaps in the search range (to skip), and displaying progress bars during
    the search all come for free.


    **Constructor Arguments**:

    * *data* - Memory or flash dump data to search

    * *address - Memory address corresponding to the start of *data*

    * *start_offset* -
      Offset within data to begin searching. A negative value implies 0 (default).

    * *end_offset* -
      Inclusive upper bound offset for the search. A negative value implies the last
      element in  *data*.

    * *gaps* -
      A ``list`` of regions within *data* that should be skipped during searches.
      (*One may want to exclude regions of data actively modified by the running bootloader.*)
      List entries may be either ``(address, length)`` tuples of ``range`` objects.
      **Caller-provided gaps must not overlap.**

    |
    """

    # Subclasses may define this to briefly describe their search target,
    # for use in search progress status updates
    _target_desc = None

    def _describe_search(self, start, **_kwargs):
        address = self._address + start

        if self._target_desc is None:
            return 'Searching at 0x{:08x}'.format(address)

        return 'Searching for {:s} at 0x{:08x}'.format(self._target_desc, address)

    def _validate_offsets(self, target, start, end):
        dlen = len(self._data)

        if start > end:
            err = 'Start index ({:d}) must be <= end ({:d})'
            raise IndexError(err.format(start, end))

        if start < 0 or start >= dlen:
            err = 'Start index ({:d})) outside bounds [0, {:d}]'
            raise IndexError(err.format(start, dlen))

        if end < 0 or end >= dlen:
            err = 'End index ({:d}) outside of bounds [{:d}, {:d}]'
            raise IndexError(err.format(end, start, dlen))

        if target is None:
            return

        tlen = len(target)

        if (end - start + 1) < tlen:
            err = 'Target size ({:d}) exceeds size of search range {:d} -> ([{:d}, {:d}])'
            raise IndexError(err.format(tlen, end - start, start, end))

    def __init__(self, data: bytes, address: int, start_offset=-1, end_offset=-1, gaps=None, **kwargs):

        if not hasattr(self, '_search_at') and self.find is Hunter.find:
            err = self.__class__.__name__ + ' is missing _search_at() method'
            raise NotImplementedError(err)

        gaps = [] if gaps is None else gaps

        self._data          = data

        self._start_offset  = 0 if start_offset < 0 else start_offset
        self._end_offset    = len(data) - 1 if end_offset < 0 else end_offset
        self._validate_offsets(None, self._start_offset, self._end_offset)

        self._address       = address
        self._end_address   = address + self._end_offset

        # Normalize our gap list to range objects in terms of OFFSET, not address.
        #
        # User-facing code works with addresses, but internal code uses offsets
        # with respect to relative offsets within a data blob
        self._gaps = []
        for gap in gaps:
            if isinstance(gap, tuple):
                start = gap[0] - self._address
                stop  = start + gap[1]
                gap = range(start, stop, 1)
            elif isinstance(gap, range):
                gap = range(gap.start - self._address, gap.stop - self._address)
            else:
                err = 'Unexpected gap type: ' + type(gap).__name__
                raise TypeError(err)

            self._gaps.append(gap)
        self._gaps = sorted(self._gaps, key=lambda g: g.start)

        # Progress handle used to provide feedback about search status
        # See _init_progress() and _deinit_progress()
        self._progress = None

    def _gapped_range_iter(self, target, start=-1, end=-1):
        """
        Non-API internal method; subject to change.

        Returns an offset (not address) iterator over a target's search range,
        excluding any specified gaps, from [start, end].

        Note: this is different than Python's range() which is [start, stop)!)

        Entries in the gaps list must be specified as (address, length)
        tuples or range() objects (defined by address, *not* offset).
        The reason for this asymmetry is that (API) user-facing code shall
        operate in terms of the address ranges of memory dumps/payloads,
        while this internal search code operates of data BLOB offsets.
        """
        start = self._start_offset if start < 0 else start
        end   = self._end_offset if end < 0 else end
        self._validate_offsets(target, start, end)

        # range() has an exclusive upper limit [start, end), but
        # our API presents inclusive offsets: [start_offset, end_offset]
        full_range = range(start, end + 1)
        if len(self._gaps) == 0:
            return full_range

        return _GappedRangeIter(full_range, self._gaps)

    def _split_data_offsets(self) -> list:
        """
        Return self._data split into valid data offset ranges, excluding gaps.
        """
        # TODO: Should be able to removed _GappedRangeIter entirely and just
        #       carve out gaps right from the get-go.
        #
        # FIXME: This assumes no overlaps.
        if not self._gaps:
            return [range(0, len(self._data))]

        ret = []
        start = 0
        end = len(self._data)

        # Gaps is already sorted by ascending start offset
        for gap in self._gaps:
            if start < gap.start:
                ret.append(range(start, gap.start))
                start = gap.stop
            elif start >= gap.start:
                start = gap.stop

        if start < end:
            ret.append(range(start, end))

        return ret

    @property
    def name(self) -> str:
        """
        Hunter class name
        """
        return self.__class__.name

    def _init_progress(self, start, end, **kwargs):
        # Don't bother with gaps in progress update. Trying to present it
        # would be unintuitive. It'll be obvious from a large progress jump.
        start = self._start_offset if start < 0 else start
        end   = self._end_offset if end < 0 else end

        show_progress = kwargs.get('show_progress', True)
        total_span    = end - start
        desc          = self._describe_search(start, **kwargs)

        self._progress = Progress.create(total_span, desc=desc,
                                         show=show_progress, unit='B')

    def _deinit_progress(self):
        self._progress.close()

    def _find_impl(self, target, start, end, **kwargs):

        search_range = self._gapped_range_iter(target, start, end)
        for i in search_range:
            # Constructor validates that _search_at exists. Below we suppress
            # pylint's 'Hunter has no _search_at' error.
            result = self._search_at(target, i, search_range.stop, **kwargs)  # pylint: disable=E1101

            # None implies that the implementation wishes for us to continue
            # iterating. Otherwise, it would have raised HunterResultNotFound
            # if it did a search of the entire range on its own and found nothing.
            if result is None:
                self._progress.update()
                continue

            found_offset = result[0]
            found_length = result[1]

            # Skip this if it's in a gap
            if self._is_in_gap(found_offset, found_length):
                self._progress.update()
                continue

            self._progress.update(found_length)

            try:
                extra_info = result[2]
            except IndexError:
                extra_info = {}

            ret = {
                'src_off':  found_offset,
                'src_addr': self._address + found_offset,
                'src_size': found_length,
                **extra_info,
            }

            return ret

        raise HunterResultNotFound()

    def _is_in_gap(self, offset, length):
        for gap in self._gaps:
            # This offset is an inclusive bound, but gap.stop is not
            end_offset = offset + length - 1

            if offset in gap:
                # Starts within gap
                return True

            if end_offset in gap:
                # Ends within gap
                return True

            if offset <= gap.start and end_offset >= (gap.stop - 11):
                # Passes through gap
                return True

        return False

    def find(self, target, start=-1, end=-1, **kwargs) -> dict:
        """
        Search for *target* within the Hunter's *data* (provided via the constructor)
        and return information about the first result encountered as a dictionary with the following
        keys-value pairs:

        +-----------+-----------+------------------------------------------------------------------+
        | Key (str) | Type      | Description                                                      |
        +===========+===========+==================================================================+
        | src_off   | int       | 0-based index into data where target was found                   |
        +-----------+-----------+------------------------------------------------------------------+
        | src_addr  | int       | Absolute address of the located target                           |
        +-----------+-----------+------------------------------------------------------------------+
        | src_size  | int       | Size of the located target, in bytes                             |
        +-----------+-----------+------------------------------------------------------------------+

        Subclasses of :py:class:`.Hunter` may return additional entries in their result dictionary.
        (*Refer to the specific subclass documentation for any additional entries.*)

        Note that the above key-value scheme is intentionally a consistent with that used in
        :py:class:`~depthcharge.Stratagem` entries, and the repective *Stratagem Specification*
        returned by an Operation's :py:meth:`stratagem_spec() <depthcharge.Operation.get_stratagem_spec>`
        method.

        The *start_offset* and *end_offset* parameters provided to the :py:class:`Hunter`
        constructor can be overridden using this method's *start* and *end* arguments, respectively.
        The default negative values mean, *"Use the offsets that the object was created with.*"

        A :py:exc:`HunterResultNotFound` exception is raised if the target could not be found.

        """
        try:
            self._init_progress(start, end,  **kwargs)
            return self._find_impl(target, start, end, **kwargs)
        finally:
            self._deinit_progress()

    def finditer(self, target, start=-1, end=-1, **kwargs):
        """
        Return an generator over all :py:meth:`find()` results for `target` in the
        data of interest.

        The *start* and *end* arguments, if greater than or equal to zero,
        can be used to override the *start_offset* and *end_offset* parameters
        provided to the :py:class:`.Hunter` constructor.

        **Example:**

        .. code:: python

            for result in my_hunter.finditer(my_target):
                offset = result['src_off']
                size   = result['src_size']
                hexstr = my_data[offset:offset + size].hex()

                msg = '{:d}-byte result found at 0x{:08x}: {:s}'
                print(msg.format(size, result['src_addr'], hexstr))

        """
        search_range = self._gapped_range_iter(target, start, end)
        curr_idx = search_range.start

        try:
            while True:
                # Allow find() to handle progress updates. If we do so here, we
                # risk writing to the screen when a calling script is trying
                # to print information as it becomes available from our generator.

                result = self.find(target, curr_idx, end, **kwargs)

                # Advance past prior result
                curr_idx = result['src_off'] + result['src_size']

                yield result

        except (IndexError, HunterResultNotFound):
            # Expected stop condition
            return
        finally:
            self._deinit_progress()

    def build_stratagem(self, target_payload: bytes, start=-1, end=-1, **kwargs):
        """
        Produce a :py:class:`~depthcharge.Stratagem` that can be used to create *target_payload*,
        given *data* (provided earlier via the :py:class:`.Hunter` constructor).

        The *start* and *end* parameters can be used to override the *start_offset* and *end_offset*
        parameters that the Hunter was created with. If left as negative values, the Hunter's
        defaults will be used.

        The nature of the resulting Stratagem is tightly coupled with the
        :py:class:`~depthcharge.Operation` it will be used by. Refer to specific implementations for
        more information, as well as any ``**kwargs`` that can be used to configure the Stratagem
        creation.

        If a particular Hunter does not produce Stratagem objects, invoking this method will
        raise a :py:exc:`~depthcharge.StratagemNotRequired` exception.
        """
        raise StratagemNotRequired(self.__class__.__name__ + ' does not produce a Stratagem')
