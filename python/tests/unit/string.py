# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# Relax style and documentation requirements for unit tests.
# pylint: disable=missing-function-docstring,missing-class-docstring,too-few-public-methods
#

"""
Unit tests for depthcharge.string
"""

import os
import random
import tempfile

from unittest import TestCase

# TODO: Add test cases for other conversion fns
from depthcharge.string import xxd, xxd_reverse, xxd_reverse_file


class TestXxd(TestCase):

    def test_random(self):
        """
        Test forward and reverse conversion of random data.
        """

        address = 0x87f0_0000
        data = bytearray()

        random.seed(0)
        for _ in range(0, 4095):
            data.append(random.randint(0, 255))

        dump = xxd(address, data)
        rev_address, rev_data = xxd_reverse(dump)

        self.assertEqual(rev_address, address)
        self.assertEqual(rev_data, data)

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as outfile:
            tempname = outfile.name
            outfile.write(dump)

        rev_address, rev_data = xxd_reverse_file(tempname)

        self.assertEqual(rev_address, address)
        self.assertEqual(rev_data, data)

        os.remove(tempname)

    def test_whitespace(self):
        """
        Confirm that lines containing only 0x20 are parsed.
        This previously failed due to a strip().

        Doesn't exercise xxd_reverse_file.
        """
        address = 13
        data = b'\x20' * 57

        dump = xxd(address, data)
        rev_address, rev_data = xxd_reverse(dump)

        self.assertEqual(address, rev_address)
        self.assertEqual(data, rev_data)
