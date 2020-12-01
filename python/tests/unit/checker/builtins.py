# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-module-docstring

import os
from tempfile import gettempdir
from unittest import TestCase

from depthcharge.checker import Report
from depthcharge.checker._builtins import _BUILTIN_DEFS


class TestImportBuiltins(TestCase):
    """
    Simple test to ensure that all builtin checkers aren't woefully broken.
    Doubles as a way to export a report inclusive of everything contained in
    depthcharge.checker._builtins
    """

    @classmethod
    def setUpClass(cls):
        cls.keep_files = os.getenv('DEPTHCHARGE_TEST_KEEP_FILES', '') != ''
        cls.pfx = os.path.join(gettempdir(), 'depthcharge_builtins_test.')

        cls.builtin_risks = []
        for builtin in _BUILTIN_DEFS:
            cls.builtin_risks.append(builtin[2])

    def _create_report(self, ext):
        report = Report()
        for risk in self.builtin_risks:
            risk['source'] = 'test_html.' + ext
            report.add(risk)
        return report

    def test_csv(self):
        filename = self.pfx + 'csv'
        report = self._create_report('csv')
        report.save_csv(filename)

        if not self.keep_files:
            os.remove(filename)

    def test_html(self):
        filename = self.pfx + 'html'
        report = self._create_report('html')
        report.save_html(filename)

        if not self.keep_files:
            os.remove(filename)

    def test_markdown(self):
        filename = self.pfx + 'md'
        report = self._create_report('md')
        report.save_markdown(filename)

        if not self.keep_files:
            os.remove(filename)
