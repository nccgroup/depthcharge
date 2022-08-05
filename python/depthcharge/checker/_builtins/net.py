# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Built-in SecurityRisk definitions associated with networking functionality.
"""

from textwrap import dedent

from .. import SecurityImpact

_BUILTIN_DEFS = (

    ('CONFIG_NETCONSOLE', True, {
        'identifier': 'CONFIG_NETCONSOLE',
        'summary': 'NetConsole functionality provides unauthenticated access to U-Boot over network',
        'impact': SecurityImpact.ATTACK_SURFACE |  SecurityImpact.INFO_LEAK | SecurityImpact.EXEC,

        'description': dedent("""
            U-Boot's NetConsole functionality allows the interactive U-Boot command line to be
            presented via a network interface, rather than a serial port (i.e. UART) interface.
            This UDP-based functionality is designed to operate in conjunction with netcat
            on the corresponding host. The corresponding traffic is unauthenticated and plaintext.

            Thus, while a helpful development tools, this functionality does not appear to be
            designed nor intended for use a production settings. Doing so greatly exposes the attack
            surface of the relevant platform and could allow a network-resident attacker to execute
            console commands supported in the U-Boot environment.

            More information about NetConsole functionality can be found in the upstream documentation:
                <https://source.denx.de/u-boot/u-boot/-/blob/master/doc/README.NetConsole>
        """),

        'recommendation': dedent("""
            Disable NetConsole functionality in production/release firmware builds
            via `CONFIG_NETCONSOLE`.

            In general, disable any networking functionality that is not required to fulfil
            functional requirements. For any networking functionality that is necessary and
            relied upon, consider reviewing it further to determine if it satisfies the platform's
            security requirements for confidentiality, integrity, authenticity, and availability.
        """)
    }),

    ('CONFIG_CMD_TFTPBOOT', True, {
        'identifier': 'CVE-2018-18439',
        'summary': 'An excessively large binary loaded via tftpboot can corrupt program memory',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            Prior to U-Boot 2019.04-rc1, no size validation was performed on images
            retrieved over TFTP. Use of this functionality in the presence of a network-resident
            attacker could allow the attacker to supply a maliciously crafted image that is large
            enough to overwrite memory containing the running (post-relocation) U-Boot executable.

            In this threat scenario, the concern is that the memory corruption would lead to
            malicious code execution. Given that TFTP is an unauthenticated file transfer
            mechanism that could otherwise be attacked, this vulnerability is envisioned to be
            abused in situations where U-Boot's Verified Boot functionality is in use.

            More information can be found in this advisory:
                <https://www.openwall.com/lists/oss-security/2018/11/02/2>
        """),

        # Not recommending backporting individual changes at this time, given that
        # there's a bit of a gotcha with respect to ensuring that 9cc2323f is also included
        # when more than one DRAM bank is involved.
        'recommendation': 'Update to U-Boot 2019.04.\n',

        'affected_versions': ('0.0', '2019.01')
    }),

    ('CONFIG_NETCONSOLE', True, {
        'identifier': 'CVE-2019-14192',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption in NetConsole functionality can be triggered via maliciously crafted UDP packets',
        'description': dedent("""\
            A length argument passed to `nc_input_packet()` in `net/net.c` is obtained
            directly from a UDP packet, without first performing any validations.
            This can lead to an out-of-bounds memory write when the tainted length
            parameter is subsequently used in a `memcpy()` operation.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit fe72880.
            Otherwise, disable NetConsole and any other unnecessary networking functionality.
        """),

        # None listed in advisory.
        # TODO: Go spelunking in git caverns to find actual minimum.
        'affected_versions': ('0.0', '2019.07')
    }),

    # FIXME: It is PAINFUL to me that there's so much duplication here.
    #        The vast majority of all of these NFS/UDP handler CVEs are the
    #        same root cause/pattern, with fixes all landing in the next
    #        release. I see no real value in having this split into multiple
    #        identifiers, and am only doing it to stay consistent with the
    #        excessive number of CVEs...
    #
    #        Maybe bundle them up into a single meta-identifier for less noise?
    #        Need to get some independent opinions on whether an identifier
    #        like CVE-2019-14193..14204 makes sense to folks.

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14193',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption can be triggered via maliciously crafted NFS messages',
        'description': dedent("""
            A length argument passed to `nfs_readlink_reply()` in `net/nfs.c`
            is obtained from a UDP packet field when `udp_packet_handler()` is
            invoked in `net/net.c`, which does not perform length validation.
            This leads to an out-of-bounds memory write, triggerable by a
            network-resident attacker, when the tainted length parameter is
            subsequently used in a `memcpy()` operation.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit fe72880.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14194',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            In the `nfs_read_reply()` function found in `net/nfs.c`, a path
            length is obtained from a network packet and later used as
            the length parameter in a `memcpy()` invocation performed
            by the `store_block()` function, without sufficient validation. This
            results in an out-of-bounds memory write that is triggerable by a
            network-resident attacker.

            CVE-2019-14194 applies to the NFSv2 case, while CVE-2019-14198 applies
            to the NFSv3 case.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit aa207cf3a.
            Otherwise, disable NFS support and any networking functionality that is not required.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14195',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            In the `nfs_readlink_reply()` function found in `net/nfs.c`, a path
            length is obtained directly from a network packet and used as
            the length parameter in a `memcpy()` invocation, without validation.
            This leads to an out-of-bounds memory write that is triggerable by a
            network-resident attacker,

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit cf3a4f1e.
            Otherwise, disable NFS support and any networking functionality that is not required.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14196',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            Insufficient path length validation is performed in `net/nfs.c` -
            `nfs_lookup_reply()` - prior to using `memcpy()` to copying data to
            into a global `filefh` buffer, using a length obtained from a
            received packet. This allows a network-resident attacker to corrupt
            memory.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 5d14ee4e.
            Otherwise, disable NFS support and any networking functionality that is not required.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14197',
        'impact': SecurityImpact.INFO_LEAK,
        'summary': 'An out-of-bounds memory read can be induced via maliciously crafted NFS messages',

        'description': dedent("""\
            In `nfs_read_reply()` a `memcpy()` of data into a response buffer
            is performed without first validating that a source buffer contains
            enough data. This could allow a network-resident attacker to read
            outside the bounds of the source packet buffer. The location and
            potential contents of the "leaked" buffer depend upon the network
            driver in use.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 741a8a08.
            Otherwise, disable NFS support and any networking functionality that is not required.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14198',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            In the `nfs_read_reply()` function found in `net/nfs.c`, a path
            length is obtained from a network packet and later used as
            the length parameter in a `memcpy()` invocation performed
            by the `store_block()` function, without sufficient validation. This
            results in an out-of-bounds memory write that is triggerable by a
            network-resident attacker.

            CVE-2019-14194 applies to the NFSv2 case, while CVE-2019-14198 applies
            to the NFSv3 case.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit aa207cf3a.
            Otherwise, disable NFS support and any networking functionality that is not required.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_NET', True, {
        'identifier': 'CVE-2019-14199',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Memory corruption can be triggered via maliciously crafted UDP message',
        'description': dedent("""
            In `net/net.c`, the length argument passed to `udp_packet_handler` implementations
            may underflow, resulting in a large unsigned integer value. This can lead to
            memory corruption when the handler later uses this length to copy data. A
            network-resident attacker can induce this behavior with a maliciously
            crafted UDP packet.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit fe728806.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14200',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Stack memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            An unvalidated packet length (see CVE-2019-14199) is used in the NFS handler
            `rpc_lookup_reply()` when copying data. This can allow a network-resident
            attacker to corrupt stack memory via maliciously crafted UDP messages.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 741a8a08.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14201',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Stack memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            An unvalidated packet length (see CVE-2019-14199) is used in the NFS handler
            `nfs_lookup_reply()` when copying data. This can allow a network-resident
            attacker to corrupt stack memory via maliciously crafted UDP messages.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 741a8a08.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14202',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Stack memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            An unvalidated packet length (see CVE-2019-14199) is used in the NFS handler
            `nfs_readlink_reply()` when copying data. This can allow a network-resident
            attacker to corrupt stack memory via maliciously crafted UDP messages.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 741a8a08.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14203',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Stack memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            An unvalidated packet length (see CVE-2019-14199) is used in the NFS handler
            `nfs_mount_reply()` when copying data. This can allow a network-resident
            attacker to corrupt stack memory via maliciously crafted UDP messages.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 741a8a08.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_CMD_NFS', True, {
        'identifier': 'CVE-2019-14204',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Stack memory corruption can be triggered via maliciously crafted NFS messages',

        'description': dedent("""\
            An unvalidated packet length (see CVE-2019-14199) is used in the NFS handler
            `nfs_unmountall_reply()` when copying data. This can allow a network-resident
            attacker to corrupt stack memory via maliciously crafted UDP messages.

            This and related advisories are discussed in the following blog post:
                <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 741a8a08.
            Otherwise, disable NFS support and any other unnecessary networking functionality.
        """),

        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_IP_DEFRAG', True, {
        'identifier': 'CVE-2022-30790',
        'impact': SecurityImpact.WR_MEM,
        'summary': 'Hole descriptor overwrite in packet defragmentation leads to arbitrary out of bounds write primitive',
        'description': dedent("""\
            A malformed UDP packet can exploit a logical defect in __net_defragment() to perform
            an arbitrary write to an attacker-controlled offset from the affected hole metadata location.
            This issue would only be exploitable by a network-adjacent attacker, as the malformed
            packet would likely be dropped during routing.

            More information can be found in the following NCC Group advisory:
            https://research.nccgroup.com/2022/06/03/technical-advisory-multiple-vulnerabilities-in-u-boot-cve-2022-30790-cve-2022-30552

        """),

        'recommendation': 'Update to U-Boot 2022.07 or backport the fix from commit b85d130e.',

        'affected_versions': ('2009.11-rc1', '2022.07')
    }),

    ('CONFIG_IP_DEFRAG', True, {
        'identifier': 'CVE-2022-30552',
        'impact': SecurityImpact.DOS,
        'summary': 'Large buffer overflow leads to DoS in U-Boot IP Packet Defragmentation Code',

        'description': dedent("""\
            A malformed UDP packet can a length calculation to underflow, resulting in a memcpy()
            being performed with an extremely large value. The duration of this operation, combined
            with the substantial memory corruption, result in a denial of service (DoS). This issue
            would only be exploitable by a network-adjacent attacker, as the malformed packet would
            likely be dropped during routing.

            More information can be found in the following NCC Group advisory:
            https://research.nccgroup.com/2022/06/03/technical-advisory-multiple-vulnerabilities-in-u-boot-cve-2022-30790-cve-2022-30552

        """),

        'recommendation': 'Update to U-Boot 2022.07 or backport the fix from commit b85d130e.',

        'affected_versions': ('2009.11-rc1', '2022.07')
    }),
)
