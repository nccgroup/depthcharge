# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring

"""
Unit tests for depthcharge.hunter.FDTHunter
"""

import os
import subprocess
import shutil
import tempfile
from unittest import TestCase, skipIf

from depthcharge.hunter import FDTHunter, HunterResultNotFound

from ..test_utils import random_data


# flake8: noqa=W191
_DTS = \
"""
/dts-v1/;

/ {
	#address-cells = <1>;
	#size-cells = <1>;

	bus@ff784000 {
		#address-cells = <1>;
		#size-cells = <1>;
		compatible = "depthcharge-bus", "simple-bus";
		ranges = <0x0 0x10000000 0x10000>;

		node@d00dfeed {
			reg = <0xd00dfeed 1>;
		};
	};

};
"""

_DTC = shutil.which('dtc')

@skipIf(_DTC is None, 'Test requires that "dtc" is installed')
class TestFDTHunter(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dts = _DTS
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as outfile:
            outfile.write(_DTS)
            dts_filename = outfile.name

        args = [_DTC, '-q', '-I', 'dts', '-O', 'dtb', dts_filename]
        sub = subprocess.run(args, check=True, capture_output=True)
        cls.dtb = sub.stdout
        os.remove(dts_filename)

        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as outfile:
            outfile.write(cls.dtb)
            dtb_filename = outfile.name

        args = [_DTC, '-q', '-I', 'dtb', '-O', 'dts', dtb_filename]
        sub = subprocess.run(args, check=True, capture_output=True, text=True)
        cls.dts_expected = sub.stdout
        os.remove(dtb_filename)

    def test_find(self):
        base = 0x8000
        locs = (200, 1724, 3141)

        blob = random_data(4096)
        dtb_len = len(self.dtb)

        for loc in locs:
            blob[loc:loc + dtb_len] = self.dtb

        hunter = FDTHunter(blob, base)

        result = hunter.find(None)
        self.assertTrue(result is not None)
        self.assertEqual(result['src_off'], locs[0])
        self.assertEqual(result['src_addr'], base + locs[0])
        self.assertEqual(result['src_size'], dtb_len)
        self.assertEqual(result['dtb'], self.dtb)
        self.assertEqual(result['dts'], self.dts_expected)

        with self.assertRaises(HunterResultNotFound):
            _ = hunter.find('NotInThisDTS')

    def test_finditer(self):
        base = 0x8000
        locs = (200, 1724, 3141)

        blob = random_data(4096)
        dtb_len = len(self.dtb)

        for loc in locs:
            blob[loc:loc + dtb_len] = self.dtb

        i = 0
        hunter = FDTHunter(blob, base)
        for result in hunter.finditer(None):
            self.assertTrue(result is not None)
            self.assertEqual(result['src_off'], locs[i])
            self.assertEqual(result['src_addr'], base + locs[i])
            self.assertEqual(result['src_size'], dtb_len)
            self.assertEqual(result['dtb'], self.dtb)
            self.assertEqual(result['dts'], self.dts_expected)

            i += 1

        with self.assertRaises(HunterResultNotFound):
            _ = hunter.find('NotInThisDTS')
