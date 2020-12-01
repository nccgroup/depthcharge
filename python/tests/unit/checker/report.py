# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring
# pylint: disable=attribute-defined-outside-init
#
# Files are checked against MD5 checksums after being eyeballed.
# Not ideal, but just a way to avoid inadvertent changes.
#

import os

from tempfile import gettempdir
from unittest import TestCase

from depthcharge.checker import Report, SecurityImpact, SecurityRisk

from ..test_utils import verify_md5sum


class TestReport(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.keep_files = os.getenv('DEPTHCHARGE_TEST_KEEP_FILES', '') != ''
        cls.filename_pfx = os.path.join(gettempdir(), 'depthcharge_report_test.')

    def setUp(self):
        self.filenames = None

    def tearDown(self):
        if self.filenames is not None and not self.keep_files:
            for filename in self.filenames:
                os.remove(filename)

    @staticmethod
    def _create_report():
        report = Report()

        report.add(
            SecurityRisk(
                'test01',
                SecurityImpact.RD_MEM | SecurityImpact.WR_MEM,
                'test01.src',
                'summary01',
                'description01',
                'recommendation01',
            )
        )

        report.add(
            SecurityRisk(
                'test02',
                SecurityImpact.RD_MEM,
                'test02.src',
                'summary02',
                'description02',
                'recommendation02',
            )
        )

        report.add(
            SecurityRisk(
                'test03',
                SecurityImpact.WR_MEM,
                'test03.src',
                'summary03',
                'description03',
                'recommendation03',
            )
        )

        # Shouldn't get added - duplicate identifier
        report.add(
            SecurityRisk(
                'test01',
                SecurityImpact.NONE,
                'test01.src.dupe',
                'summary01.dupe',
                'description01.dupe',
                'recommendation01.dupe',
            )
        )

        return report

    def _create_second_report(self):
        report = self._create_report()

        # New item
        ret = report.add(
            SecurityRisk(
                'test04',
                SecurityImpact.INFO_LEAK,
                'test_merge.src',
                'summary04',
                'description04',
                'recommendation04'
            )
        )
        self.assertEqual(ret, True)
        self.assertEqual(len(report), 4)

        # Duplicate item not added
        ret = report.add(
                SecurityRisk(
                    'test03',
                    SecurityImpact.LIMITED_WR_MEM,
                    'test03.src.dupe',
                    'summary03.dupe',
                    'description03.dupe',
                    'recommendation03.dupe',
                )
        )

        self.assertEqual(ret, False)
        self.assertEqual(len(report), 4)

        return report

    @staticmethod
    def _create_third_report():
        report = Report()
        report.add(
            SecurityRisk(
                identifier='test06',
                summary='summary06',
                impact=(SecurityImpact.WEAK_AUTH),
                source='test06.src',
                description='description06',
                recommendation='recommendation06'
            )
        )

        report.add(
            SecurityRisk(
                'test07',
                SecurityImpact.ATTACK_SURFACE,
                'test07.src',
                'summary07',
                'description07',
                'recommendation07'
            )
        )

        return report

    def test_constructor(self):
        _ = self._create_report()

    def next_filename(self, ext=None) -> str:
        if ext is not None:
            self.filenames = list()
            self.filename_i = 0
            self.filename_fmt = self.filename_pfx + '{:d}.' + ext

        ret = self.filename_fmt.format(self.filename_i)
        self.filename_i += 1
        return ret

    def test_csv(self):
        report = self._create_report()

        filename = self.next_filename('csv')
        with self.subTest(filename + ': CSV with header'):
            report.save_csv(filename, write_header=True)
            verify_md5sum(filename, 'eb56da21708cf560c7317176795546b6', self)

        filename = self.next_filename()
        with self.subTest(filename + ': CSV without header'):
            report.save_csv(filename, write_header=False)
            verify_md5sum(filename, '3f77137b215c9a31fb654bc8cd1bcd8a', self)

    def test_html(self):
        ts = '2020-10-23 23:29:51.092675'
        report = self._create_report()

        filename = self.next_filename('html')
        with self.subTest(filename + ': HTML table with header, no TS'):
            report.save_html(filename, write_header=True, timestamp=None)
            verify_md5sum(filename, 'b5002a997bb111a3bae13a8776934d82', self)

        filename = self.next_filename()
        with self.subTest(filename + ': HTML table with header, w/ TS'):
            report.save_html(filename, write_header=True, timestamp=ts)
            verify_md5sum(filename, 'b551b1c1253408cff3b0bc6574454cac', self)

        filename = self.next_filename()
        with self.subTest(filename + ': HTML table without header, no TS'):
            report.save_html(filename, write_header=False, timestamp=None)
            verify_md5sum(filename, '4f7fff546e1a5a4a17359e259fe5cb20', self)

        filename = self.next_filename()
        with self.subTest(filename + ': HTML table without header, w/ TS'):
            report.save_html(filename, write_header=False, timestamp=ts)
            verify_md5sum(filename, 'ed81fb47170f984f1da7f5afada0d0b0', self)

        filename = self.next_filename()
        with self.subTest(filename + ': HTML table only - with header, w/ TS'):
            report.save_html(filename, table_only=True, write_header=True, timestamp=ts)
            verify_md5sum(filename, '5df1de954509fd0cebcbff48f6498656', self)

        filename = self.next_filename()
        with self.subTest(filename + ': HTML table only - without header, w/ TS'):
            report.save_html(filename, table_only=True, write_header=False, timestamp=ts)
            verify_md5sum(filename, '32e7628493c8a6069aba453f2f0b6a02', self)

        filename = self.next_filename()
        with self.subTest(filename + ': HTML table only - without header, no TS'):
            report.save_html(filename, table_only=True, write_header=False, timestamp=None)
            verify_md5sum(filename, '32e7628493c8a6069aba453f2f0b6a02', self)

    def test_markdown(self):
        report = self._create_report()
        filename = self.next_filename('md')
        with self.subTest(filename):
            report.save_markdown(filename)
            verify_md5sum(filename, 'b41b2b2e7d3736efe1e095e3b32f2e8d', self)

    def test_len(self):
        report = self._create_report()
        self.assertEqual(len(report), 3)

    def test_add(self):
        # Entirety of test is in this method
        _ = self._create_second_report()

    def test_merge(self):
        report1 = self._create_report()
        report2 = self._create_second_report()

        self.assertEqual(len(report1), 3)
        report1.merge(report2)
        self.assertEqual(len(report1), 4)

    def test_merge_multiple(self):
        report1 = self._create_report()
        report2 = self._create_second_report()
        report3 = self._create_third_report()

        self.assertEqual(len(report1), 3)
        report1.merge(report2, report3)
        self.assertEqual(len(report1), 6)

    def test_ior(self):
        report1 = self._create_report()
        report2 = self._create_second_report()

        self.assertEqual(len(report1), 3)
        report1 |= report2
        self.assertEqual(len(report1), 4)
