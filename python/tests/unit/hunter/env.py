# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring
# flake8: noqa=line-too-long

"""
Unit tests for depthcharge.hunter.EnvironmentHunter
"""

from unittest import TestCase
from zlib import crc32

from depthcharge import uboot
from depthcharge.hunter import EnvironmentHunter, HunterResultNotFound

from ..test_utils import random_data

# Fun test case from a U-boot sandbox build. Tast byte of the CRC is a printable
# character, which causes our regex to match 1 char early.
_ENV = uboot.parse_environment("""\
arch=sandbox
baudrate=115200
board=sandbox
board_name=sandbox
boot_a_script=load ${devtype} ${devnum}:${distro_bootpart} ${scriptaddr} ${prefix}${script}; source ${scriptaddr}
boot_extlinux=sysboot ${devtype} ${devnum}:${distro_bootpart} any ${scriptaddr} ${prefix}${boot_syslinux_conf}
boot_net_usb_start=usb start
boot_pci_enum=pci enum
boot_prefixes=/ /boot/
boot_script_dhcp=boot.scr.uimg
boot_scripts=boot.scr.uimg boot.scr
boot_syslinux_conf=extlinux/extlinux.conf
boot_targets=host1 host0
bootcmd=run distro_bootcmd
bootcmd_host0=devnum=0; run host_boot
bootcmd_host1=devnum=1; run host_boot
bootcount=1
bootdelay=2
bootm_size=0x10000000
cpu=sandbox
distro_bootcmd=scsi_need_init=; setenv nvme_need_init; setenv ide_need_init; virtio_need_init=; for target in ${boot_targets}; do run bootcmd_${target}; done
eth1addr=00:00:11:22:33:45
eth3addr=00:00:11:22:33:46
eth5addr=00:00:11:22:33:47
ethaddr=00:00:11:22:33:44
fdt_addr_r=0xc00000
fdtcontroladdr=5dccc70
host_boot=if host dev ${devnum}; then devtype=host; run scan_dev_for_boot_part; fi
ide_boot=run ide_init; if ide dev ${devnum}; then devtype=ide; run scan_dev_for_boot_part; fi
ide_init=if ${ide_need_init}; then setenv ide_need_init false; ide reset; fi
ipaddr=1.2.3.4
kernel_addr_r=0x1000000
nvme_boot=run boot_pci_enum; run nvme_init; if nvme dev ${devnum}; then devtype=nvme; run scan_dev_for_boot_part; fi
nvme_init=if ${nvme_need_init}; then setenv nvme_need_init false; nvme scan; fi
pxefile_addr_r=0x2000
ramdisk_addr_r=0x2000000
sata_boot=if sata dev ${devnum}; then devtype=sata; run scan_dev_for_boot_part; fi
scan_dev_for_boot=echo Scanning ${devtype} ${devnum}:${distro_bootpart}...; for prefix in ${boot_prefixes}; do run scan_dev_for_extlinux; run scan_dev_for_scripts; done;
scan_dev_for_boot_part=part list ${devtype} ${devnum} -bootable devplist; env exists devplist || setenv devplist 1; for distro_bootpart in ${devplist}; do if fstype ${devtype} ${devnum}:${distro_bootpart} bootfstype; then run scan_dev_for_boot; fi; done; setenv devplist
scan_dev_for_extlinux=if test -e ${devtype} ${devnum}:${distro_bootpart} ${prefix}${boot_syslinux_conf}; then echo Found ${prefix}${boot_syslinux_conf}; run boot_extlinux; echo SCRIPT FAILED: continuing...; fi
scan_dev_for_scripts=for script in ${boot_scripts}; do if test -e ${devtype} ${devnum}:${distro_bootpart} ${prefix}${script}; then echo Found U-Boot script ${prefix}${script}; run boot_a_script; echo SCRIPT FAILED: continuing...; fi; done
scriptaddr=0x1000
scsi_boot=run scsi_init; if scsi dev ${devnum}; then devtype=scsi; run scan_dev_for_boot_part; fi
scsi_init=if ${scsi_need_init}; then scsi_need_init=false; scsi scan; fi
stderr=serial,vidconsole
stdin=serial,cros-ec-keyb,usbkbd
stdout=serial,vidconsole
usb_boot=usb start; if usb dev ${devnum}; then devtype=usb; run scan_dev_for_boot_part; fi
virtio_boot=run boot_pci_enum; run virtio_init; if virtio dev ${devnum}; then devtype=virtio; run scan_dev_for_boot_part; fi
virtio_init=if ${virtio_need_init}; then virtio_need_init=false; virtio scan; fi
""")

