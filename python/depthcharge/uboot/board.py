
# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Parsing and conversion of "board" or platform-specific data
"""

import re

from .. import log


_BDINFO_NUM_REGEX = re.compile((
    r'(?P<name>[\w\d<>\s-]+)'
    r'(=)\s*'
    r'(?P<value>(0x)?[\w\d:\./@#$%-]+)'
    r'\s*'
    r'(?P<suffix>[\w\d-]+)?'
))


def bdinfo_dict(output: str) -> dict:
    """
    Convert output of U-Boot's *bdinfo* command to a dictionary.

    Technically, each item may come from a variety of locations,
    whether it be *gd*, *gd->bd*, or another structure.

    However, we'll just return everything in a single dict
    out of laziness.
    """
    ret = {}

    for line in output.splitlines():
        match = _BDINFO_NUM_REGEX.match(line)
        if not match:
            log.debug('Skipping unmatched bdinfo item: ' + line)
            continue

        try:
            name    = match.group('name').strip()
            value   = match.group('value').strip()
            suffix  = match.group('suffix') or ''

            # Fixup some known formatting
            if 'drambank' in ret:
                name = name.replace('->', 'DRAM bank')

            try:
                value = int(value, 0)
            except ValueError:
                # Try to move forward with it as-is
                pass

            # Variable names in gd->bd tend to be mached up in one word,
            # Try to follow that convention...
            key  = name.replace(' ', '').lower()
            ret[key] = {'name': name, 'value': value, 'suffix': suffix}

        except (AttributeError, IndexError):
            log.error('Failed to parse line: ' + match.group())

    return ret
