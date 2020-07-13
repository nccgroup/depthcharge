# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements ConstantHunter
"""
from .hunter import Hunter


class ConstantHunter(Hunter):
    """
    This is a simple :py:class:`~.hunter.Hunter` that searches for fixed data values
    (of type ``bytes``).

    Example use-cases include searching for file format "magic" values (e.g. Device Tree's
    ``d00dfeed``), tables (e.g., CRC32, SHA1, SHA256 LUTs), or opcodes near code or data of
    interest.

    Its constructor and methods are implemented according to the descriptions in
    :py:class:`.Hunter`.
    """

    def _search_at(self, target, start, end, **_kwargs):
        tlen = len(target)
        if 0 < end < (start + tlen):
            return None

        if target == self._data[start:start + len(target)]:
            return (start, len(target))

        return None
