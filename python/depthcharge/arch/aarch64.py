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
    _alignment = 1

    _word_size = 8
    _phys_size = 8
    _word_mask = 0xffffffff_ffffffff
    _endianness = 'little'
    _supports_64bit_data = True

    # Seems we need this word-aligned for the CpCrashRegisterReader to work...
    _da_crash_addr = 0xffffffff_fffffff0

    _regs = {
        'x0':   {},
        'x1':   {},
        'x2':   {},
        'x3':   {},
        'x4':   {'da_data_reg': True},
        'x5':   {},
        'x6':   {},
        'x7':   {},
        'x8':   {},
        'x9':   {},
        'x10':  {},
        'x11':  {},
        'x12':  {},
        'x13':  {},
        'x14':  {},
        'x15':  {},
        'x16':  {},
        'x17':  {},
        'x18':  {'gd': True},
        'x19':  {},
        'x20':  {},
        'x21':  {},
        'x22':  {},
        'x23':  {},
        'x24':  {},
        'x25':  {},
        'x26':  {},
        'x27':  {},
        'x28':  {},
        'x29':  {'alias': 'fp'},
        'elr':  {},
        'lr':   {},
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
