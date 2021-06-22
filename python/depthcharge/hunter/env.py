# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements EnvironmentHunter
"""

from zlib import crc32

from .hunter import Hunter, HunterResultNotFound
from .. import uboot
from ..arch import Architecture


class EnvironmentHunter(Hunter):
    """
    An EnvironmentHunter searches a memory or flash dump for instances of U-Boot environments,
    which store collections of variable definitions. This :py:class:`.Hunter` identifies three
    types of U-Boot environments:

    1. Built-in defaults used when no (valid) environment is present in non-volatile storage.
    2. A valid environment stored in non-volatile storage, prefixed with a CRC32 header value.
    3. A "redundant" environment, (see `CONFIG_SYS_REDUNDAND_ENVIRONMENT
       <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/env/Kconfig#L394>`_) which includes
       both a CRC32 header and a *flags* value used to determine the active environment copy.

    The constructor supports two keyword arguments that place a lower and upper bound on the
    sizes (in number of entries) of environment instances returned by :py:meth:`find()` and
    :py:meth:`finditer()`:

    * *min_entries* (default: 5)
    * *max_entries* (default: ``None``)

    """

    def __init__(self, data: bytes, address: int, start_offset=-1, end_offset=-1, gaps=None, **kwargs):
        super().__init__(data, address, start_offset, end_offset, gaps, **kwargs)

        self._arch = Architecture.get(kwargs.get('arch', 'arm'))

        min_entries = kwargs.get('min_entries', 5)
        max_entries = kwargs.get('max_entries', None)

        self._env = uboot.env.raw_regex(min_entries, max_entries)

    def _expected_crc(self, offset, redundant_env):
        if redundant_env:
            # env_t is { uint32_t crc32; usigned char flags; unsigned char data[]; }
            return self._arch.to_uint(self._data[offset-5:offset-1])

        # Otherwise, env_t is { uint32_t crc32; unsigned char data[]; }
        return self._arch.to_uint(self._data[offset-4:offset])

    def _actual_offset_size_crc(self, offset: int, min_size: int, max_size: int, redund: bool) -> tuple:
        """
        Returns (actual environment size: int, actual offset: int, crc: int).

        Otherwise, returns None
        """
        size = min_size

        # We can run into the situation where the CRC contains printable characters such that our
        # regex catches portions of the CRC (in the name of the first environment variable)
        #
        # To work around this, we use the validity of the CRC and advance our start offset
        # if we don't find a match.

        actual_offset = offset
        actual_offset_max = offset + self._data[offset:offset+min_size].index(b'=')

        # Not an off-by-one. You can actually have a completely empty variable name.
        #   setenv '' oh_no
        while actual_offset <= actual_offset_max:

            # Just for my own sanity when indexing
            ao = actual_offset
            expected_crc = self._expected_crc(ao, redund)

            try:
                # This covers the used portion of the environment
                crc = crc32(self._data[ao:ao + min_size])
                if crc == expected_crc:
                    return size

                # Unused portion. We can probably optimize this considering
                # that unused portions should be a fixed value.
                for i in range(ao + min_size, ao + max_size):
                    crc = crc32(self._data[i].to_bytes(1, 'little'), crc)
                    if crc == expected_crc:
                        return (ao, i - ao + 1, crc)

            except IndexError:
                # We may run outside the bounds of self._data[] for a small
                # binary when no header is present. (i.e., default env in code)
                pass

            actual_offset += 1

        return (None, None, None)

    def _get_env_flags(self, offset, redundant_env) -> int:
        """
        Returns env flags value for an redundant env, and None otherwise
        """
        if redundant_env:
            return self._data[offset-1]

        # No flags value is present in the env_t structure when
        # "SYS_REDUNDAND_ENVIRONMENT" [sic] is not enabled.
        return None

    def _search_at(self, target, start, end, **kwargs):

        match = self._env.search(self._data[start:end])
        if not match:
            raise HunterResultNotFound()

        # We've located environment data, now we have to figure out if
        # what we have is:
        # (1) An occurrence of the hard-coded default environment
        # (2) An occurrence of the environment from external storage
        #   (2a) The CRC for this exported/imported env
        #   (2b) The actual length (CONFIG_ENV_SIZE) of the environment
        #   (2c) Whether this is a "redundant" env, which means
        #        the size of the env_t structure changes on us by one byte.

        span = match.span()
        offset = start + span[0]
        size = span[1] - span[0]

        # struct environment_s (env_t) has a char flags field only
        # if CONFIG_SYS_REDUNDAND_ENVIRONMENT [sic] is set. Default
        # value of "None" implies - "I don't know"
        redundant_env = kwargs.get('redundant_env', None)

        # CONFIG_ENV size is customizable, per U-Boot's CONFIG_ENV_SIZE env/Kconfig.
        # The default size is 0x1f000. Many platforms set it much lower, on the order
        # of 0x1000 or 0x2000. The largest defconfigs set a size of 0x100000.
        max_size = kwargs.get('env_size_max', 0x100000)

        extra_info = {}

        # Attempt to decode the preceding header, if there actually is one, to determine
        # the environment's actual offset, size, CRC32 checksum, and flags (if relevant).
        try:
            if redundant_env is not None:
                # User has told us if we have a redundant env or not. Just trust what they say.
                (actual_off, actual_size, crc) = self._actual_offset_size_crc(offset, size, max_size, redundant_env)

            else:
                # Otherwise, user doesn't know -- we'll try both.
                for redund in (True, False):
                    (actual_off, actual_size, crc) = self._actual_offset_size_crc(offset, size, max_size, redund)
                    if None not in (actual_off, actual_size, crc):
                        redundant_env = redund
                        break

            if None in (actual_off, actual_size, crc):
                # Either this is just a built-in envrionnment or we've failed miserably.
                # Just return what we matched.
                actual_off  = offset
                actual_size = size

            if crc is not None:
                extra_info['crc'] = crc

                env_flags = self._get_env_flags(actual_off, redundant_env)
                if env_flags is not None:
                    extra_info['flags'] = env_flags
                    env_type = 'Stored redundant environment'
                else:
                    env_type = 'Stored environment'

                extra_info['type'] = env_type

            else:
                extra_info['type'] = 'Built-in environment'

            extra_info['raw']  = self._data[actual_off:actual_off + actual_size]
            extra_info['dict'] = uboot.env.parse_raw(extra_info['raw'])
            extra_info['arch'] = self._arch.name

            # User is looking for an environment containg a specific item.
            # This is done here at the end so we check against the correct span of data .
            if target:
                if isinstance(target, str):
                    target = target.encode('ascii')

                if target not in extra_info['raw']:
                    raise HunterResultNotFound()

        except IndexError:
            raise HunterResultNotFound()

        return (actual_off, actual_size, extra_info)
