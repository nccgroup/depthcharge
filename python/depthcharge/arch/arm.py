# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
ARM 32-bit support
"""

import os
import re

from .arch import Architecture


class ARM(Architecture):
    """
    ARMv7 (or earlier) target information - 32-bit little-endian
    """
    _desc = 'ARM 32-bit, little-endian'
    _alignment = 4
    _word_size = 4
    _phys_size = 4
    _word_mask = 0xffffffff
    _endianness = 'little'
    _supports_64bit_data = False
    _da_crash_addr = 1

    _regs = {
        'r0':  {'da_data_reg': True},
        'r1':  {},
        'r2':  {},
        'r3':  {},
        'r4':  {},
        'r5':  {},
        'r6':  {},
        'r7':  {},
        'r8':  {},
        'r9':  {'gd': True, 'alias': 'sb'},
        'r10': {},
        'r11': {'alias': 'fp'},
        'r12': {'alias': 'ip'},
        'r13': {'alias': 'sp'},
        'r14': {'alias': 'lr'},
        'r15': {'alias': 'pc'},
    }

    _DA_ENTRY = re.compile(r"""
        (?P<name>[a-zA-Z][a-zA-Z0-9]+)
        \s?:\s?
        (\[<)?
        (?P<value>[0-9a-fA-F]{8})
        (>\])?
    """, re.VERBOSE)

    @classmethod
    def parse_data_abort(cls, text: str) -> dict:
        """
        Parse ARM data abort output formatted as follows and return each field in a dict.

            00000001:data abort
            pc : [<8f7d8858>]	   lr : [<8f7d8801>]
            reloc pc : [<17835858>]	   lr : [<17835801>]
            sp : 8ed99718  ip : 00000000	 fp : 00000001
            r10: 00000001  r9 : 8eda2ea8	 r8 : 00000001
            r7 : 00000000  r6 : 00000004	 r5 : 00000004  r4 : 00000001
            r3 : 8ed9972c  r2 : 020200b4	 r1 : 8ed994ec  r0 : 00000009
            Flags: nZCv  IRQs off  FIQs off  Mode SVC_32
            Code: 2800f915 f04fd0cf e7ce30ff d10a2d04 (2000f8d8)

        Note: The "Mode" entry under "Flags:" will kcontain a " (T)" suffix
              when the device is in Thumb mode.
        """
        ret = {}
        for line in text.splitlines():
            line = line.strip()

            if line.startswith('Flags:'):
                ret['flags'] = {}
                for field in line.split('  '):
                    name, value = field.split(' ', 1)
                    name = name.replace('Flags:', 'Asserted')
                    ret['flags'][name] = value
                continue

            elif line.startswith('Code:'):
                ret['code'] = cls._parse_instructions(line)
            else:
                if line.startswith('reloc '):
                    pfx = 'reloc '
                    line = line[len(pfx):]
                else:
                    pfx = ''

                for match in cls._DA_ENTRY.finditer(line):
                    regname, _ = cls.register(match.group('name'))
                    name = pfx + regname
                    value = match.group('value')

                    regs = ret.get('registers', {})

                    try:
                        regs[name] = int(value, 16)
                    except ValueError:
                        regs[name] = value

                    ret['registers'] = regs

        if not ret:
            msg = 'No data abort content found in the following text:' + os.linesep
            msg += text
            raise ValueError(msg)

        return ret
