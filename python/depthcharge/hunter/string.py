# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements StringHunter
"""

import re
from functools import lru_cache

from .hunter import Hunter, HunterResultNotFound


@lru_cache(maxsize=32)
def _str_regex(pat=None, min_len=-1, max_len=-1, null_terminated=True):

    if null_terminated:
        min_len -= 1
        max_len -= 1

    if pat is None or len(pat) == 0:
        # All printable characters, plus '\t', ' ', '\r', '\n'
        pat = b'[\x09\x0a\x0d\x20-\x7e]'

        if min_len < 1:
            min_len = 1

        pat += b'{' + str(min_len).encode('ascii') + b','

        if max_len > 0 and max_len >= min_len:
            pat += str(max_len).encode('ascii')

        pat += b'}'

    if null_terminated and pat[-1] != b'\x00':
        pat += b'\x00'

    return re.compile(pat)


class StringHunter(Hunter):
    """
    The StringHunter can be used to search for NULL-terminated ASCII strings within a binary
    RAM or flash dump (i.e., *data* shoudl be of type ``bytes``), via regular expressions.

    As every good little reverse engineer knows, stings can be very telling about the nature of
    code. For example, they could hint at the use of
    `HABv4 <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/arch/arm/mach-imx/hab.c#L587>`_
    `functionality <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/arch/arm/mach-imx/hab.c#L646>`_
    to authenticate images on NXP i.MX-based platforms.

    |
    """

    def _search_at(self, target, start, end, **kwargs):
        min_len = kwargs.get('min_len', -1)
        max_len = kwargs.get('max_len', -1)

        match_only  = kwargs.get('match', False)

        if target is None or len(target) == 0:
            # Default to searching for (an optionally length-limited) string
            regexp = _str_regex(None, min_len, max_len)
        elif isinstance(target, str):
            target = target.encode('ascii')
            regexp = _str_regex(pat=target)
        elif isinstance(target, bytes):
            regexp = _str_regex(pat=target)
        else:
            err = 'Expected target to be str or bytes, got {:s}'
            raise TypeError(err.format(type(target).__name__))

        if match_only:
            # Don't search starting here, match only at this location
            m = regexp.match(self._data[start:end])
            if m is None:
                return None
        else:
            m = regexp.search(self._data[start:end])
            if m is None:
                # We covered the full range in this case
                raise HunterResultNotFound()

        found_offset, found_end_offset = m.span()
        return (found_offset + start, found_end_offset - found_offset)

    def string_at(self, address, min_len=-1, max_len=-1, allow_empty=False) -> str:
        """
        Attempt to determine if the specified address contains a
        NULL-terminated ASCII string, with optional length constraints.

        If an ASCII string is located at the specified address, it is returned
        sans NULL byte.  Otherwise, :py:exc:`~.hunter.HunterResultNotFound` is raised.

        An :py:exc:`IndexError` is raised if *address* is outside the bounds of the
        *data* parameter originally provided to the constructor.
        """
        offset = address - self._address
        if offset < 0 or offset > self._end_offset:
            err = 'Address (0x{:08x}) outside of associated range: 0x{:08x} - 0x{:08x}'
            raise IndexError(err.format(address, self._address, self._end_address))

        # Allow empty string
        if allow_empty and self._data[offset] == 0:
            return ''

        result = self._search_at(None, offset, self._end_offset + 1, min_len=min_len, max_len=max_len, match=True)
        if result is None:
            raise HunterResultNotFound

        found_offset = result[0]
        found_size   = result[1]

        s = self._data[found_offset:found_offset + found_size].decode('ascii')
        if s.endswith('\x00'):
            s = s[:-1]
        return s
