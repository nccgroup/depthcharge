# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Unit tests for depthcharge.hunter.ReverseCRC32Hunter
"""
import os
import sys

from unittest import TestCase
from zlib import crc32

import depthcharge
from depthcharge.hunter import ReverseCRC32Hunter, HunterResultNotFound

from ..test_utils import random_data


class TestReverseCRC32Hunter(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._old_log_level = depthcharge.log.get_level()
        # Set to ERROR (unless there's an env override) to hide progress bars
        depthcharge.log.set_level(os.getenv('DEPTHCHARGE_LOG_LEVEL', depthcharge.log.ERROR))

    @classmethod
    def tearDownClass(cls):
        depthcharge.log.set_level(cls._old_log_level)

    def setUp(self):
        self.data = random_data(128)

        # Ensure we have sequences in place for our test cases
        self.data[33:37] = b'\x00\x00\x00\x00'
        self.data[13:17] = b'\x42\xc0\xff\xee'

        self.data = bytes(self.data)

    def test_find(self):
        base = 0xcafe1400
        hunter = ReverseCRC32Hunter(self.data, base)

        # CRC32 output, input, offset, # iterations
        test_cases = [
            (0xd202ef8d, b'\x00', 33, 1),
            ((0xd202ef8d).to_bytes(4, sys.byteorder), b'\x00', 33, 1),
            (0x41d912ff, b'\x00\x00', 33, 1),
            (0xff41d912, b'\x00\x00\x00', 33, 1),
            (0x2144df1c, b'\x00\x00\x00\x00', 33, 1),
            (0xe4274e42, b'\x42', 13, 37),
            (0xbda7a6c3, b'\x42\xc0', 13, 1337),
            (0x7beaab9e, b'\x42\xc0\xff', 13, 93),
            (0xd420c27a, b'\x42\xc0\xff\xee', 13, 12345),
        ]

        for tc in test_cases:
            with self.subTest(tc):
                result = hunter.find(tc[0], max_iterations=12345)

                offset      = result['src_off']
                addr        = result['src_addr']
                size        = result['src_size']
                iterations  = result['iterations']

                expected_size       = len(tc[1])
                expected_offset     = tc[2]
                expected_iterations = tc[3]

                self.assertTrue(result is not None)
                self.assertEqual(len(result), 4)
                self.assertEqual(offset, expected_offset)
                self.assertEqual(addr, base + offset)
                self.assertEqual(size, expected_size)
                self.assertEqual(iterations, expected_iterations)

    def test_crc32_build_stratagem_quick(self):
        base = 0x41424300

        payload = (0xd202ef8d).to_bytes(4, sys.byteorder) + \
                  (0xff41d912).to_bytes(4, sys.byteorder) + \
                  (0x7beaab9e).to_bytes(4, sys.byteorder) + \
                  (0xd420c27a).to_bytes(4, sys.byteorder) + \
                  (0x2144df1c).to_bytes(4, sys.byteorder) + \
                  (0x41d912ff).to_bytes(4, sys.byteorder)

        expected = [
            {'dst_off':  0, 'src_addr': base + 33, 'src_size': 1, 'iterations': 1},
            {'dst_off':  4, 'src_addr': base + 33, 'src_size': 3, 'iterations': 1},
            {'dst_off':  8, 'src_addr': base + 13, 'src_size': 3, 'iterations': 93},
            {'dst_off': 12, 'src_addr': base + 13, 'src_size': 4, 'iterations': 12345},
            {'dst_off': 16, 'src_addr': base + 33, 'src_size': 4, 'iterations': 1},
            {'dst_off': 20, 'src_addr': base + 33, 'src_size': 2, 'iterations': 1},
        ]

        with self.subTest('No gaps'):
            hunter = ReverseCRC32Hunter(self.data, base)
            stratagem = hunter.build_stratagem(payload, max_iterations=12345)

            self.assertTrue(stratagem is not None)
            self.assertEqual(len(stratagem), len(expected))

            matches = [False] * len(expected)
            for i in range(0, len(expected)):
                for entry in stratagem:
                    if entry == expected[i]:
                        matches[i] = True
                        break

            for i in range(0, len(matches)):
                msg = ''
                if matches[i] is False:
                    msg = 'No match for: ' + str(expected[i]) + ' - Results:\n'
                    for entry in stratagem:
                        msg += ' ' + str(entry) + '\n'

                self.assertTrue(matches[i], msg=msg)

        with self.subTest('With gaps'):
            with self.assertRaises(HunterResultNotFound):
                hunter = ReverseCRC32Hunter(self.data, base, gaps=[(base + 13, 4)])
                stratagem = hunter.build_stratagem(payload, max_iterations=12345)

            with self.assertRaises(HunterResultNotFound):
                hunter = ReverseCRC32Hunter(self.data, base, gaps=[(base + 13, 4), (base + 30, 2)])
                stratagem = hunter.build_stratagem(payload, max_iterations=12345)

            hunter = ReverseCRC32Hunter(self.data, base, gaps=[(base + 30, 2)])
            stratagem = hunter.build_stratagem(payload, max_iterations=12345)

            self.assertTrue(stratagem is not None)
            self.assertEqual(len(stratagem), len(expected))

            matches = [False] * len(expected)
            for i in range(0, len(expected)):
                for entry in stratagem:
                    if entry == expected[i]:
                        matches[i] = True
                        break

            for i in range(0, len(matches)):
                msg = ''
                if matches[i] is False:
                    msg = 'No match for: ' + str(expected[i]) + ' - Results:\n'
                    for entry in stratagem:
                        msg += ' ' + str(entry) + '\n'

                self.assertTrue(matches[i], msg=msg)

    def _validate_crc32_stratagem(self, target, src_data, stratagem):
        buf = bytearray(len(target))
        self.assertTrue(stratagem is not None)

        src_slice = None

        # An unfortunate bit of code duplication with CRC32Writer.write
        for entry in stratagem:
            iterations = entry['iterations']
            input_size = entry['src_size']
            d          = entry['dst_off']

            self.assertTrue(iterations > 0)
            self.assertTrue(input_size > 0)

            if 'tsrc_off' in entry:
                # Should not be used.
                self.assertTrue(entry['src_addr'] == -1)
                i = entry['tsrc_off']
                src_slice = buf[i:i + input_size]
            else:
                i = entry['src_addr']
                src_slice = src_data[i:i + input_size]

            buf[d:d + 4] = crc32(src_slice).to_bytes(4, sys.byteorder)
            for i in range(1, iterations):
                buf[d:d + 4] = crc32(buf[d:d + 4]).to_bytes(4, sys.byteorder)

        # It should not have grown or shrunk. If it did,
        # the test code is buggy.
        self.assertTrue(len(buf) == len(target))

        buf = bytes(buf)
        msg = ''
        if target != buf:
            msg = 'target != buf - Stratagem:\n'
            for entry in stratagem:
                msg += '    ' + str(entry) + '\n'

        self.assertEqual(target, bytes(buf), msg=msg)

    def test_crc32_build_stratagem_zebra(self):
        for i in range(0,  15):
            with self.subTest('Seed=' + str(i)):
                data = random_data(8 * 1024, ret_bytes=True, seed=i)
                payload = b'STRT' + b'zebra' * 8 + b'DONE'
                hunter = ReverseCRC32Hunter(data, 0, revlut_maxlen=200)
                stratagem = hunter.build_stratagem(payload, max_iterations=10000)
                self._validate_crc32_stratagem(payload, data, stratagem)

    def test_crc32_build_stratagem_raven(self):
        data = random_data(8 * 1024)

        # Insert a sequence that specifically results in a stratagem entry
        # with a size of 7 and only a single iteration. This is a special
        # and rare edge case that I previously had a silly bug in.
        # It results in the CRC32 result: ' the'
        data[42:42 + 7] = b'\xfd\xff\xf7\xba\xfd\x01('

        # Another instance of this edge case, for which the result ('n th')
        # should occur twice in our payload along 4-byte boundaries.
        data[3:3 + 4] = b'\xe9\x13\x07\xf8'

        data = bytes(data)

        payload = _RAVEN.encode('utf-8')
        hunter = ReverseCRC32Hunter(data, 0, revlut_maxlen=128)
        stratagem = hunter.build_stratagem(payload, max_iterations=500000)
        self._validate_crc32_stratagem(payload, data, stratagem)


_RAVEN = """
"Prophet!" said I, "thing of evil!—prophet still, if bird or devil!
By that Heaven that bends above us—by that God we both adore—
Tell this soul with sorrow laden if, within the distant Aidenn,
It shall clasp a sainted maiden whom the angels name Lenore—
Clasp a rare and radiant maiden whom the angels name Lenore."
            Quoth the Raven "Nevermore."

"Be that word our sign of parting, bird or fiend!" I shrieked, upstarting—
"Get thee back into the tempest and the Night's Plutonian shore!
Leave no black plume as a token of that lie thy soul hath spoken!
Leave my loneliness unbroken!—quit the bust above my door!
Take thy beak from out my heart, and take thy form from off my door!"
            Quoth the Raven "Nevermore."

And the Raven, never flitting, still is sitting, still is sitting
On the pallid bust of Pallas just above my chamber door;
And his eyes have all the seeming of a demon's that is dreaming,
And the lamp-light o'er him streaming throws his shadow on the floor;
And my soul from out that shadow that lies floating on the floor
           Shall be lifted—nevermore!
"""
