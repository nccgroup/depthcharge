# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Built-in SecurityRisk definitions associated with code in U-Boot's lib/ source
directory, which generally originates from third-party projects.
"""

from textwrap import dedent

from .. import SecurityImpact


def _random_uuid(value: bool, config: dict):
    return value is True and (
        config.get('CONFIG_RANDOM_UUID', False) or
        config.get('CONFIG_CMD_UUID', False)
    )


_BUILTIN_DEFS = (
    ('CONFIG_ZLIB', True, {
        'identifier': 'CVE-2016-9840',
        'summary': 'Enabled zlib code contains pointer arithmetic that relies upon undefined behavior',
        'impact': SecurityImpact.UNKNOWN,

        'description': dedent("""\
            Pointer arithmetic in zlib code used by U-Boot (`lib/zlib/inftrees.c`) relies upon
            undefined behavior (in the C standard) to operate correctly. An incorrect pointer
            value may be computed if code emitted by the compiler deviates from that which
            was intended by the author.

            Additional information and the upstream change in zlib may be found here:
                <https://github.com/madler/zlib/commit/6a043145ca6e9c55184013841a67b2fef87e44c0>
        """),

        'recommendation': dedent("""\
            Upgrade to U-Boot 2020.10 or backport the fix in commit 499b7493.
        """),

        'affected_versions': ('0.0', '2020.07')
    }),

    ('CONFIG_LIB_UUID', _random_uuid, {
        'identifier': 'CVE-2019-11690',
        'summary': 'Randomized UUID values used in GUID partitions tables are deterministic',
        'impact': SecurityImpact.INFO_LEAK,

        'description': dedent("""\
            Random UUID values used when creating GPT entries are obtained from an unseeded PRNG.
            Therefore, the values used as UUIDs are effectively deterministic.
        """),

        'recommendation': dedent("""\
            Upgrade to U-Boot 2019.07 or backport the fix in commit 4ccf678f.

            If the unpredictability of UUIDs is an important component in fulfilling platform security
            requirements, review the relevant UUID code and rand() implementation (e.g. xorshift) in
            U-Boot and evaluate whether further improvements using a CSPRNG seeded from a TRNG,
            rather than `get_ticks()`.
        """),

        # CVE says "through v2019.04", but it looks like the fix landed in the v2019.07-rc2 window.
        'affected_versions': ('2014.04', '2019.07-rc1')
    }),

    # TODO: CONFIG_LLB
    # CVE-2018-18440 -
    # See: 9cc2323feebdde500f50f7abb855045dbde765cb
    # ('0.0', '2019.01')
)
