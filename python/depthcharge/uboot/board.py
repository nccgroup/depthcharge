
# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Parsing and conversion of "board" or platform-specific data
"""

import os
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

    dram_banks = {}
    curr_dram_bank = None

    for line in output.splitlines():
        match = _BDINFO_NUM_REGEX.match(line)
        if not match:
            log.debug('Skipping unmatched bdinfo item: ' + line)
            continue

        try:
            name    = match.group('name').strip()
            value   = match.group('value').strip()
            suffix  = match.group('suffix') or ''
            suffix  = suffix.strip()

            try:
                value = int(value, 0)
            except ValueError:
                # Try to move forward with it as-is
                pass

            # Aggregate DRAM bank information in a nested fashion.
            # Treat everything else as a single (assumed unique) entry.
            if name == 'DRAM bank':
                curr_dram_bank = {}
                dram_banks[value] = curr_dram_bank
            elif curr_dram_bank is not None and name.startswith('-> '):
                name = name.replace('-> ', '')
                curr_dram_bank[name] = value
            else:
                # Variable names in gd->bd tend to be mached up in one word,
                # Try to follow that convention...
                key  = name.replace(' ', '').lower()
                ret[key] = {'name': name, 'value': value, 'suffix': suffix}

                curr_dram_bank = None

        except (AttributeError, IndexError):
            log.error('Failed to parse line: ' + match.group())

    ret['dram_bank'] = { 'name': 'DRAM bank(s)', 'value': dram_banks, 'suffix': '' }
    return ret

def bdinfo_str(bdinfo: dict) -> str:
    """
    Return a user-facing, printable string from a dictionary
    returned by `bdinfo_dict()`.
    """
    s = ''
    for key in sorted(bdinfo.keys()):
        entry = bdinfo[key]
        name = entry['name']
        value = entry['value']
        suffix = entry['suffix']

        if key == 'dram_bank':
            assert(isinstance(value, dict))
            banks = sorted(value.keys())
            for bankno in banks:
                start = value[bankno]['start']
                size  = value[bankno]['size']

                pfx  = 'DRAM Bank #{:d}'.format(int(bankno))
                s += '  {:20s} start=0x{:08x}, size=0x{:08x}'.format(pfx, start, size)
                s += os.linesep
        else:

            if isinstance(value, int):
                if name in ('arch_number', 'baudrate'):
                    line = '  {:20s} {:d}'.format(name, value)
                else:
                    line = '  {:20s} 0x{:08x}'.format(name, value)
            else:
                line = '  {:20s} {:s}'.format(name, value)

            if suffix:
                line += ' ' + suffix

            s += line + os.linesep

    return s.rstrip()
