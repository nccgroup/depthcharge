# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring

"""
Unit tests for depthcharge.hunter.ConstantHunter
"""

from unittest import TestCase

from depthcharge.hunter import ConstantHunter, HunterResultNotFound

from ..test_utils import random_data


class TestConstantHunter(TestCase):

    # This is exercising Hunter.find()
    def test_find(self):
        addr = 0x87804ef0

        with self.subTest('No offsets'):
            with self.subTest('@ 0'):
                haystack = b'needle6789012345678901234'
                hunter = ConstantHunter(haystack, addr)
                result = hunter.find(b'needle')
                self.assertTrue(result is not None)
                self.assertEqual(result['src_off'], 0)
                self.assertEqual(result['src_addr'], addr)
                self.assertEqual(result['src_size'], len(b'needle'))

            with self.subTest('@ 10'):
                haystack = b'0123456789needle678901234'
                hunter = ConstantHunter(haystack, addr)
                result = hunter.find(b'needle')
                self.assertTrue(result is not None)
                self.assertEqual(result['src_off'], 10)
                self.assertEqual(result['src_addr'], addr + 10)
                self.assertEqual(result['src_size'], len(b'needle'))

            with self.subTest('@ 19'):
                haystack = b'0123456789012345678needle'
                hunter = ConstantHunter(haystack, addr)
                result = hunter.find(b'needle')
                self.assertTrue(result is not None)
                self.assertEqual(result['src_off'], 19)
                self.assertEqual(result['src_addr'], addr + 19)
                self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('Start offset = 6 (constructor)'):
            haystack = b'needle6789needle678901234'

            hunter = ConstantHunter(haystack, addr, 6)
            result = hunter.find(b'needle')

            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], 10)
            self.assertEqual(result['src_addr'], addr + 10)
            self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('Start offset = 6 (find)'):
            hunter = ConstantHunter(haystack, addr)
            result = hunter.find(b'needle', 6)

            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], 10)
            self.assertEqual(result['src_addr'], addr + 10)
            self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('Start offset = 6 (find)'):
            hunter = ConstantHunter(haystack, addr)
            result = hunter.find(b'needle', 6)

            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], 10)
            self.assertEqual(result['src_addr'], addr + 10)
            self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('End offset = 8 (constructor)'):
            haystack = b'0123456789needle678901234'

            with self.assertRaises(HunterResultNotFound):
                hunter = ConstantHunter(haystack, addr, end_offset=6)
                _ = hunter.find(b'needle')

        with self.subTest('End offset = 8 (find)'):
            haystack = b'0123456789needle678901234'

            with self.assertRaises(HunterResultNotFound):
                hunter = ConstantHunter(haystack, addr)
                _ = hunter.find(b'needle', end=8)

        with self.subTest('Start offset = 6, end offset = 15 (constructor)'):
            haystack = b'0123456789needle678901234'

            hunter = ConstantHunter(haystack, addr, 6, 15)
            result = hunter.find(b'needle')

            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], 10)
            self.assertEqual(result['src_addr'], addr + 10)
            self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('Start offset = 6, end offset = 15 (find)'):
            haystack = b'0123456789needle678901234'

            hunter = ConstantHunter(haystack, addr)
            result = hunter.find(b'needle', 6, 15)

            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], 10)
            self.assertEqual(result['src_addr'], addr + 10)
            self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('Start offset = 6, end offset = 15 (find) w/ gaps'):
            haystack = b'0123456789needle678901234'

            hunter = ConstantHunter(haystack, addr, gaps=[(addr + 4, 3), (addr + 19, 10)])
            result = hunter.find(b'needle', 6, 15)

            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], 10)
            self.assertEqual(result['src_addr'], addr + 10)
            self.assertEqual(result['src_size'], len(b'needle'))

        with self.subTest('Invalid start/end index'):
            with self.assertRaises(IndexError):
                hunter = ConstantHunter(haystack, addr)
                result = hunter.find(b'needle', 74)

            with self.assertRaises(IndexError):
                hunter = ConstantHunter(haystack, addr)
                result = hunter.find(b'needle', 10, 6)

            with self.assertRaises(IndexError):
                hunter = ConstantHunter(haystack, addr)
                result = hunter.find(b'needle', 6, 7)

    # This is exercising Hunter.finditer()
    def test_finditer(self):
        addr = 0x4321
        target = b'SongsFromUnderTheSink'  # Mischief Brew, 2016

        expected = [
            {'src_off': 0,   'src_addr': addr,       'src_size': len(target)},  # At beginning
            {'src_off': 37,  'src_addr': addr + 37,  'src_size': len(target)},
            {'src_off': 58,  'src_addr': addr + 58,  'src_size': len(target)},  # Back-to-back
            {'src_off': 84,  'src_addr': addr + 84,  'src_size': len(target)},
            {'src_off': 106, 'src_addr': addr + 106, 'src_size': len(target)},  # Runs up to end
        ]

        data = random_data(128)

        for e in expected:
            offset = e['src_off']
            size   = e['src_size']

            data[offset:offset + size] = target

        with self.subTest('No offsets'):
            results = []
            hunter = ConstantHunter(data, addr)
            for result in hunter.finditer(target):
                results.append(result)
            self.assertEqual(results, expected)

        with self.subTest('Offsets narrowing search (constructor) : 1, 127'):
            exp_subset = expected[1:]
            hunter = ConstantHunter(data, addr, 1, 127)
            results = []
            for result in hunter.finditer(target):
                results.append(result)
            self.assertEqual(results, exp_subset)

        with self.subTest('Offsets narrowing search (constructor) : 37, 126'):
            exp_subset = expected[1:]

            hunter = ConstantHunter(data, addr, 37, 126)
            results = []
            for result in hunter.finditer(target):
                results.append(result)
            self.assertEqual(results, exp_subset)

        with self.subTest('Offsets narrowing search (constructor) : 38, 125'):
            exp_subset = expected[2:-1]
            hunter = ConstantHunter(data, addr, 38, 125)
            results = []
            for result in hunter.finditer(target):
                results.append(result)
            self.assertEqual(results, exp_subset)

        hunter = ConstantHunter(data, addr)

        with self.subTest('Offsets narrowing search (finditr) : 1, 127'):
            exp_subset = expected[1:]
            results = []
            for result in hunter.finditer(target, 1, 127):
                results.append(result)

        with self.subTest('Offsets narrowing search (finditr) : 38, 126'):
            exp_subset = expected[2:]
            results = []
            for result in hunter.finditer(target, 38, 126):
                results.append(result)

        with self.subTest('Offsets narrowing search (finditr) : 38, 125'):
            exp_subset = expected[2:-1]
            results = []
            for result in hunter.finditer(target, 38, 125):
                results.append(result)
            self.assertEqual(results, exp_subset)

        with self.subTest('Gaps'):
            gaps = [(addr + 37, 10), (addr + 90, 1), (addr + 110, 5)]
            hunter = ConstantHunter(data, addr, gaps=gaps)
            exp_subset = [expected[0], expected[2]]
            results = []
            for result in hunter.finditer(target):
                results.append(result)
            self.assertEqual(results, exp_subset)
