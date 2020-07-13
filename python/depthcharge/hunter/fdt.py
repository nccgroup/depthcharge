# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements FDTHunter, which searches for Flattened Device Tree blobs, also commonly referred to as
DTBs (whose corresponding "source" are DTS files).
"""

import os
import re
import shutil
import subprocess
import tempfile

from .. import log
from .hunter import Hunter, HunterResultNotFound


class FDTHunter(Hunter):
    """
    This :py:class:`.Hunter` searches for `Flattened Device Tree <https://www.devicetree.org>`_
    (also see `elinux.org <https://elinux.org/Device_Tree_Reference>`_) instances within a memory or
    flash dump.

    If the Device Tree Compiler (dtc) is installed, results will include both the binary
    representation of the device tree (dtb) as well as a source representation (dts).
    """

    def __init__(self, data: bytes, address: int, start_offset=-1, end_offset=-1, gaps=None, **kwargs):
        super().__init__(data, address, start_offset, end_offset, gaps, **kwargs)

        # Path to DTC binary
        self._dtc = shutil.which('dtc')
        if self._dtc is None:
            msg = 'The "dtc" program was not found. DTS (source) will not be provided in results.'
            log.warning(msg)

        # Regex for matching FDT header (per v17 spec)
        self._regex = re.compile(
            b'(?P<magic>\xd0\x0d\xfe\xed)' +
            b'(?P<totalsize>.{4})' +
            b'(?P<off_dt_struct>.{4})' +
            b'(?P<off_dt_strings>.{4})' +
            b'(?P<off_mem_rsvmap>.{4})' +
            b'(?P<version>.{4})' +
            b'(?P<last_comp_version>.{4})' +
            b'(?P<boot_cpuid_phys>.{4})' +
            b'(?P<size_dt_strings>.{4})' +
            b'(?P<size_dt_struct>.{4})'
        )

    def _device_tree(self, match, offset, end):
        """
        Attempt to sanity check the FDT in order to rule out false positives
        and return the FDT blob.

        We'll let the external dtc program do the actual parsing during dtb->dts
        conversion. Here we only do the simplest of checks...
        """
        log.debug('Inspecting potential DTB @ 0x{:08x}'.format(offset))

        def field(name):
            return int.from_bytes(match.group(name), 'big')

        # Skip past magic
        start = offset
        offset += 4

        totalsize = field('totalsize')
        if totalsize > (end - offset):
            msg = 'Invalid FDT @ 0x{:08x} - totalsize too large (0x{:08x})'
            log.debug(msg.format(start, totalsize))
            return None
        offset += 4

        off_dt_struct = field('off_dt_struct')
        if off_dt_struct > (end - offset):
            msg = 'Invalid FDT @ 0x{:08x} - off_dt_struct too large (0x{:08x})'
            log.debug(msg.format(start, off_dt_struct))
            return None
        offset += 4

        off_dt_strings = field('off_dt_strings')
        if off_dt_strings > (end - offset):
            msg = 'Invalid FDT @ 0x{:08x} - off_dt_strings too large (0x{:08x})'
            log.debug(msg.format(start, off_dt_strings))
            return None
        offset += 4

        off_mem_rsvmap = field('off_mem_rsvmap')
        if off_mem_rsvmap > (end - offset):
            msg = 'Invalid FDT @ 0x{:08x} - off_mem_rsvmap too large (0x{:08x})'
            log.debug(msg.format(start, off_mem_rsvmap))
            return None

        # Skip version, last_comp_version, boot_cpuid_phy
        offset += 16

        size_dt_strings = field('size_dt_strings')
        if (end - off_dt_strings) < size_dt_strings:
            msg = 'Invalid FDT @ 0x{:08x} - size_dt_strings too large (0x{:08x})'
            log.debug(msg.format(start, size_dt_strings))
            return None

        size_dt_struct = field('size_dt_struct')
        if (end - off_dt_struct) < size_dt_struct:
            msg = 'Invalid FDT @ 0x{:08x} - size_dt_struct too large (0x{:08x})'
            log.debug(msg.format(start, size_dt_struct))
            return None

        log.debug('Returning DTB @ 0x{:08x}, size={:d} bytes'.format(start, totalsize))
        return self._data[start:start + totalsize]

    def _create_dts(self, dtb):
        """
        Launch external dtc process to convert a dtb into a dts
        """

        with tempfile.NamedTemporaryFile(delete=False) as outfile:
            dtb_file_name = outfile.name
            outfile.write(dtb)

        args = [self._dtc, '-q', '-I', 'dtb', '-O', 'dts', dtb_file_name]
        result = subprocess.run(args, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            msg = 'DTB -> DTS conversion failed: '
            msg += result.stderr.replace('FATAL ERROR: ', '').rstrip()
            raise ValueError(msg)

        os.remove(dtb_file_name)
        return result.stdout

    def _search_at(self, target, start, end, **kwargs):
        match = True
        while match is not None and start < end:
            match = self._regex.search(self._data[start:end])
            if match:
                span = match.span()
                offset = start + span[0]

                dtb = self._device_tree(match, offset, end)
                if dtb:
                    extra = {}
                    extra['dtb'] = dtb

                    if self._dtc and not kwargs.get('no_dts', False):
                        dts = self._create_dts(dtb)
                        if dts:
                            extra['dts'] = dts

                    ret = (offset, len(dtb), extra)
                    if target is None:
                        return ret

                    if isinstance(target, str) and target in extra.get('dts', ''):
                        return ret

                    if isinstance(target, bytes) and target in extra['dtb']:
                        return ret

                # We had a false positive or an invalid FDT.
                # Skip past its "magic" word so we can continue our search.
                start += offset + 4

        raise HunterResultNotFound()
