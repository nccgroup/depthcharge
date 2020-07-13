# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring

"""
Unit test for depthcharge.revcrc32.revercse_crc32_4bytes()
"""

import random
import sys

from zlib import crc32
from unittest import TestCase

from depthcharge.revcrc32 import reverse_crc32_4bytes


class TestReverseCRC32(TestCase):

    def test_rev32(self):
        random.seed(0)
        for _ in range(0, 64):
            expected_data  = random.getrandbits(32).to_bytes(4, sys.byteorder)
            with self.subTest(expected_data.hex()):
                result = crc32(expected_data)
                reversed_data  = reverse_crc32_4bytes(result).to_bytes(4, sys.byteorder)
                self.assertEqual(expected_data, reversed_data)
