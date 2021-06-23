# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
AARCH64 (ARMv8-A) support
"""

import os
import re

from .arch import Architecture

class AARCH64(Architecture):
    """
    AARCH64 (ARMv8) target information
    """
    _desc = 'ARMv8 64-bit, little-endian'

    # Per https://developer.arm.com/documentation/den0024/a/An-Introduction-to-the-ARMv8-Instruction-Sets/The-ARMv8-instruction-sets/Addressing?lang=en
    #
    # Unaligned address support
    #  Except for exclusive and ordered accesses, all loads and stores support
    #  the use of unaligned addresses when accessing normal memory. This
    #  simplifies porting code to A64.
    #
    _alignment = 1  # AARCH64 supports unaligned accesses

    _word_size = 8
    _phys_size = 8
    _word_mask = 0xffffffff_ffffffff
    _endianness = 'little'
    _supports_64bit_data = True

    _regs = {
        'elr':  { 'ident': 0x5e },
        'lr':   { 'ident': 0x5f },
        'x0':   { 'ident': 0x60 },
        'x1':   { 'ident': 0x61 },
        'x2':   { 'ident': 0x62 },
        'x3':   { 'ident': 0x63 },
        'x4':   { 'ident': 0x64 },
        'x5':   { 'ident': 0x65 },
        'x6':   { 'ident': 0x66 },
        'x7':   { 'ident': 0x67 },
        'x8':   { 'ident': 0x68 },
        'x9':   { 'ident': 0x69 },
        'x10':  { 'ident': 0x6a },
        'x11':  { 'ident': 0x6b },
        'x12':  { 'ident': 0x6c },
        'x13':  { 'ident': 0x6d },
        'x14':  { 'ident': 0x6e },
        'x15':  { 'ident': 0x6f },
        'x16':  { 'ident': 0x70 },
        'x17':  { 'ident': 0x71 },
        'x18':  { 'ident': 0x72 },
        'x19':  { 'ident': 0x73 },
        'x20':  { 'ident': 0x74 },
        'x21':  { 'ident': 0x75 },
        'x22':  { 'ident': 0x76 },
        'x23':  { 'ident': 0x77 },
        'x24':  { 'ident': 0x78 },
        'x25':  { 'ident': 0x79 },
        'x26':  { 'ident': 0x7a },
        'x27':  { 'ident': 0x7b },
        'x28':  { 'ident': 0x7c },
        'x29':  { 'ident': 0x7d },
    }

    _DA_ENTRY = re.compile(r"""
        (?P<name>[a-zA-Z][a-zA-Z0-9]+)
        \s?:\s?
        (?P<value>[0-9a-fA-F]{16})
    """, re.VERBOSE)

    _ESR_ENTRY = re.compile(r"""
        esr\s+0x(?P<value>[0-9a-fA-F]+)
    """, re.VERBOSE)

    @classmethod
    def parse_data_abort(cls, text: str) -> dict:
        """
        Parse AARCH64 data abort output formatted as follows, and return
        each field in a dict.

        ffffffff:"Synchronous Abort" handler, esr 0x96000005
        elr: 00000000000ccc18 lr : 00000000000ccb10 (reloc)
        elr: 000000003b3a3c18 lr : 000000003b3a3b10
        x0 : 0000000000000009 x1 : 000000003ebfa800
        x2 : 0000000000000040 x3 : 0000000000000000
        x4 : 00000000ffffffff x5 : 0000000000000000
        x6 : 000000003b3b77af x7 : 0000000000000001
        x8 : 000000003af52a18 x9 : 0000000000000008
        x10: 00000000ffffffd0 x11: 0000000000000010
        x12: 0000000000000006 x13: 000000000001869f
        x14: 000000003af52cd8 x15: 0000000000000021
        x16: 000000003b37f4f8 x17: 0000000000000000
        x18: 000000003af52de0 x19: 0000000000000004
        x20: 00000000ffffffff x21: 00000000ffffffff
        x22: 000000003b3b6f4c x23: 0000000000000002
        x24: 0000000000000003 x25: 0000000000000010
        x26: 0000000000000001 x27: 000000003af52ad8
        x28: 0000000000000004 x29: 000000003af52a50

        Code: 12003ca5 78237b65 92403ca2 17ffffe9 (39400085)
        Resetting CPU ...

        """
        ret = {}
        for line in text.splitlines():
            line = line.strip()

            pfx = ""
            match = cls._ESR_ENTRY.search(line)
            if match:
                ret['esr'] = int(match.group('value'), 16)

            elif line.startswith('Code:'):
                ret['code'] = cls._parse_instructions(line)

            else:
                pfx = ''
                if line.endswith('(reloc)'):
                    line = line[:-len('(reloc)')]
                    pfx = 'reloc '


                for match in cls._DA_ENTRY.finditer(line):
                    regname, _ = cls.register(match.group('name'))
                    name = pfx + regname
                    value = match.group('value')

                    regs = ret.get('registers', {})

                    try:
                        regs[name] = int(value, 16)
                    except ValueError:
                        regs[name] = int(value, 10)

                    ret['registers'] = regs

        if not ret:
            msg = 'No data abort content found in the following text:' + os.linesep
            msg += text
            raise ValueError(msg)

        return ret
