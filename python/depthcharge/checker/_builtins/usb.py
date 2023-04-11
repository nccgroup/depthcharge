
# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Built-in SecurityRisk definitions associated with USB functionality.
"""

from textwrap import dedent

from .. import SecurityImpact

_BUILTIN_DEFS = (
    ('CONFIG_DFU_OVER_USB', True, {
        'identifier': 'CVE-2022-2347',
        'impact': SecurityImpact.WR_MEM | SecurityImpact.RD_MEM,
        'summary': 'Unchecked download size and direction in USB DFU',

        'description': dedent("""\
            The USB DFU download implementation does not bound the length field
            in setup packets, nor does it verify the transfer direction of the
            command. An attacker can craft a setup packet with a wLength
            greater than 4096 bytes and corrupt memory beyond a heap-allocated
            request buffer. For a device-to-host transfer, an attacker may be
            able to read data beyond the heap-allocated buffer.

            For more information refer to the advisory located at:

            https://research.nccgroup.com/2023/01/20/technical-advisory-u-boot-unchecked-download-size-and-direction-in-usb-dfu-cve-2022-2347/
        """),

        # There was an unsuccessful fix that broke DFU. In light of that,
        # we'll just recommend a version upgrade rather than attempt to
        # reference which patches to backport. Here, I'm actually
        # considering the issue to be "fixed" as of commit
        # 14dc0ab138988a8e45ffa086444ec8db48b3f103.
        'recommendation': dedent("""\
            Upgrade to U-Boot 2023.01 or later.
        """),

        'affected_versions': ('2012.10-rc1', '2023.01-rc4'),
    }),

    ('CONFIG_SPL_DFU', True, {
        'identifier': 'CVE-2022-2347',
        'impact': SecurityImpact.WR_MEM | SecurityImpact.RD_MEM,
        'summary': 'Unchecked download size and direction in USB DFU',

        'description': dedent("""\
            The USB DFU download implementation does not bound the length field
            in setup packets, nor does it verify the transfer direction of the
            command. An attacker can craft a setup packet with a wLength
            greater than 4096 bytes and corrupt memory beyond a heap-allocated
            request buffer. For a device-to-host transfer, an attacker may be
            able to read data beyond the heap-allocated buffer.

            For more information refer to the advisory located at:

            https://research.nccgroup.com/2023/01/20/technical-advisory-u-boot-unchecked-download-size-and-direction-in-usb-dfu-cve-2022-2347/
        """),

        # There was an unsuccessful fix that broke DFU. In light of that,
        # we'll just recommend a version upgrade rather than attempt to
        # reference which patches to backport. Here, I'm actually
        # considering the issue to be "fixed" as of commit
        # 14dc0ab138988a8e45ffa086444ec8db48b3f103.
        'recommendation': dedent("""\
            Upgrade to U-Boot 2023.01 or later.
        """),

        'affected_versions': ('2012.10-rc1', '2023.01-rc4'),
    }),
)
