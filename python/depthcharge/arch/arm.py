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

    # ident values used by RETURN_REGISTER payload
    _regs = {
        'r0':  {'ident': 0x61},
        'r1':  {'ident': 0x62},
        'r2':  {'ident': 0x63},
        'r3':  {'ident': 0x64},
        'r4':  {'ident': 0x65},
        'r5':  {'ident': 0x66},
        'r6':  {'ident': 0x67},
        'r7':  {'ident': 0x68},
        'r8':  {'ident': 0x69},
        'r9':  {'ident': 0x6a, 'gd': True, 'alias': 'sb'},
        'r10': {'ident': 0x6b},
        'r11': {'ident': 0x6c, 'alias': 'fp'},
        'r12': {'ident': 0x6d, 'alias': 'ip'},
        'r13': {'ident': 0x6e, 'alias': 'sp'},
        'r14': {'ident': 0x6f, 'alias': 'lr'},
        'r15': {'ident': 0x70, 'alias': 'pc'},
    }

    _DA_ENTRY = re.compile(r"""
        (?P<name>[a-zA-Z][a-zA-Z0-9]+)
        \s?:\s?
        (?P<value>[0-9a-fA-F]{8})
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

        """
        ret = {}
        for line in text.splitlines():
            pfx = ''
            if 'reloc' in line:
                pfx = 'reloc '
            elif line.startswith('Flags:'):
                ret['flags'] = {}
                for field in line.split('  '):
                    name, value = field.split(' ')
                    name = name.replace('Flags:', 'Asserted')
                    ret['flags'][name] = value
                continue

            elif line.startswith('Code:'):
                code = line.split()
                instructions = []
                for instruction in code[1:]:
                    try:
                        instruction = instruction.replace('(', '').replace(')', '').strip()
                        instruction = int(instruction, 16)
                        instruction = instruction.to_bytes(cls.word_size, byteorder=cls.endianness)
                        instructions.append(instruction)
                    except ValueError as e:
                        msg = 'Invalid instruction or parse error: ' + str(e)
                        raise ValueError(msg)

                ret['code'] = instructions

            else:
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
