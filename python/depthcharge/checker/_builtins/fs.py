# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Built-in SecurityRisk definitions associated with file system implementations.
"""

from textwrap import dedent

from .. import SecurityImpact


_BUILTIN_DEFS = (

    # The fix is implemented using lmb (CONFIG_LMB=y). Does there exist a valid configuration for
    # which CONFIG_LMB=n and the unsafe behavior could be reached? (i.e. in SPL builds?)
    #
    # TODO: Investigate this further to determine if additional checks are neccessary
    ('CONFIG_LMB', True, {
        'identifier': 'CVE-2018-18440',
        'summary': 'An excessively large binary loaded via from a file system can corrupt program memory',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            Prior to U-Boot 2019.04-rc1, no size validation was performed on images
            retrieved from file systems. Loading an excessively large boot image could
            overwrite program memory belonging to the running U-Boot bootloader.

            In this threat scenario, the concern is that the memory corruption would lead to
            malicious code execution. This vulnerability is envisioned to be abused in situations
            where U-Boot's Verified Boot functionality is in use, such that the ability to
            tamper with an untrusted file system does not already achieve the desired objective.

            More information can be found in this advisory:
                <https://www.openwall.com/lists/oss-security/2018/11/02/2>
        """),

        # Not recommending backporting individual changes at this time, given that
        # there's a bit of a gotcha with respect to ensuring that 9cc2323f is also included
        # when more than one DRAM bank is involved.
        'recommendation': 'Update to U-Boot 2019.04.\n',

        'affected_versions': ('0.0', '2019.01')
    }),

    ('CONFIG_FS_EXT4', True, {
        'identifier': 'CVE-2019-11059',
        'summary': 'A mishandled EXT4 64-bit exception results in a buffer overflow',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            Prior to U-Boot 2019.07-rc1, support for arbitrary-sized block group descriptors
            with 64-bit addressing was not implemented correctly and resulted in out-of-bounds
            memory writes.

            Exploitation, if possible, would require the ability to tamper with
            or otherwise provide a maliciously crafted EXT4 filesystem to U-Boot. (For example,
            an attacker could reflash non-volatile storage, provided physical access.)
        """),

        'recommendation': dedent("""
            Update to U-Boot 2019.07 or backport the fix from commit febbc583.
        """),

        'affected_versions': ('2016.11-rc1', '2019.04')
    }),

    ('CONFIG_DOS_PARTITION', True, {
        'identifier': 'CVE-2019-13103',
        'summary': 'A maliciously crafted EXT4 filesystem can induce unbounded recursion that corrupts stack memory',
        'impact': SecurityImpact.LIMITED_WR_MEM,

        'description': dedent("""\
            Prior to U-Boot 2019.10-rc1, no max recursion depth was enforced in `disk/dos_part.c` when
            iterating over nested DOS partitions. If an attacker (with sufficient access to tamper
            with non-volatile storage or image loading functionality) were able to coerce the bootloader
            into processing a DOS partition table containing nested, self-referential entries the
            resulting unbounded recursion could corrupt stack memory.
        """),

        'recommendation': dedent("""
            Update to U-Boot 2019.10 or backport the fix from commit 232e2f4f.
        """),

        # nvd.nist.gov states "through 2019.07-rc4" but the patch landed after the 2019.07 release.
        # Going with what I see in the upstream git logs here. I imagine the CVE text predates the fix.
        #
        # Additionally, no minimum version specified. Using 0.0 for now in the interest of my time.
        'affected_versions': ('0.0', '2019.07')
    }),

    ('CONFIG_FS_EXT4', True, {
        'identifier': 'CVE-2019-13104',
        'summary': 'Stack memory corruption can be induced by a maliciously crafted EXT4 filesystem',
        'impact': SecurityImpact.LIMITED_WR_MEM,

        'description': dedent("""
            A maliciously crafted EXT4 filesystem can trigger an integer underflow of a
            value that is passed to a `memcpy()` invocation as the length parameter. This results
            in a copy operation for a significantly large amount of data that will likely corrupt
            the entirety of stack memory, if not inducing a crash prior to completing.
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit 878269db.
        """),

        # nvd.nist.gov states "through 2019.07-rc4" but the patch landed after the 2019.07 release.
        # Going with what I see in the upstream git logs here. I imagine the CVE text predates the fix.
        'affected_versions': ('2016.11-rc1', '2019.07')
    }),

    ('CONFIG_FS_EXT4', True, {
        'identifier': 'CVE-2019-13105',
        'summary': 'A double-free can occur when listing files in an EXT4 filesystem',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            The function `ext_cache_read()` does not set a `cache->buf` pointer to `NULL`
            after freeing the corresponding memory. This can lead to a double free scenario, which
            traditionally can be abused by an attacker as an arbitrary memory write primitive,
            possibly leading to code execution.

            Based upon the CVE entry specifying a local attack vector, this is understood
            to be potentially exploitable in situations where an attacker can coerce U-Boot
            into processing a filesystem, via local/physical access.
        """),

        'recommendation': dedent("""
            Update to U-Boot 2019.10 or backport the fix from commit 6e5a79de.
        """),

        # See above version comment
        'affected_versions': ('2019.07-rc1', '2019.07'),
    }),

    ('CONFIG_FS_EXT4', True, {
        'identifier': 'CVE-2019-13106',
        'summary': 'A stack-based buffer overflow can be induced by a maliciously crafted EXT4 filesystem',
        'impact': SecurityImpact.WR_MEM,

        'description': dedent("""\
            In the `ext4fs_read_file()` function, a `memcpy()` operation is performed without
            validating that the length parameter is smaller than the remaining storage in the
            destination buffer. (The check only tests against the total size of the entire buffer

            This stack-based buffer overflow may allow for arbitrary code execution in situations
            where it is plausible for an attacker to stage a maliciously crafted EXT4 file system,
            such as when an attacker has physical access to the non-volatile memory accessed by
            the bootloader.
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2019.10 or backport the fix from commit e205896c.
        """),

        # See above version comment
        'affected_versions': ('2016.09', '2019.07')
    }),

    ('CONFIG_DOS_PARTITION', True, {
        'identifier': 'Commit 54193c5d',
        'summary': 'A stack-based buffer overflow can be induced by a DOS MBR with a large block size.',
        'impact': SecurityImpact.WR_MEM,
        'description': dedent("""\
            A hard-coded MBR block size of 512 results in a stack-based buffer overflow when a DOS
            partition has larger block sizes (e.g. 2 or 4 KiB). Exploitation of this vulnerability
            can result in arbitrary code execution, which is most impactful when secure boot
            functionality otherwise has sought to prevent this.

            This defect was introduced in commit fe8c2806 and fixed in commit 54193c5di. No CVE is
            currently assigned to this vulnerability.

            More information, including exploitation, can be found in the following blog post:
            https://fredericb.info/2022/06/breaking-secure-boot-on-google-nest-hub-2nd-gen-to-run-ubuntu.html
        """),

        'recommendation': 'Update to U-Boot 2011.09 or backport the fix from commit 54193c5d.',

        # Looks like this was introduced prior to the YYYY.MM version scheme.
        'affected_versions': ('0.0', '2011.09'),
    }),


    ('CONFIG_DOS_PARTITION', True, {
        'identifier': 'Commit 7aed3d38',
        'summary': 'A stack-based buffer overflow can be induced by a DOS MBR with a large block size.',
        'impact': SecurityImpact.WR_MEM,
        'description': dedent("""\
            A hard-coded MBR block size of 512 results in a stack-based buffer overflow when a DOS
            partition has larger block sizes (e.g. 2 or 4 KiB). Exploitation of this vulnerability
            can result in arbitrary code execution, which is most impactful when secure boot
            functionality otherwise has sought to prevent this.

            This defect was (re)introduced in commit 8639e34d and fixed in commit 7aed3d38. It is
            essentially the same vulnerability fixed in commit 54193c5d. No CVE is currently
            assigned to this vulnerability.

            More information, including exploitation, can be found in the following blog post:
            https://fredericb.info/2022/06/breaking-secure-boot-on-google-nest-hub-2nd-gen-to-run-ubuntu.html
        """),

        'recommendation': 'Update to U-Boot 2019.10 or backport the fix from commit 7aed3d38.',

        'affected_versions': ('2018.03-rc2', '2019.10'),

    }),

    ('CONFIG_CMD_GPT', True, {
        'identifier': 'CVE-2020-8432',
        'summary': 'Double-free in do_rename_gpt_parts function',
        'impact': SecurityImpact.WR_MEM,
        'description': dedent("""\
            Induced failures in do_rename_gpt_parts() may result in a double-free.  In general,
            double-free vulnerabilities can provide an attackers with an arbitrary write primitive
            that could lead to malicious code execution.
        """),

        'recommendation': 'Update to U-Boot 2020.04 or backport the fix from commit 5749faa3.',

        # Command introduced in commit , issue fixed in 5749faa3
        'affected_versions': ('2013.01-rc2', '2020.04')
    }),
)
