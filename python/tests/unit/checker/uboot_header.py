# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring
# pylint: disable=attribute-defined-outside-init

from os.path import dirname, join, realpath
from unittest import TestCase

from depthcharge.checker import UBootHeaderChecker, SecurityRisk, SecurityImpact


class TestUBootHeaderChecker(TestCase):
    """
    Largely just exercises UBootHeaderChecker's constructor and load() method.
    The audit() implementation is common to that of UBootConfigChecker.
    """

    custom_risk = SecurityRisk('CUSTOM01',
                               SecurityImpact.RD_MEM | SecurityImpact.INFO_LEAK,
                               'test.src',
                               'summary-custom01',
                               'description-custom01',
                               'recommendation-custom01')

    resource_dir = realpath(join(dirname(__file__), '..', '..', 'resources'))

    @classmethod
    def resource(cls, filename: str):
        return realpath(join(cls.resource_dir, filename))

    def test_simple(self):
        header = self.resource('config_01.h')

        checker = UBootHeaderChecker('2011.13', self.resource_dir)
        config = checker.load(header)

        # Defined in specified header
        self.assertTrue('CONFIG_CMD_MEMORY' in config)
        self.assertTrue(config['CONFIG_CMD_MEMORY'][0])

        # Defined in #include'd header
        self.assertTrue('CONFIG_CMD_LOADS' in config)
        self.assertTrue(config['CONFIG_CMD_LOADS'][0])

        # Defined in #include'd header and then undef'd
        self.assertTrue('CONFIG_CMD_I2C' in config)
        self.assertFalse(config['CONFIG_CMD_I2C'][0])

        report = checker.audit()
        self.assertTrue('CONFIG_CMD_LOADS' in report)
        self.assertTrue('CONFIG_CMD_MEMORY' in report)
        self.assertFalse('CONFIG_CMD_I2C' in report)

    def test_dummy(self):
        header = self.resource('config_02.h')

        with self.subTest('Confim failure'):
            with self.assertRaises(ValueError):
                checker = UBootHeaderChecker('2011.13', self.resource_dir)
                _ = checker.load(header)

        with self.subTest('Confim dummy_headers works'):
            checker = UBootHeaderChecker('2011.13', self.resource_dir, dummy_headers=['test/induce_error.h'])
            _ = checker.load(header)

        with self.subTest('dummy_headers as string'):
            checker = UBootHeaderChecker('2011.13', self.resource_dir, dummy_headers='test/induce_error.h')
            _ = checker.load(header)

    def test_config(self):
        header = self.resource('config_03.h')
        config_in = {
            'INCLUDE_MEMORY_COMMANDS': (True, 'some.source'),
            'AN_INTEGER': (3, 'some.other.source'),
            'A_STR': ('Some string', 'src3'),
        }

        checker = UBootHeaderChecker('2011.13', self.resource_dir, config_defs=config_in)
        config_out = checker.load(header)

        self.assertTrue('INCLUDE_MEMORY_COMMANDS' in config_out)
        self.assertTrue('CONFIG_CMD_MEMORY' in config_out)
        self.assertTrue(config_out['CONFIG_CMD_MEMORY'][0])
