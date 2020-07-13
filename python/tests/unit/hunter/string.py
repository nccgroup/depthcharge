# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring

"""
Unit tests for depthcharge.hunter.StringHunger
"""

from unittest import TestCase
from depthcharge.hunter import StringHunter, HunterResultNotFound
from ..test_utils import random_data


class TestStringHunter(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.addr = 0x87800000
        data = random_data(512)

        cls.expected = [
            # Offset    String
            (0,         b'hello world, from test case\x00'),
            (117,       b'I want to conquer the world!\x00'),   # len=29
            (256,       b'String containing\r\na new line\x00'),
            (309,       b'So\r\nMany\nNew\r\nLines!\r\n\x00'),  # len=23
            (309 + 23,  b'Back-to-back string ~`!@#$%^&*_-+=,.<>:"\'[]{}\\|\x00'),  # len=48
            (501,       b'0123456789\x00')
        ]

        # Insert test case data
        for entry in cls.expected:
            offset = entry[0]
            string_data = entry[1]
            string_len = len(string_data)

            data[offset:offset + string_len] = string_data
            if offset > 0 and data[offset - 1] != 0x00:
                # Ensure non-string data precedes our test data
                data[offset - 1] = 0x03

        cls.data = bytes(data)

    def _validate_entry(self, result, exp_entry):
        exp_off = exp_entry[0]
        exp_addr = self.addr + exp_off
        exp_len = len(exp_entry[1])

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result['src_off'], exp_off)
        self.assertEqual(result['src_addr'], exp_addr)
        self.assertEqual(result['src_size'], exp_len)

    def test_find(self):
        hunter = StringHunter(self.data, self.addr)

        with self.subTest('Any string @ 0'):
            result = hunter.find(None, min_len=5, max_len=35)
            self._validate_entry(result, self.expected[0])

        with self.subTest('Any string @ 297'):
            result = hunter.find(None, min_len=3, max_len=49, start=297)
            self._validate_entry(result, self.expected[3])

        with self.subTest('Any string @ 332 w/ no bounds'):
            result = hunter.find(None, start=332)
            self._validate_entry(result, self.expected[4])

            result = hunter.find(None, start=332, min_len=-1)
            self._validate_entry(result, self.expected[4])

            result = hunter.find(None, start=332, max_len=-1)
            self._validate_entry(result, self.expected[4])

            result = hunter.find(None, start=332, min_len=-1, max_len=-1)
            self._validate_entry(result, self.expected[4])

        with self.subTest('Any string @ 332 w/ bounds: (min=48, max=100)'):
            result = hunter.find(None, min_len=48, max_len=100, start=332)
            self._validate_entry(result, self.expected[4])

        with self.subTest('Any string @ 332 w/ bounds (min=48, max=48)'):
            result = hunter.find(None, min_len=48, max_len=48, start=332)
            self._validate_entry(result, self.expected[4])

        with self.subTest('Overconstrained - no results'):
            with self.assertRaises(HunterResultNotFound):
                result = hunter.find(None, min_len=49, start=332)
                self._validate_entry(result, self.expected[4])

        with self.subTest('Custom pattern, str'):
            result = hunter.find('[a-zA-Z ]+world!?')
            self._validate_entry(result, self.expected[1])

        with self.subTest('Custom pattern, bytes'):
            result = hunter.find(b'([a-zA-Z ]+world!?|0123456789)')
            self._validate_entry(result, self.expected[1])

            result = hunter.find(b'([a-zA-Z ]+world!?|0123456789)', start=300)
            self._validate_entry(result, self.expected[-1])

        with self.subTest('Start offset=100'):
            hunter = StringHunter(self.data, self.addr, start_offset=100)
            result = hunter.find(None)
            self._validate_entry(result, self.expected[1])

        with self.subTest('Start offset=100, End offset=145'):
            hunter = StringHunter(self.data, self.addr, start_offset=100, end_offset=145)
            result = hunter.find(None)
            self._validate_entry(result, self.expected[1])

            hunter = StringHunter(self.data, self.addr, start_offset=100, end_offset=145)
            result = hunter.find(None, min_len=29, max_len=29)
            self._validate_entry(result, self.expected[1])

        with self.subTest('Start offset=100, End offset=144'):
            with self.assertRaises(HunterResultNotFound):
                hunter = StringHunter(self.data, self.addr, start_offset=100, end_offset=144)
                result = hunter.find(None)
                self._validate_entry(result, self.expected[1])

    def test_string_at(self):
        hunter = StringHunter(self.data, self.addr)
        result = hunter.string_at(self.addr + 501)
        expected = self.expected[-1][1][:-1]   # [Last item], [second field], [:trim null byte]
        self.assertEqual(expected.decode('ascii'), result)

        result = hunter.string_at(self.addr + 501, min_len=10, max_len=11)
        expected = self.expected[-1][1][:-1]   # [Last item], [second field], [:trim null byte]
        self.assertEqual(expected.decode('ascii'), result)

        with self.assertRaises(HunterResultNotFound):
            result = hunter.string_at(self.addr + 502, min_len=11)

    def test_find_iter_no_gaps(self):
        match = [False] * len(self.expected)
        hunter = StringHunter(self.data, self.addr)

        for result in hunter.finditer(None):
            self.assertTrue(isinstance(result, dict))
            offset = result['src_off']
            # addr = result['src_addr']
            length = result['src_size']

            data = self.data[offset:offset + length]

            for i in range(0, len(self.expected)):
                if offset == self.expected[i][0]:
                    self.assertEqual(self.expected[i][1], data)
                    match[i] = True
                    break

        self.assertEqual(sum(match), len(self.expected))

    def test_find_iter_gaps(self):
        match = [False] * len(self.expected)
        gaps = [(self.addr + 100, 200), (self.addr + 423, 80)]
        hunter = StringHunter(self.data, self.addr, gaps=gaps)
        for result in hunter.finditer(None):
            self.assertTrue(isinstance(result, dict))
            offset = result['src_off']
            # addr = result['src_addr']
            length = result['src_size']

            data = self.data[offset:offset + length]

            for i in range(0, len(self.expected)):
                if offset == self.expected[i][0]:
                    self.assertEqual(self.expected[i][1], data)
                    match[i] = True
                    break

        self.assertEqual(sum(match), len(self.expected) - 3)
