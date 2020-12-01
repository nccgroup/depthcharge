# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
U-Boot version comparison functionality
"""

import re


def version_in_range(version: str, min_version: str, max_version: str):
    """
    A convenience wrapper for :py:meth:`UBootVersion.in_range()`.
    """
    version = UBootVersion(version)
    return version.in_range(min_version, max_version)


class UBootVersion:

    # Refer to the definitions at the top of the U-Boot Makefile
    #
    # We don't bother collecting NAME or the SCM information since we
    # can't make meaningful comparisons with these.
    _VERSION_RE = re.compile((r'v?(?P<version>[0-9]+)'
                              r'\.'
                              r'(?P<patch>[0-9]+)'
                              r'(\.(?P<sub>[0-9]+))?'
                              r'(-rc(?P<extra>[0-9]+))?'))

    @classmethod
    def find(cls, s: str):
        """
        Search for a U-Boot version string on a line and either return it as a
        :py:class:`UBootVersion` object or a ``None``.
        """
        match = cls._VERSION_RE.search(s)
        if match is not None:
            return UBootVersion(match)

        return None

    def __init__(self, version: str):
        if isinstance(version, str):
            orig = version
            version = self._VERSION_RE.match(version)
            if version is None:
                raise ValueError('No U-Boot version identified in string: ' + orig)

        if not isinstance(version, re.Match):
            m = 'Unexpected type for `version` parameter: ' + type(version).__name__
            raise TypeError(m)

        self._version = int(version.group('version'))
        self._patch = int(version.group('patch'))

        self._sub = version.group('sub')
        self._sub = 0 if self._sub is None else int(self._sub)

        # If -rcN extra is not present, then it's a release.
        self._extra = version.group('extra')
        self._extra = 1e6 if self._extra is None else int(self._extra)

    def __lt__(self, other):
        if self._version < other._version:
            return True

        if self._version > other._version:
            return False

        if self._patch > other._patch:
            return False

        if self._patch < other._patch:
            return True

        if self._sub > other._sub:
            return False

        if self._sub < other._sub:
            return True

        return self._extra < other._extra

    def __gt__(self, other):
        if self._version > other._version:
            return True

        if self._version < other._version:
            return False

        if self._patch < other._patch:
            return False

        if self._patch > other._patch:
            return True

        if self._sub < other._sub:
            return False

        if self._sub > other._sub:
            return True

        return self._extra > other._extra

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def __eq__(self, other):
        return (self._version == other._version and
                self._patch == other._patch and
                self._sub == other._sub and
                self._extra == other._extra)

    def compare(self, other: str):
        """
        Return -1 if this version is less than *other*,
                0 if both versions are equal (not considering SCM info), or
                1 if this version is greater than *other*.
        """
        if isinstance(other, UBootVersion):
            pass
        elif isinstance(other, str):
            other = UBootVersion(other)
        else:
            raise TypeError('Invalid type for parameter `other`: ' + type(other).__name__)

        if self < other:
            return -1

        if self > other:
            return 1

        assert self == other
        return 0

    def in_range(self, min_version: str, max_version: str) -> bool:
        """
        Returns ``True`` if version falls within the inclusive range of
        *[min_version, max_version]*, and ``False`` otherwise.
        """
        if isinstance(min_version, UBootVersion):
            pass
        elif isinstance(min_version, str):
            min_version = UBootVersion(min_version)
        else:
            err = 'Invalid type for `min_version` parameter: ' + type(min_version).__name__
            raise TypeError(err)

        if isinstance(max_version, UBootVersion):
            pass
        elif isinstance(max_version, str):
            max_version = UBootVersion(max_version)
        else:
            err = 'Invalid type for `max_version` parameter: ' + type(max_version).__name__
            raise TypeError(err)

        return min_version <= self <= max_version
