# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# Relax style and documentation requirements for unit tests.
# pylint: disable=missing-function-docstring, missing-class-docstring
# pylint: disable=wildcard-import, line-too-long
#

"""
Unit tests for depthcharge.uboot.env
"""

import os

from unittest import TestCase
from depthcharge import uboot

_ENV_DICT = {
    'addip': 'setenv bootargs ${bootargs} ip=${ipaddr}:${serverip}:${gatewayip}:${netmask}:${hostname}:eth0:off',
    'hostname': 'Philbert',
    'ipaddr': '192.168.0.200',
    'serverip': '192.168.0.10',
    'gatewayip': '192.168.0.1',
    'netmask': '255.255.255.0',
    'boot_dtb': '${loadaddr} - ${dtb_addr}',
    'loadaddr': '0x82000000',
    'dtb_addr': '0x83000000',
    'dtb_size': '0x20000',
}

_ENV_DICT_EXP = {
    'addip': 'setenv bootargs ${bootargs} ip=192.168.0.200:192.168.0.10:192.168.0.1:255.255.255.0:Philbert:eth0:off',
    'boot_dtb': '0x82000000 - 0x83000000',
    'dtb_addr': '0x83000000',
    'dtb_size': '0x20000',
    'gatewayip': '192.168.0.1',
    'hostname': 'Philbert',
    'ipaddr': '192.168.0.200',
    'loadaddr': '0x82000000',
    'netmask': '255.255.255.0',
    'serverip': '192.168.0.10'
}

_ENV_TEXT = """\
addip=setenv bootargs ${bootargs} ip=${ipaddr}:${serverip}:${gatewayip}:${netmask}:${hostname}:eth0:off
boot_dtb=${loadaddr} - ${dtb_addr}
dtb_addr=0x83000000
dtb_size=0x20000
gatewayip=192.168.0.1
hostname=Philbert
ipaddr=192.168.0.200
loadaddr=0x82000000
netmask=255.255.255.0
serverip=192.168.0.10
"""

_ENV_TEXT_EXP = """\
addip=setenv bootargs ${bootargs} ip=192.168.0.200:192.168.0.10:192.168.0.1:255.255.255.0:Philbert:eth0:off
boot_dtb=0x82000000 - 0x83000000
dtb_addr=0x83000000
dtb_size=0x20000
gatewayip=192.168.0.1
hostname=Philbert
ipaddr=192.168.0.200
loadaddr=0x82000000
netmask=255.255.255.0
serverip=192.168.0.10
"""


class TestUbootEnvFns(TestCase):
    """
    Test depthcharge.uboot.env functions focused on environment data.
    """

    def test_parse(self):
        env = uboot.env.parse(_ENV_TEXT)
        self.assertEqual(env, _ENV_DICT)

    def test_expand(self):
        env = uboot.env.expand(_ENV_DICT)
        self.assertEqual(env, _ENV_DICT_EXP)

    def test_save_load(self):
        filename = 'depthcharge.uboot.env_save_load.test'
        uboot.env.save(filename, _ENV_DICT)
        env = uboot.load(filename)
        self.assertEqual(env, _ENV_DICT)
        os.remove(filename)

    def test_raw_save_load(self):
        arch = 'arm'
        flags = 0xf
        size = 0x2000

        filename = 'depthcharge.uboot.raw_env_save_load.test'

        with self.subTest('No header'):
            uboot.save_raw_environment(filename, _ENV_DICT, size, arch, no_header=True)
            env, metadata = uboot.env.load_raw(filename, arch, has_crc=False)

            self.assertEqual(env, _ENV_DICT)
            self.assertEqual(metadata['size'], size)

        with self.subTest('CRC, no flags'):
            uboot.save_raw_environment(filename, _ENV_DICT, size, arch)
            env, metadata = uboot.env.load_raw(filename, arch)

            self.assertEqual(env, _ENV_DICT)
            self.assertEqual(metadata['size'], size - 4)
            self.assertEqual(metadata['crc'], metadata['actual_crc'])

        with self.subTest('CRC + flags'):
            uboot.save_raw_environment(filename, _ENV_DICT, size, arch, flags=flags)
            env, metadata = uboot.env.load_raw(filename, arch, has_flags=True)

            self.assertEqual(env, _ENV_DICT)
            self.assertEqual(metadata['size'], size - 5)
            self.assertEqual(metadata['crc'], metadata['actual_crc'])
            self.assertEqual(metadata['flags'], flags)

        os.remove(filename)
