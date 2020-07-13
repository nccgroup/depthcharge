# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring

"""
Unit tests for depthcharge.Hunter's private utility class, _GappedRangeIter.

Hunter is further exercised implicitly through its subclasses' tests.
"""

import sys

from unittest import TestCase

from depthcharge.hunter import Hunter


class TestGappedRangeIter(TestCase):

    def setUp(self):
        self.data = bytearray(26)
        for i in range(0, 26):
            self.data[i] = 0x41 + i

        self.addr = 0x8180_0000
        self.hunter = Hunter(self.data, self.addr)

    def result(self, target=None, start=-1, end=-1, gaps=None):
        if not gaps:
            gaps = []

        self.hunter = Hunter(self.data, self.addr, gaps=gaps)
        ret = b''
        for i in self.hunter._gapped_range_iter(target, start, end):
            ret += self.data[i].to_bytes(1, sys.byteorder)
        return ret

    def test_default(self):
        self.assertEqual(self.hunter._gapped_range_iter(None), range(0, 26))
        self.assertEqual(self.hunter._gapped_range_iter(b'CDE'), range(0, 26))
        self.assertEqual(self.result(), b'ABCDEFGHIJKLMNOPQRSTUVWXYZ')

    def test_gaps_tuples(self):
        gaps = [
            (self.addr + 1,   5),  # Skip B-F
            (self.addr + 13,  1),  # Skip N
            (self.addr + 19,  3),  # Skip TUV
            (self.addr + 13,  1),  # Duplicate
            (self.addr + 18,  4),  # Overlap to skip STUV
            (self.addr + 25,  0),  # Ignore zero-length
            (self.addr - 20, 21),  # Skip A
            (self.addr + 27, 60),  # Outside our range
            (self.addr + 25, 10)   # Skip Z
        ]

        self.assertEqual(self.result(gaps=gaps), b'GHIJKLMOPQRWXY')
        self.assertEqual(self.result(start=8, gaps=gaps), b'IJKLMOPQRWXY')
        self.assertEqual(self.result(start=8, end=22, gaps=gaps), b'IJKLMOPQRW')
        self.assertEqual(self.result(start=8, end=22, gaps=gaps), b'IJKLMOPQRW')
        self.assertEqual(self.result('JKLM', start=8, end=22, gaps=gaps), b'IJKLMOPQRW')

    def test_gaps_ranges(self):
        gaps = [
            range(self.addr +  0, self.addr +  4),  # Skip A-D
            range(self.addr - 10, self.addr +  5),  # Skip A-E
            range(self.addr + 23, self.addr + 26)   # Skup XYZ
        ]

        self.assertEqual(self.result(gaps=gaps), b'FGHIJKLMNOPQRSTUVW')
        self.assertEqual(self.result(end=24, gaps=gaps), b'FGHIJKLMNOPQRSTUVW')
        self.assertEqual(self.result(start=16, end=24, gaps=gaps), b'QRSTUVW')
        self.assertEqual(self.result(target='AB', start=16, end=24, gaps=gaps), b'QRSTUVW')

    def test_gaps_mixed(self):
        gaps = [
            range(self.addr +  0, self.addr +  4),  # Skip A-D
            (self.addr + 4, 1),                     # Skip A-E
            range(self.addr + 23, self.addr + 26)   # Skup XYZ
        ]

        self.assertEqual(self.result(gaps=gaps), b'FGHIJKLMNOPQRSTUVW')
        self.assertEqual(self.result(gaps=gaps), b'FGHIJKLMNOPQRSTUVW')
        self.assertEqual(self.result(end=24, gaps=gaps), b'FGHIJKLMNOPQRSTUVW')
        self.assertEqual(self.result(start=16, end=24, gaps=gaps), b'QRSTUVW')
        self.assertEqual(self.result(target='AB', start=16, end=24, gaps=gaps), b'QRSTUVW')


class TestSplitDataOffsets(TestCase):
    def setUp(self):
        self.data = bytearray(26)
        self.addr = 0x8180_0000

    def test(self):
        with self.subTest('None'):
            hunter = Hunter(self.data, self.addr)
            split_data = hunter._split_data_offsets()
            self.assertEqual(split_data, [range(0, 26)])

        with self.subTest('Neither end'):
            gaps = [
                range(self.addr + 10, self.addr + 17),
                range(self.addr + 20, self.addr + 23),
            ]

            expected = [
                range(0,  10),
                range(17, 20),
                range(23, 26)
            ]

            hunter = Hunter(self.data, self.addr, gaps=gaps)
            split_data = hunter._split_data_offsets()
            self.assertEqual(split_data, expected)

        with self.subTest('Left'):
            gaps = [
                range(self.addr, self.addr + 7),
                range(self.addr + 10, self.addr + 17),
                range(self.addr + 20, self.addr + 23),
            ]

            expected = [
                range(7,  10),
                range(17, 20),
                range(23, 26)
            ]

            hunter = Hunter(self.data, self.addr, gaps=gaps)
            split_data = hunter._split_data_offsets()
            self.assertEqual(split_data, expected)

        with self.subTest('Right'):
            gaps = [
                range(self.addr + 10, self.addr + 17),
                range(self.addr + 20, self.addr + 23),
                range(self.addr + 24, self.addr + 26)
            ]

            expected = [
                range(0,  10),
                range(17, 20),
                range(23, 24)
            ]

            hunter = Hunter(self.data, self.addr, gaps=gaps)
            split_data = hunter._split_data_offsets()
            self.assertEqual(split_data, expected)

        with self.subTest('Both'):
            gaps = [
                range(self.addr + 0,  self.addr + 6),
                range(self.addr + 10, self.addr + 17),
                range(self.addr + 20, self.addr + 23),
                range(self.addr + 24, self.addr + 26)
            ]

            expected = [
                range(6,  10),
                range(17, 20),
                range(23, 24)
            ]

            hunter = Hunter(self.data, self.addr, gaps=gaps)
            split_data = hunter._split_data_offsets()
            self.assertEqual(split_data, expected)
