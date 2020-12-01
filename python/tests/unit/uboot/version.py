# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# Relax style and documentation requirements for unit tests.
# pylint: disable=missing-function-docstring, missing-class-docstring
# pylint: disable=wildcard-import, line-too-long
#

"""
Unit tests for depthcharge.uboot.UBootVersion
"""

from unittest import TestCase
from depthcharge.uboot import UBootVersion, version_in_range


class TestUbootVersion(TestCase):

    def test_eq(self):
        test_cases = (
            ('1.1',         '1.1',          True),
            ('1.1.0',       '1.1',          True),  # Should never see this, but we treat these as equal.
            ('1.1.0-rc1',   '1.1-rc1',      True),  # Likewise (implicit sublevel), but with release candidate "extra"
            ('1.1.0-rc2',   '1.1-rc1',      False),
            ('2020.10',     '2020.07',      False),
            ('2020.01',     '2020.01',      True),
            ('2020.01',     '2020.1',       True),  # Don't care about strict %02d format.
            ('2020.01',     '2020.01-rc2',  False),
        )

        for tc in test_cases:
            with self.subTest(tc):
                a = UBootVersion(tc[0])
                b = UBootVersion(tc[1])
                self.assertEqual(a == b, tc[2])

    def test_lt(self):
        test_cases = (
            ('1.1',         '1.1',          False),
            ('1.1.0',       '1.1',          False),  # Should never see this, but we treat these as equal.
            ('1.1.0-rc1',   '1.1-rc1',      False),  # Likewise (implicit sublevel), but with release candidate "extra"
            ('1.1.0-rc2',   '1.1-rc1',      False),
            ('1.1.0-rc1',   '1.1-rc2',      True),
            ('2020.01',     '2020.04',      True),
            ('2020.1',       '2020.4',      True),   # Don't care about strict %02d format.
            ('2020.04',     '2020.04-rc2',  False),
            ('2020.00-rc2', '2020.04',      True),
            ('2020.04',     '2020.04',      False),
            ('2020.04',     '2021.04',      True),
            ('2020.04.01',  '2020.04.05',   True),
            ('2021.04',     '2020.04',      False),
            ('2020.04.03',  '2020.04.02',   False),
        )

        for tc in test_cases:
            with self.subTest(tc):
                a = UBootVersion(tc[0])
                b = UBootVersion(tc[1])
                self.assertEqual(a < b, tc[2])

    # Specific case from a bug. test_eq updated as well.
    def test_le(self):
        a = UBootVersion('2020.10')
        b = UBootVersion('2020.07')
        self.assertFalse(a <= b)

    def test_gt(self):
        test_cases = (
            ('1.1',         '1.1',          False),
            ('1.1.0',       '1.1',          False),  # Should never see this, but we treat these as equal.
            ('1.1.0-rc1',   '1.1-rc1',      False),  # Likewise (implicit sublevel), but with release candidate "extra"
            ('1.1.0-rc2',   '1.1-rc1',      True),
            ('1.1.0-rc1',   '1.1-rc2',      False),
            ('1.1.0-rc3',   '1.1-rc2',      True),
            ('2020.04',     '2020.01',      True),
            ('2020.4',      '2020.1',       True),   # Don't care about strict %02d format.
            ('2020.04',     '2020.04-rc2',  True),
            ('2020.00-rc2', '2020.04',      False),
            ('2020.04',     '2020.04',      False),
            ('2020.04',     '2021.04',      False),
            ('2020.04.01',  '2020.04.05',   False),
            ('2021.04',     '2020.04',      True),
            ('2020.04.03',  '2020.04.02',   True),
        )

        for tc in test_cases:
            with self.subTest(tc):
                a = UBootVersion(tc[0])
                b = UBootVersion(tc[1])
                self.assertEqual(a > b, tc[2])

    def test_compare(self):
        test_cases = (
            ('1.1',         '1.1',          0),
            ('1.1.0',       '1.1',          0),  # Should never see this, but we treat these as equal.
            ('1.1.0-rc1',   '1.1-rc1',      0),  # Likewise (implicit sublevel), but with release candidate "extra"
            ('1.1.0-rc2',   '1.1-rc1',      1),
            ('1.1.0-rc1',   '1.1-rc2',      -1),
            ('1.1.0-rc3',   '1.1-rc2',      1),
            ('2020.04',     '2020.01',      1),
            ('2020.4',      '2020.1',       1),   # Don't care about strict %02d format.
            ('2020.04',     '2020.04-rc2',  1),
            ('2020.00-rc2', '2020.04',      -1),
            ('2020.04',     '2020.04',      0),
            ('2020.04',     '2021.04',      -1),
            ('2020.04.01',  '2020.04.05',   -1),
            ('2021.04',     '2020.04',      1),
            ('2020.04.03',  '2020.04.02',   1),
        )

        for tc in test_cases:
            with self.subTest(tc):
                a = UBootVersion(tc[0])
                b = UBootVersion(tc[1])
                self.assertEqual(a.compare(b), tc[2])

    def test_invalid(self):
        test_cases = ('202001', '2020.a1', '2020-rc1', "Back off man, I'm a scientist.")
        for tc in test_cases:
            with self.subTest(tc):
                with self.assertRaises(ValueError):
                    _ = UBootVersion(tc)

    def test_find(self):
        tc = 'Okay, who brought the 2011.06-rc2 dog?'
        with self.subTest(tc):
            version = UBootVersion.find(tc)
            self.assertEqual(version, UBootVersion('2011.06-rc2'))

        tc = 'Okay, who brought the dog?'
        with self.subTest(tc):
            version = UBootVersion.find(tc)
            self.assertTrue(version is None)

    def test_range(self):
        test_cases = (
            ('2020.01',     '2011.06-rc1', '2050.11',       True),
            ('2012.09',     '2049.06-rc1', '2050.11',       False),
            ('1.1',         '1.1',         '1.1',           True),
            ('1.2',         '1.1',         '1.2-rc1',       False),
            ('1.2-rc1',     '1.1',         '1.2',           True),
            ('2016.11-rc3', '2016.11-rc2', '2016.11-rc4',   True),
            ('2016.11-rc5', '2016.11-rc2', '2016.11-rc4',   False),
            ('2014.11-rc5', '2016.11-rc2', '2016.11-rc4',   False),
        )

        for tc in test_cases:
            with self.subTest(tc):
                version = UBootVersion(tc[0])
                minver  = UBootVersion(tc[1])
                maxver  = UBootVersion(tc[2])

                self.assertEqual(version.in_range(minver, maxver), tc[3])
                self.assertEqual(version.in_range(tc[1],  maxver), tc[3])
                self.assertEqual(version.in_range(minver, tc[2]),  tc[3])
                self.assertEqual(version.in_range(tc[1],  tc[2]),  tc[3])

    def test_range_convenience_fn(self):
        test_cases = (
            ('2020.01',     '2011.06-rc1', '2050.11',       True),
            ('2012.09',     '2049.06-rc1', '2050.11',       False),
            ('1.1',         '1.1',         '1.1',           True),
            ('1.2',         '1.1',         '1.2-rc1',       False),
            ('1.2-rc1',     '1.1',         '1.2',           True),
            ('2016.11-rc3', '2016.11-rc2', '2016.11-rc4',   True),
            ('2016.11-rc5', '2016.11-rc2', '2016.11-rc4',   False),
            ('2014.11-rc5', '2016.11-rc2', '2016.11-rc4',   False),
        )

        for tc in test_cases:
            with self.subTest(tc):
                version = tc[0]
                minver  = tc[1]
                maxver  = tc[2]

                self.assertEqual(version_in_range(version, minver, maxver), tc[3])
