# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
The :py:class:`.MemoryPatch` and :py:class:`.MemoryPatchList` classes are
used by :py:meth:`~depthcharge.Depthcharge.patch_memory` to described desired
changes to memory regions.
"""


class MemoryPatch:
    """
    A :py:class:`.MemoryPatch` describes a change to apply to a contiguous memory region.

    An optional *expected* parameter can be used to denote the value expected
    to be present at the specified address befor a change is made. If provided, the size of
    *expected* must be equal to that of *value*.

    The *desc* string is used to describe the change. It should be concise and
    suitable for printing to a user.

    In addition to this constructor, a :py:class:`.MemoryPatch` can be created using
    :py:meth:`from_tuple()` or :py:meth:`from_dict()`. The values provided at creation-time
    can be later accessed using the following properties.

    """

    def __init__(self, addr: int, value: bytes, expected: bytes = None, desc=''):
        self._addr = addr
        self._val = value
        self._exp = expected
        self._desc = desc

        if expected is not None and len(expected) != len(value):
            err = 'Expected data is {:d} bytes, but patch value is {:d} bytes'
            raise ValueError(err.format(len(expected), len(value)))

    @property
    def address(self) -> int:
        """
        Address that the patch should be applied to
        """
        return self._addr

    @property
    def value(self) -> bytes:
        """
        Data to write to the selected address
        """
        return self._val

    @property
    def expected(self) -> bytes:
        """
        Data expected to reside at selected address, prior to performing write
        """
        return self._exp

    @property
    def description(self) -> str:
        """
        Patch description string
        """
        suffix = ' @ 0x{:08x}'.format(self._addr)
        if self._desc is None:
            return 'Patch' + suffix

        return self._desc + suffix

    @classmethod
    def from_tuple(cls, src: tuple):
        """
        Create a :py:class:`.MemoryPatch` object from a tuple with the following elements:

        +-------+-------+----------------------------------------------------------------------+
        | Index | Type  | Description                                                          |
        +=======+=======+======================================================================+
        |   0   | int   | Address to apply patch to                                            |
        +-------+-------+----------------------------------------------------------------------+
        |   1   | bytes | Data to write to the target address                                  |
        +-------+-------+----------------------------------------------------------------------+
        |   2   | bytes | Value expected to reside at target address. Optional; may be ``None``|
        +-------+-------+----------------------------------------------------------------------+
        |   3   |  str  | Description of patch. Optional may be ``None`` or empty string.      |
        +-------+-------+----------------------------------------------------------------------+

        """
        src_len = len(src)
        if src_len == 4:
            exp  = src[2]
            desc = src[3]
        elif src_len == 3:
            exp  = src[2] if isinstance(src[2], bytes) else None
            desc = src[2] if isinstance(src[2], str)   else None
        elif src_len == 2:
            exp  = None
            desc = None
        else:
            err = 'Invalid number of elements ({:d})'
            raise ValueError(err.format(src_len))

        return cls(src[0], src[1], exp, desc)

    @classmethod
    def from_dict(cls, src: dict):
        """
        Create a MemoryPatch object from a dictionary with keys *address*, *value*,
        *expected* and *description*. Refer to the corresponding parameters of
        :py:class:`.MemoryPatch` constructor.

        """
        addr = src['address']
        val  = src['value']
        exp  = src.get('expected', None)
        desc = src.get('description', None)

        return cls(addr, val, exp, desc)


class MemoryPatchList:
    """
    A :py:class:`.MemoryPatchList` stores a sequence of :py:class:`.MemoryPatch` objects.

    Entries may be accessed by index and iterated over.
    (e.g. ``for patch in memory_patch_list: ...``)

    """

    def __init__(self, patch_list=None):
        self._list = []

        if patch_list is None:
            patch_list = []

        # Use append() to perform conversions as-needed
        for p in patch_list:
            self.append(p)

    def append(self, patch):
        """
        Append a :py:class:`.MemoryPatch` to the list. The *patch* argument may
        also be specified as a ``dict`` or ``tuple``, populated according to :py:meth:`.MemoryPatch.from_dict()`
        or :py:meth:`.MemoryPatch.from_tuple()`.
        """
        if isinstance(patch, MemoryPatch):
            pass
        elif isinstance(patch, tuple):
            patch = MemoryPatch.from_tuple(patch)
        elif isinstance(patch, dict):
            patch = MemoryPatch.from_dict(patch)
        else:
            actual = type(patch).__name__
            raise TypeError('Expected MemoryPatch or dict, got: ' + actual)

        self._list.append(patch)

    def __getitem__(self, idx):
        return self._list[idx]

    def __len__(self):
        return len(self._list)
