# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements ReverseCRC32Hunter
"""

import multiprocessing
import queue
import sys

from copy import copy
from datetime import datetime
from importlib import import_module
from zlib import crc32

from .hunter import Hunter, HunterResultNotFound

from .. import log
from ..progress import Progress
from ..revcrc32 import reverse_crc32_4bytes
from ..stratagem import Stratagem, StratagemCreationFailed


class ReverseCRC32Hunter(Hunter):
    """
    The ReverseCRC32Hunter searches for CRC32 preimages in order to allow the U-Boot ``crc32``
    console command to be exploited as an arbitrary memory write primitive that produces
    a payload 4-bytes at a time.

    It effectively answers the question, *"What series of CRC32 operations would I need to
    perform to produce my desired binary payload?"* This answer is provided in the form a
    :py:class:`~depthcharge.Stratagem`, which is in turn used by the
    :py:class:`~depthcharge.memory.CRC32MemoryWriter` to perform the actual memory writes.


    **Constructor**

    The constructor conforms the :py:class:`~depthcharge.hunter.Hunter` definition and
    supports two additional keyword arguments.

    The *endianness* keyword argument specifies the byte order of the target
    device. It defaults to ``sys.byteorder``, which may not match your target. It
    can be specified as either ``'big'`` or ``'little'``.

    A *revlut_maxlen* keyword argument can be used to override the maximum size of
    individual reverse lookup table (RLUT) entries. The default value is ``256``.

    In general, increasing *revlut_maxlen* value uses more host memory when attempting
    to find a CRC32 preimage, increasing the likelihood of success. The lower
    limit of this value is 1 and its upper bound is defined by the size of
    *data*. Continue reading to get a better understanding of what exactly this
    parameter controls.


    **Implementation Details**

    The implementation of :py:class:`~.ReverseCRC32Hunter` leverages the malleability property of CRC32 --
    just one reason why it is never suitable for validation of data sucseptible to data forgery or
    tampering threats. :py:class:`.ReverseCRC32Hunter` uses a simplification of the technique
    presented in Listing 6 of the paper listed below. In our simplified case we're effectively "appending"
    4 bytes to a zero-length input to achieve a chosen CRC32 output. The value we end up "appending"
    is the 4-byte inverse of our chosen CRC32 output. This simplified algorithm implementation
    resides in `depthcharge/revcrc32.py
    <https://github.com/nccgroup/depthcharge/blob/main/python/depthcharge/revcrc32.py>`_.

    | *Reversing CRC - Theory and Practice*
    | by Martin Stigge, Henryk Plötz, Wolf Müller, Jens-Peter Redlich
    | HU Berlin Public Report, SAR-PR-2006-05, May 2006
    | Download: `PDF`_ (`Mirror`_)

    It is not necessarily the case, however, that the 4-byte inverse of our desired CRC32 value exists
    within a given ROM or memory dump (i.e., our domain of potential CRC32 inputs). Instead, we
    iteratively perform this reverse CRC32 operation on each 4-byte result until we find an input
    that does. When later writing memory using the `crc32` U-Boot console command (via
    :py:class:`~depthcharge.memory.CRC32MemoryWriter`), each iteration incurs some amount of serial
    console overhead execution time on the target device. When focusing only on 4-byte inputs, this
    can result in extraordinarily long execution times.

    To reduce execution time on the target (i.e. the number of CRC32 iterations
    performed) we can make a trade off in the form of increased  memory consumption on our host
    machine at the time when the
    :py:class:`~depthcharge.Stratagem` (intended for use with
    :py:class:`~depthcharge.memory.CRC32MemoryWriter`) is being created. To achieve this, we
    use a reverse-lookup table (RLUT) that maps CRC32 values to the shortest byte sequence in
    our input data that produces them.

    When the :py:class:`~.ReverseCRC32Hunter` constructor is invoked it will produced this RLUT.
    This will generally take some time, so a progress bar and ETA is shown.

    The RLUT construction is performed over the constructor's *data* argument (excluding any
    regions specified by the *gaps* keyword argument) for a sliding windows of
    size N. This is repeated for all values of N in the inclusive range shown below.

    .. code-block:: text

        [1, min(revlut_maxlen, len(data)) ]

    As shown above, This is where the *revlut_maxlen* keyword argument described earlier comes into
    play.  In general, results will be "better" with a larger *revlut_maxlen* value. The "best"
    value is one maximizes RAM utilization on one's host (without triggering a
    :py:exc:`MemoryError`, of course). The memory requirements (roughly) grow cubically with respect
    to this parameter. Bear in mind that the memory consumption of these RLUTs are on the order of GiB.

    Below is an visual example of this process, with a simplified 4-iteration solution. The left
    side shows the path from a desired payload back to a byte sequence present in the input data.
    The right side denotes the runtime sequence of CRC32 operations performed on the target
    device to produce a 4-byte portion of the desired payload.

    .. image:: ../../images/crc32-stratagem.png
        :align: center

    To produce an N-length payload (where N is divisible by 4), the whole process is repeated
    for each 4-byte word in the desired payload. Depthcharge makes two simplifying assumptions:

    1. The input data is static; it does not change at runtime.
    2. The location where payloads are written does not overlap the input data.

    Both of these are reasonable assumptions; the input data can be carved to meet these requirements,
    or the :py:class:`~.ReverseCRC32Hunter` constructor can be invoked with the *gaps=* keyword
    to exclude memory regions as needed. Under these assumptions, each 4-byte word in the produced
    output can be computed in parallel.  Depthcharge uses Python's ``multiprocessing`` module
    to distribute tasks to multiple workers, with a default worker count equal to the system's
    CPU count.

    Finally, one additional optimization is used to reduce the total number of CRC32 operations
    that the need to be performed on a target device at runtime. Envision a case where a 4-byte
    sequence ``X = [aa bb cc dd]`` occurs 5 times within a payload, and the
    produced :py:claske
    s:`~depthcharge.Stratagem` requires 3,500 CRC32 iterations produce a single
    instance of the 4-byte value *X*. The naive approach would be to perform a total of 17,500 CRC32 operations to
    write all 5 copies of X, 80% of which are redundant. Therefore, to eliminate this unnecessary
    overhead, :py:meth:`~.ReverseCRC32Hunter.build_stratagem()` identifies the *unique* 4-byte
    words in a payload, and distributes only these to the parallel workers.

    When a result is produced for a word occurring only once in the desired payload, no additional
    behavior is necessary. However, if a word (*X*) occurs multiple times, the produced
    :py:class:`~depthcharge.Stratagem` entry is split into multiple entries.

    1. The produced Stratagem is appended as-is, but with the *iterations* value reduced by 1.
       The in-progress result is written to the payload location for this reduced number of
       iterations.

    2. For each of the 4 remaining occurrences of *X*, a special Stratagem entry is created.
       Instead of having a *src_addr* pointing to an address within the input data, it instead has
       a *tsrc_off* value that denotes that the input can be found at the location where
       the result of Step 1 was written. Only a single iteration is required to write produce X.

    3. A "finalizing" Stratagem entry is appended that performs one last CRC32 operation on the
       location storing the result of Step 1, with the output written to the same address.

    With this approach, the same desired payload can be achieved, but with only 3,504 CRC32
    operations.

    To avoid confusion, Stratagem entries produced by :py:class:`~.ReverseCRC32Hunter` do
    not contain a *src_off* key.  In cases where a *tsrc_off* (Target buffer source offset) is
    used, *src_addr* is set to ``-1``.


    **Example**

    If you still have a healthy dose of skepticism about the high-level approach used here, worry not!
    An example demonstrating this algorithm is provided in `examples/reverse_crc32_algo_poc.py
    <https://github.com/nccgroup/depthcharge/blob/main/python/examples/reverse_crc32_algo_poc.py>`_
    This example uses :py:meth:`~.Hunter.build_stratagem()` to produce the following string, using
    Edgar Allen Poe's *The Raven* as input data. In order to allow this example to be used without
    a target device, the :py:class:`~depthcharge.Stratagem` is "executed" by simply making calls
    to ``zlib.crc32``, rather than by passing the Stratagem to
    :py:class:`~depthcharge.memory.CRC32MemoryWriter()`.

    *Payload String*:

    .. centered:: ``"NCC Group - Depthcharge \\n<https://github.com/nccgroup/depthcharge>"``

    .. _PDF: https://sar.informatik.hu-berlin.de/research/publications/SAR-PR-2006-05/SAR-PR-2006-05_.pdf
    .. _Mirror: https://web.archive.org/web/20191010094138/https://sar.informatik.hu-berlin.de/research/publications/SAR-PR-2006-05/SAR-PR-2006-05_.pdf

    """

    def __init__(self, data: bytes, address: int, start_offset=-1, end_offset=-1, gaps=None, **kwargs):
        super().__init__(data, address, start_offset, end_offset, gaps, **kwargs)

        # TODO: callers should be providing this based upon target arch endianness
        self._endianness = kwargs.get('endianness', sys.byteorder)

        # The functionality provided by revcrc32.reverse_crc32_4bytes() is used
        # to "walk backwards" in a potential chain of CRC32 operations,
        # each performed over 4-byte inputs, until we find the start of the
        # chain via our "reverse LUT" (revlut).
        #
        # These should never be necessary unless U-Boot changes the CRC32
        # algorithm in use. However I've included these kwargs just to be a
        # good neighbor to anyone who decides to yoink this code into some
        # other fun project. (That's why it's open source, go for it!)
        #
        # Check out the paper linked in the revcrc32.py pydocs to understand
        # what each of these are and how to determine them.
        self._poly     = kwargs.get('poly',     0xedb88320)
        self._invpoly  = kwargs.get('invpoly',  0x5b358fd3)
        self._initxor  = kwargs.get('initxor',  0xffffffff)
        self._finalxor = kwargs.get('finalxor', 0xffffffff)

        revlut_maxlen = kwargs.get('revlut_maxlen', 256)
        revlut_maxlen_err = 'revlut_maxlen must be an integer > 0'
        if not isinstance(revlut_maxlen, int):
            raise TypeError(revlut_maxlen_err)

        if revlut_maxlen < 1:
            raise ValueError(revlut_maxlen_err)

        # Just for error reporting later
        self._revlut_maxlen = revlut_maxlen

        # Range of CRC32 operation sizes we'll include in our reverse LUT
        self._revlut_range = list(range(1, revlut_maxlen + 1))

        # Search iterator over data, considering gaps we should skip
        self._data_range = self._gapped_range_iter(None, start_offset, end_offset)

        # Populates self._revlut
        # TODO: Allow this to be pickled and loaded/saved
        self._build_revlut()

    # We take on a bit more logical complexity in this implementation in
    # the interest of reducing redundant CRC32 computations. This is achieved
    # through the use of zlib.crc32()'s second `value` argument.
    def _build_revlut(self):
        self._revlut = {}

        progress = Progress.create(len(self._data_range), desc='Creating Reverse CRC32 LUTs')

        min_len = self._revlut_range[0]
        for i in self._data_range:
            data_left = self._data_range.stop - i
            if data_left < min_len:
                break

            curr_state = 0
            prev_len   = 0

            for input_len in self._revlut_range:
                if data_left < input_len:
                    break

                if self._is_in_gap(i, input_len):
                    continue

                data = self._data[i + prev_len:i + input_len]
                curr_state = crc32(data, curr_state)

                # Insert if...
                #   We don't have a corresponding CRC -> (offset, len) mapping yet
                #       OR
                #   This new mapping requires less input data
                if (curr_state not in self._revlut) or (input_len < self._revlut[curr_state][1]):
                    self._revlut[curr_state] = (i, input_len)

                prev_len = input_len
            progress.update(1)

        progress.close()

    def find(self, target, start=-1, end=-1, **kwargs) -> dict:
        """
        Search for a sequence of CRC32 operations, performed over the *data* provided to the
        :py:class:`~.ReverseCRC32Hunter` construtor that results in *target*

        That *target* parameter must be a ``bytes`` object with a length of 4.

        The *start* and *end* parameters operate according to
        :py:meth:`Hunter.find() <depthcharge.hunter.Hunter.find>`.

        A *max_iterations* keyword argument can be provided to limit the maximum number of
        operations to allow when searching for a sequence of CRC32 operations that result in the
        *target* value. This default is to 4096.

        As discussed in the :py:class:`~.ReverseCRC32Hunter` "*Implementation Details*" section,
        increasing the allowed maximum number of iterations will increase the amount of time required to
        deploy a payload with :py:class:`~depthcharge.writer.CRC32.MemoryWriter`. To keep this
        reasonably low, the *revlut_maxlen* parameter passed to the :py:class:`~.ReverseCRC32Hunter`
        constructor may need to be increased.

        When a result is found, it is returned in a dictionary that has the keys described
        in :py:meth:`Hunter.find() <depthcharge.hunter.Hunter.find>`, and an additional
        *iterations* key.

        In the event that no result is found, a :py:exc:`~depthcharge.hunter.HunterResultNotFound`
        exception is raised.

        """
        self._validate_offsets(None, self._start_offset, self._end_offset)

        max_iterations = kwargs.get('max_iterations', 4096)

        if isinstance(target, bytes):
            if len(target) != 4:
                err = 'Expected 4-byte target, got {:d} bytes'
                raise ValueError(err.format(len(target)))

            # FIXME: Probably pull from arch?
            target = int.from_bytes(target, self._endianness)

        elif not isinstance(target, int):
            err = 'Target CRC32 output must be an int or bytes, got {:s}'
            raise TypeError(err.format(type(target).__name__))

        for curr_iter in range(1, max_iterations + 1):
            result = self._do_search(target, start, end, curr_iter, max_iterations)
            if isinstance(result, dict):
                return result

            target = result

        err  = 'No results for target=0x{:08x}, revlut_maxlen={:d} after {:d} iterations. '
        err += 'Try increasing revlut_maxlen and/or max_iterations.'
        raise HunterResultNotFound(err.format(target, self._revlut_maxlen, curr_iter))

    def _do_search(self, target, _start, _end, curr_iter, _max_iterations):
        try:
            (offset, length) = self._revlut[target]

            return {
                'src_off': offset,
                'src_addr': self._address + offset,
                'src_size': length,
                'iterations': curr_iter,
            }
        except KeyError:
            pass

        # Returning another target (rather than a dict) signals to the caller that we've
        # walked one more CRC32 operation backwards in the chain.
        new_target = reverse_crc32_4bytes(target)
        return new_target

    def build_stratagem(self, target_payload: bytes, start=-1, end=-1, **kwargs):
        """
        Given a target binary payload, return the sequence of CRC32 operations
        that can be performed to create this payload, one 4-byte word at time.
        This result is returned in the form of a :py:class:`~depthcharge.Stratragem`.
        Refer to the :py:class:`~.ReverseCRC32Hunter` *Implementation Details*
        section for details about how this works.

        The `target_payload` must be a multiple of 4 bytes.
        Otherwise, an :py:class:`~depthcharge.StratagemCreationFailed` exception is raised.

        This implementation assumes that the location where the `target_payload` is
        being written **does not** overlap the memory space being searched for
        viable operations. It is the user's responsibility to provide a `gaps` list
        to the constructor to avoid this.

        If a :py:class:`~depthcharge.Stratagem` for the desired payload could not be created
        because no solution was found, a :py:class:`~depthcharge.hunter.HunterResultNotFound`
        exception is raised.

        Optional keyword arguments:

        * *max_iterations* - Maximum number of CRC32 operations to allow per 4-byte word.
          Default: 4096

        * *num_procs* - Number of concurrent processes to use during search.
          Default: System's CPU count


        :Tip: When possible, consider using ROM code as the Hunter's input data.  This will allow
          :py:class:`~depthcharge.Stratagem` to remain usable across any changes in the target
          system's U-Boot build.


        """
        t_start = datetime.now()

        max_iterations = kwargs.get('max_iterations', 4096)
        num_procs = kwargs.get('num_procs', -1)

        target_payload_len = len(target_payload)
        if (target_payload_len % 4) != 0 or (target_payload_len == 0):
            err = 'Target payload size must be a multiple of 4, got {:d} bytes'.format(target_payload_len)
            raise StratagemCreationFailed(err.format(4, target_payload_len))

        if num_procs < 1:
            num_procs = multiprocessing.cpu_count()

        # Reduce the target payload (and thereby the workload of this
        # long-running operation) to the unique word values that occur within
        # our target payload.
        #
        # This dictionary maps word_value -> [associated offsets within payload]
        workload = {}

        for i in range(0, target_payload_len, 4):
            word = target_payload[i:i + 4]
            try:
                workload[word].append(i)
            except KeyError:
                workload[word] = [i]

        total_workload = len(workload)
        progress = Progress.create(total_workload, desc='Creating CRC32 Stratagem')

        # Use dynamic import to avoid creating circular static imports, as both
        # the hunter and the writer need to reference each other's classes.
        crc32_writer = import_module('..memory.crc32', 'depthcharge.memory')
        stratagem = Stratagem(crc32_writer.CRC32MemoryWriter)

        with multiprocessing.Manager() as manager:
            results = manager.Queue()
            dbg_msg = 'Posted work for dst_off={:s}, max_iterations={:d}'
            with multiprocessing.Pool(num_procs) as pool:
                for target, offsets in workload.items():
                    args = (target, offsets, start, end, max_iterations, results)
                    log.debug(dbg_msg.format(str(offsets), max_iterations))
                    pool.apply_async(self._do_stratagem_work, args, error_callback=_err_cb)
                pool.close()

                # This is a memory-heavy operation. Try to relinquish what we can.
                #
                # A big time-memory tradeoff that could be made is the use of
                # a shared revlut dict (via the manager.dict) rather than allowing
                # each child process to work with a copy of the huge self._revlut.
                # Food for thought. Might be worth doing some perf measurements
                # and considering an explicit gc.collect().
                workload = None  # lgtm [py/unused-local-variable]

                results_gathered = 0
                while results_gathered < total_workload:
                    try:
                        result = results.get(True, 0.5)
                        log.debug('Got result: ' + str(result))
                    except queue.Empty:
                        continue

                    dst_offsets = result[0]
                    entry       = result[1]

                    if not isinstance(entry, dict):
                        pool.terminate()
                        raise entry

                    # Remove find() result that we don't care about.
                    # This is not part of the CRC32Writer Stratagem spec.
                    del entry['src_off']

                    if len(dst_offsets) == 1:
                        # Target word occurs once in our payload.
                        # Nothing special to do here.
                        entry['dst_off'] = dst_offsets[0]
                        stratagem.append(entry)

                    elif entry['iterations'] == 1:
                        # Easily handled special case: word occurs multiple time
                        # in target payload, but there's only 1 iteration.
                        # Just update the destination offset.
                        for dst_offset in dst_offsets:
                            e = copy(entry)
                            e['dst_off'] = dst_offset
                            stratagem.append(e)
                    else:
                        # Otherwise, we have multiple occurrences of the same word
                        # in our payload, for which we have an optimization.
                        #
                        # The naive implementation here is to simply do what
                        # we did above, but that means we'd burn a lot of time
                        # performing unnecessary CRC32 operations when writing
                        # to a target device (over a slow serial port).
                        #
                        # We can significantly reduce the number of
                        # deployment-time operations here.
                        #
                        # Consider a word value `w` that occurs multiple times
                        # in the target payload at address `A`, `B`, `C`, ...
                        #
                        # Instead of performing N iterations of CRC32 every
                        # time we want to write to a target offset, we can
                        # instead perform N-1 operations for the first
                        # occurrence of `w`, whose output is located at some
                        # address `A`.
                        #
                        # Then, for all other locations containing this
                        # duplicate word (e.g. address `X`), we can perform just 1
                        # CRC32 operation: *X = CRC32(*A)
                        #
                        # Finally, we perform the last iteration `A`:
                        #   *A = CRC32(*A)
                        #
                        for i, dst_off in enumerate(dst_offsets):
                            e = copy(entry)

                            if i == 0:  # Perform N-1 iterations at first occurrence
                                e['iterations'] -= 1
                            else:       # Address `X`
                                e['src_addr'] = -1
                                e['tsrc_off'] = dst_offsets[0]
                                e['src_size'] = 4
                                e['iterations'] = 1

                            e['dst_off'] = dst_off
                            stratagem.append(e)

                        # Finalize the result at our occurrence (`A`)
                        e = copy(entry)
                        e['src_addr'] = -1
                        e['tsrc_off'] = dst_offsets[0]
                        e['src_size'] = 4
                        e['iterations'] = 1
                        e['dst_off'] = dst_offsets[0]
                        stratagem.append(e)

                    results_gathered += 1
                    progress.update(1)
                pool.join()
        progress.close()

        n_entries = len(stratagem)
        iterations = [entry['iterations'] for entry in stratagem]
        total_ops = sum(iterations)
        max_iter = max(iterations)

        t_stop = datetime.now()
        t_elapsed = t_stop - t_start

        msg = 'CRC32Writer Stratagem created{:s} in {:s}\n\t'
        msg += '{:d} entries, {:d} total operations, largest operation is {:d} iterations'
        payload_name = ' from ' + kwargs.get('payload_name') if 'payload_name' in kwargs else ''
        msg = msg.format(payload_name, str(t_elapsed), n_entries, total_ops, max_iter)
        log.note(msg)

        stratagem.comment = msg
        return stratagem

    def _do_stratagem_work(self, target, offsets, start, end, max_iter, work_queue):
        try:
            result = self.find(target, start, end, max_iterations=max_iter)
        except Exception as e:  # pylint: disable=W0703
            # We want to propagate the exception back to main thread of execution.
            # Hence, we really do want to catch the "overly general" Exception here
            # and suppress PyLint's complaint.
            result = e

        work_queue.put((offsets, result))


def _err_cb(err):
    log.error(str(err))