_ENV_BIN_LEN = 3044


class TestEnvironmentHunter(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.blob = bytearray()

        env_headerless = uboot.create_raw_environment(_ENV, _ENV_BIN_LEN, 'arm', no_header=True)

        # Headerless copy #1 at start of image
        cls.blob += env_headerless

        cls.blob += random_data(127, seed=0) + b'\0'

        # Copy #2
        cls.blob += env_headerless

        cls.blob += random_data(63, seed=1) + b'\0'

        # Environment with a CRC32 header, but no flags byte. Exact fit.
        cls.blob += uboot.create_raw_environment(_ENV, 4096, 'arm')
        cls.env_size = 4092

        cls.blob += random_data(255, seed=2)

        # Redundant envs
        cls.blob += uboot.create_raw_environment(_ENV, 4096, 'arm', flags=0x5)
        cls.blob += uboot.create_raw_environment(_ENV, 4096, 'arm', flags=0x4)

        cls.blob += random_data(55, seed=2)


    def test_find(self):
        base = 0x2000

        hunter = EnvironmentHunter(self.blob, base)

        with self.subTest('Headerless @ offset 0'):
            result = hunter.find(None)
            self.assertEqual(result['src_addr'], base)
            self.assertEqual(result['src_off'],  0)
            self.assertEqual(result['src_size'], _ENV_BIN_LEN)
            self.assertFalse('flags' in result)
            self.assertFalse('crc32' in result)
            self.assertFalse('actual_crc32' in result)

            result = hunter.find('ipaddr')
            self.assertEqual(result['src_addr'], base)
            self.assertEqual(result['src_off'],  0)
            self.assertEqual(result['src_size'], _ENV_BIN_LEN)
            self.assertFalse('flags' in result)
            self.assertFalse('crc32' in result)
            self.assertFalse('actual_crc32' in result)

            with self.assertRaises(HunterResultNotFound):
                result = hunter.find('not_in_environment')

        with self.subTest('Second headerless @ _ENV_BIN_LEN+128'):
            result = hunter.find('', start=_ENV_BIN_LEN + 128)
            self.assertEqual(result['src_addr'], base + _ENV_BIN_LEN + 128)
            self.assertEqual(result['src_off'],  _ENV_BIN_LEN + 128)
            self.assertEqual(result['src_size'], _ENV_BIN_LEN)
            self.assertFalse('flags' in result)
            self.assertFalse('crc32' in result)
            self.assertFalse('actual_crc32' in result)


        with self.subTest('Env with header'):
            expected_off = 2 * _ENV_BIN_LEN + 128 + 64
            result = hunter.find(None, start=expected_off)

            # Account for CRC header
            expected_off += 4

            self.assertFalse('flags' in result)
            self.assertEqual(result['src_addr'], base + expected_off)
            self.assertEqual(result['src_off'],  expected_off)
            self.assertEqual(result['src_size'], self.env_size)

            off = result['src_off']
            size = result['src_size']

            crc = crc32(self.blob[off:off + size])
            self.assertEqual(result['crc'], crc)

        with self.subTest('First redundant env'):
            expected_off += 4092 + 255
            result = hunter.find(None, start=expected_off)

            # Account for CRC + flags
            expected_off += 5

            self.assertEqual(result['src_addr'], base + expected_off)
            self.assertEqual(result['src_off'],  expected_off)
            self.assertEqual(result['flags'], 0x5)

            off = result['src_off']
            size = result['src_size']

            crc = crc32(self.blob[off:off + size])
            self.assertEqual(result['crc'], crc)

        with self.subTest('Second redundant env'):
            expected_off += 4091
            result = hunter.find(None, start=expected_off)

            # Account for CRC + flags
            expected_off += 5

            self.assertEqual(result['src_addr'], base + expected_off)
            self.assertEqual(result['src_off'],  expected_off)
            self.assertEqual(result['flags'], 0x4)

            off = result['src_off']
            size = result['src_size']

            crc = crc32(self.blob[off:off + size])
            self.assertEqual(result['crc'], crc)

    def test_find_iter(self):
        """
        Just check that we catch all 5.
        """
        base = 0x2000
        hunter = EnvironmentHunter(self.blob, base)

        results = []
        for result in hunter.finditer(None):
            results.append(result)

        self.assertEqual(5, len(results))
