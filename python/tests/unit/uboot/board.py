# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#

"""
Unit tests for depthcharge.uboot.board
"""

from unittest import TestCase
from textwrap import dedent, indent

from depthcharge.uboot.board import bdinfo_dict, bdinfo_str

class TestUbootBoardFns(TestCase):

    _exp_dict = {
        'arch_number': {
            'name': 'arch_number',
            'value': 0,
            'suffix': ''
        },

        'boot_params': {
            'name': 'boot_params',
            'value': 0x100,
            'suffix': '',
        },

        'baudrate': {
            'name': 'baudrate',
            'value': 115200,
            'suffix': 'bps',
        },

        'dram_bank': {
            'name': 'DRAM bank(s)',
            'suffix': '',
            'value': {
                0: {
                    'start': 0x00000000,
                    'size': 0x3b400000,
                },

                1: {
                    'start': 0x80000000,
                    'size': 0x400000,
                },
            },
        },

        'fbbase': {
            'name': 'FB base',
            'value': 0x00000000,
            'suffix': '',
        },

        'fdt_blob': {
            'name': 'fdt_blob',
            'value': 0x3b3cd320,
            'suffix': ''
        },

        'irq_sp': {
            'name': 'irq_sp',
            'value': 0x3af66ec0,
            'suffix': '',
        },

        'relocaddr': {
            'name': 'relocaddr',
            'value': 0x3b36b000,
            'suffix': '',
        },

        'relocoff': {
            'name': 'reloc off',
            'value': 0x3b363000,
            'suffix': '',
        },

        'spstart': {
            'name': 'sp start',
            'value': 0x3af66eb0,
            'suffix': '',
        },

        'tlbaddr': {
            'name': 'TLB addr',
            'value': 0x3b3f0000,
            'suffix': '',
        },
    }

    _exp_str = indent(dedent("""\
        arch_number          0
        baudrate             115200 bps
        boot_params          0x00000100
        DRAM Bank #0         start=0x00000000, size=0x3b400000
        DRAM Bank #1         start=0x80000000, size=0x00400000
        FB base              0x00000000
        fdt_blob             0x3b3cd320
        irq_sp               0x3af66ec0
        relocaddr            0x3b36b000
        reloc off            0x3b363000
        sp start             0x3af66eb0
        TLB addr             0x3b3f0000"""), '  ')

    _s = dedent("""
        arch_number = 0x00000000
        boot_params = 0x00000100
        DRAM bank   = 0x00000000
        -> start    = 0x00000000
        -> size     = 0x3b400000
        DRAM bank   = 0x00000001
        -> start    = 0x80000000
        -> size     = 0x00400000
        baudrate    = 115200 bps
        TLB addr    = 0x3b3f0000
        relocaddr   = 0x3b36b000
        reloc off   = 0x3b363000
        irq_sp      = 0x3af66ec0
        sp start    = 0x3af66eb0
        FB base     = 0x00000000
        Early malloc usage: 344 / 2000
        fdt_blob    = 0x3b3cd320
    """)

    def test_bdinfo_dict(self):
        d = bdinfo_dict(self._s)
        self.assertEqual(d, self._exp_dict)

    def test_bdinfo_str(self):
        d = bdinfo_dict(self._s)
        outstr = bdinfo_str(d)
        self.assertEqual(outstr, self._exp_str)
