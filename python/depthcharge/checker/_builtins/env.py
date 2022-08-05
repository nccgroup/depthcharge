# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Built-in SecurityRisk definitions associated with networking functionality.
"""

from textwrap import dedent

from .. import SecurityImpact

_nowhere_desc = dedent("""
    U-Boot's environment variable data, when saved to non-volatile storage, does not include
    integrity and authenticity metadata sufficient to determine that this data has been maliciously
    modified.

    If an attacker, either physically or through another software vulnerability, is able
    to modify the contents of non-volatile storage then they could inject malicious modifications to
    important U-Boot environment variables such as bootcmd, bootargs, and bootdelay. Unless measures
    have been specifically taken to prevent it, this often implies that an attacker can boot
    arbitrary code using functionality enabled into the U-Boot build.
""")


_nowhere_recc = dedent("""\
    Use CONFIG_ENV_IS_NOWHERE=y without any other CONFIG_ENV_IS_* items enabled.

    If environment data must be written to and retrieved from non-volatile storage, you may need to
    implement custom code for integrity and authenticity verification.
""")

_all_versions = (0.0, 9999.99)

_BUILTIN_DEFS = (

    # TODO: CONFIG_ENV_AES
    # 5eb35220b2cbeac79af8d73c696f5930a755c5bd
    # CVE-2017-3225 CVE-2017-3226
    #('CONFIG_ENV_AES', True, {

    #}),

    ('CONFIG_ENV_IS_IN_EEPROM', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_EEPROM',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in EEPROM is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_FLASH', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_FLASH',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in flash is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_NVRAM', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_NVRAM',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in NVRAM is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_SATA', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_SATA',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in SATA device is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_MMC', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_MMC',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in MMC is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_SPI_FLASH', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_SPI_FLASH',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in SPI flash in is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_ONENAND', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_ONENAND',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored OneNAND in is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_EXT4', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_EXT4',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in EXT4 filesystem is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_FAT', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_FAT',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in FAT filesystem is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_FAT', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_UBI',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in UBI volume is vulnerable to tampering',
        'description': _nowhere_desc,
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),

    ('CONFIG_ENV_IS_IN_REMOTE', True,  {
        'identifier': 'CONFIG_ENV_IS_IN_UBI',
        'impact': SecurityImpact.EXEC,
        'summary': 'Environment stored in remote device may be vulnerable to tampering',
        'description': dedent("""\
            U-Boot's environment variable data, when saved to non-volatile storage, does not include
            integrity and authenticity metadata sufficient to determine that this data has been
            maliciously modified.

            If an attacker, either physically or through another software vulnerability, is able to
            modify the contents of the remote device's non-volatile storage then they could inject malicious
            modifications to important U-Boot environment variables such as bootcmd, bootargs, and
            bootdelay. Bus interposition would also provide a sufficient vantage point to tamper
            with this data while it is transmitted to U-Boot from the remote device.

            Unless measures have been specifically taken to prevent it, this often implies that an
            attacker can boot arbitrary code using functionality enabled into the U-Boot build.
        """),
        'recommendation': _nowhere_recc,
        'affected_versions': _all_versions,
    }),
)
