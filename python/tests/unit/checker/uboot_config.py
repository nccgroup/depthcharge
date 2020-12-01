# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring
# pylint: disable=attribute-defined-outside-init

import re

from os.path import dirname, join, realpath
from unittest import TestCase

from depthcharge.checker import UBootConfigChecker, SecurityRisk, SecurityImpact


class TestUBootConfigChecker(TestCase):
    """
    Test that builtin-in security and registered handlers are reporting correctly.
    """

    custom_risk = SecurityRisk('CUSTOM01',
                               SecurityImpact.RD_MEM | SecurityImpact.INFO_LEAK,
                               'test.src',
                               'summary-custom01',
                               'description-custom01',
                               'recommendation-custom01')

    @staticmethod
    def resource(filename: str):
        return realpath(join(dirname(__file__), '..', '..', 'resources', filename))

    def test_load_audit(self):
        filename = self.resource('dotconfig-01.txt')
        checker = UBootConfigChecker('2020.12')
        _ = checker.load(filename)
        _ = checker.audit()

    def test_fit_vulns(self):
        filename = self.resource('dotconfig-02.txt')

        def run_subtest(ver, risk_idents, exclude_idents):
            with self.subTest(ver + ' - ' + str(risk_idents)):
                checker = UBootConfigChecker(ver)
                config = checker.load(filename)

                self.assertTrue(config['CONFIG_FIT_SIGNATURE'][0])
                report = checker.audit()
                for ident in risk_idents:
                    self.assertTrue(ident in report)

                for ident in exclude_idents:
                    self.assertFalse(ident in report)

        run_subtest('2013.07', ('CVE-2018-3968',), ())
        run_subtest('2020.01', ('CVE-2020-10648',), ())

        excludes = ('CVE-2018-3968', 'CVE-2020-10648')
        run_subtest('2020.04', (), excludes)

        filename = self.resource('dotconfig-03.txt')
        run_subtest('2020.04', ('BOTH_LEGACY_AND_FIT_SIG_ENABLED',),  excludes)

    def test_custom_bool_handler(self):
        filename = self.resource('dotconfig-02.txt')

        with self.subTest('CONFIG_FOO=y'):
            checker = UBootConfigChecker('2020.04')
            checker.register_handler('CONFIG_FOO', True, self.custom_risk)
            config = checker.load(filename)

            self.assertTrue('CONFIG_FOO' in config)
            self.assertTrue(config['CONFIG_FOO'][0])

            report = checker.audit()
            self.assertTrue('CUSTOM01' in report)

        with self.subTest('CONFIG_BAR=n'):
            checker = UBootConfigChecker('2020.04')
            checker.register_handler('CONFIG_BAR', False, self.custom_risk)
            config = checker.load(filename)

            self.assertTrue('CONFIG_BAR' in config)
            self.assertFalse(config['CONFIG_BAR'][0])

            report = checker.audit()
            self.assertTrue('CUSTOM01' in report)

    def test_custom_string_handler(self):
        filename = self.resource('dotconfig-02.txt')

        checker = UBootConfigChecker('2020.01')
        match_str = '"Hell of a damn grave. Wish it were mine."'
        checker.register_handler('CONFIG_ROYAL_TENENBAUM', match_str, self.custom_risk)

        config = checker.load(filename)
        self.assertTrue('CONFIG_ROYAL_TENENBAUM' in config)
        self.assertEqual(config['CONFIG_ROYAL_TENENBAUM'][0], match_str)

        report = checker.audit()
        self.assertTrue('CUSTOM01' in report)

    def test_custom_regex_handler(self):
        filename = self.resource('dotconfig-02.txt')

        checker = UBootConfigChecker('2020.01')
        checker.register_handler('CONFIG_MY_VOICE', re.compile(r'[A-Z_]+'), self.custom_risk)

        config = checker.load(filename)
        self.assertTrue('CONFIG_MY_VOICE' in config)
        self.assertEqual(config['CONFIG_MY_VOICE'][0], 'IS_MY_PASSPORT')

        report = checker.audit()
        self.assertTrue('CUSTOM01' in report)

    def _test_handler(self, value, user_data):
        self.assertEqual(2001, int(value))
        self.assertTrue(user_data is self)
        return True

    def test_custom_fn_handler(self):
        filename = self.resource('dotconfig-02.txt')

        checker = UBootConfigChecker('2020.01')
        checker.register_handler('CONFIG_SPACE_ODYSSEY', self._test_handler, self.custom_risk, self)

        config = checker.load(filename)
        self.assertTrue('CONFIG_SPACE_ODYSSEY' in config)
        self.assertEqual(config['CONFIG_SPACE_ODYSSEY'][0], '2001')

        report = checker.audit()
        self.assertTrue('CUSTOM01' in report)

    def test_spl_item(self):
        filename = self.resource('dotconfig-04.txt')
        checker = UBootConfigChecker('2019.04')
        config = checker.load(filename)

        self.assertTrue('CONFIG_SPL_FS_EXT4' in config)
        self.assertTrue(config['CONFIG_SPL_FS_EXT4'][0])

        report = checker.audit()
        self.assertTrue('CVE-2019-11059' in report)
