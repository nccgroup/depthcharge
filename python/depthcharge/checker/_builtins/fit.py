# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Built-in SecurityRisk definitions associated with FIT image functionality
"""

from textwrap import dedent

from .. import SecurityImpact


def _enabled_with_legacy_image(value: str, config: dict):
    return value and config.get('CONFIG_LEGACY_IMAGE_FORMAT', False)


def _enabled_without_full_check(value: str, config: dict):
    return value and not config.get('CONFIG_FIT_FULL_CHECK', False)


_BUILTIN_DEFS = (
    ('CONFIG_FIT_SIGNATURE', True, {
        'identifier': 'CVE-2018-3968',
        'impact': SecurityImpact.VERIFICATION_BYPASS,
        'summary':
            'Unsigned "legacy" images can be still executed when FIT image signature validation is enabled',

        'description': dedent("""\
            Prior to U-Boot 2014.07-rc3 there was no build-time configuration option for disabling
            support for unsigned "legacy" images. As a result, enabling FIT image signature
            validation via `CONFIG_FIT_SIGNATURE=y` was not sufficient to ensure that only
            images passing signature validation could be booted.

            Given the ability to stage an unsigned "legacy" image and pass it to `bootm`, an
            attacker can bypass signature validation and execute arbitrary code.

            Refer to the following advisory for more information:
                <https://talosintelligence.com/vulnerability_reports/TALOS-2018-0633>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2014.07 or otherwise backport the changes from commit 21d29f7f.
            Ensure `CONFIG_LEGACY_IMAGE_FORMAT` is disabled when using `CONFIG_FIT_SIGNATURE=y`.
        """),

        'affected_versions': ('2013.07-rc1', '2014.07-rc2')
    }),

    ('CONFIG_FIT_SIGNATURE', True, {
        'identifier': 'CVE-2018-1000205',
        'summary': 'Edge cases in FIT and FDT code could result in a verified boot bypass',
        'impact': SecurityImpact.VERIFICATION_BYPASS,

        'description': dedent("""\
            The following mailing list post proposed three patches to unaccounted for edge cases
            believed to present a risk of verified boot bypasses.  The author notes that the threat
            scenario requires special hardware behavior. Determining the susceptibility of any given
            platform would require more review, as information in the CVE entry is sparse.

            Link:
                <https://lists.denx.de/pipermail/u-boot/2018-June/330898.html>
        """),

        # Before commenting on backporting patches, need to investigate the item noted below.
        # The author's vboot patches landed in 7346c1e1 and 72239fc8.
        #
        # TODO: Track down the FDT change WRT https://lists.denx.de/pipermail/u-boot/2018-June/330601.html
        #
        'recommendation': 'Update to U-Boot 2018.09.\n',

        'affected_versions': ('2013.07-rc1', '2018.09')
    }),

    # Vestigial reference design configuration that results in behavior similar to CVE-2018-3968
    ('CONFIG_FIT_SIGNATURE', _enabled_with_legacy_image, {
        'identifier': 'BOTH_LEGACY_AND_FIT_SIG_ENABLED',
        'impact': SecurityImpact.VERIFICATION_BYPASS,
        'summary':
            'Unsigned "legacy" images can be still executed when FIT image signature validation is enabled',

        'description': dedent("""\
            In order for U-Boot's FIT signature enforcement to be effective, support for the unsigned
            "legacy" image format must be disabled. Otherwise, an attacker can bypass signature validation
            by providing and booting a legacy image.

            In U-Boot 2014.07 and later, enabling `CONFIG_FIT_SIGNATURE=y` implies that
            `CONFIG_LEGACY_IMAGE_FORMAT` should be disabled by default. However, if `CONFIG_LEGACY_IMAGE_FORMAT`
            is explicitly enabled in the platform configuration (as is the case in many reference
            design configuration), legacy image support will still be included. This results in the
            configuration described above, which may undermine the intended image authenticity
            enforcement goals.
        """),

        'recommendation': dedent("""\
            Disable the legacy image format via `CONFIG_LEGACY_IMAGE_FORMAT` in situations where a
            platform shall only boot signed, verified images.
        """),
    }),

    # Fixes for this appeared to land in the merge commit @ e0718b3ab754860bd47677e6b4fc5b70da42c4ab,
    # with fixes in 390b26dc270aa3159df0c31775f91cd374a3dd3a..0e29648f8e7e0aa60c0f7efe9d2efed98f8c0c6e
    ('CONFIG_FIT_SIGNATURE', True, {
        'identifier': 'CVE-2020-10648',
        'impact': SecurityImpact.VERIFICATION_BYPASS,
        'summary':
            'FIT image signature validation can be bypassed by tampering with an authentic image',

        'description': dedent("""\
            Prior to version 2020.04(-rc5), U-Boot did not verify that the contents of a FIT
            image configuration's *hashed-nodes* was actually associated with the images used when
            booting a specific configuration.

            As a result, an attacker could append additional configurations that included their own
            images to execute, but specify that the signatures be computed over legitimate images
            contained in a different, authentic configuration.

            In situations where an attacker can tamper with a FIT image, stage their own payloads,
            and control which configuration is booted, this can allow signature validation to be
            bypassed and arbitrary attacker-provided code to be executed.

            Refer to the following advisory for additional information:
                <https://labs.f-secure.com/advisories/das-u-boot-verified-boot-bypass>
        """),

        'recommendation': dedent("""\
            Update to U-Boot 2020.04, or otherwise backport fixes merged in commit e0718b3a.

            Per the F-Secure advisory, one possible mitigation is to explicitly specify the
            configuration in the FIT image to boot: `bootm ${loadaddr}#conf@1 - ${fdtaddr}`

            This mitigation, of course, assumes that an attacker is not able to otherwise tamper
            with the bootloader environment (e.g. `bootcmd`).

            Links:
                <https://source.denx.de/u-boot/u-boot/-/commit/e0718b3ab754860bd47677e6b4fc5b70da42c4ab>
                <https://lists.denx.de/pipermail/u-boot/2020-March/403409.html>
                <https://labs.f-secure.com/advisories/das-u-boot-verified-boot-bypass>

        """),

        'affected_versions': ('2013.07-rc1', '2020.04-rc5'),
    }),

    ('CONFIG_FIT_SIGNATURE', True, {
        'identifier': 'CVE-2021-27138',
        'impact': SecurityImpact.VERIFICATION_BYPASS,
        'summary': 'FIT signature bypass via unit addresses',

        'description': dedent("""\
                As of 2017, U-Boot no longer uses unit addresses in FIT images. However, because
                libfdt can match nodes ignoring any unit addressees, it is possible that signature
                verification checks the wrong node if one with the same name but different unit
                address is inserted.
        """),

        'recommendation': 'Update to U-Boot 2021.04.',

        # FIT images introduced in 782cfbb2
        'affected_versions': ('2013.07-rc1', '2021.04')
    }),

    ('CONFIG_FIT_SIGNATURE', True, {
        'identifier': 'CVE-2021-27097',
        'impact': SecurityImpact.VERIFICATION_BYPASS,
        'summary': 'FIT signature bypass via multiple root nodes',

        'description': dedent("""
            A malformed FIT image, such as one containing multiple root nodes, could cause the
            wrong parent node to be processed during validation.
        """),

        'recommendation': 'Update to U-Boot 2021.04 and ensure CONFIG_FIT_FULL_CHECK=y.',

        # FIT images introduced in 782cfbb2
        'affected_versions': ('2013.07-rc1', '2021.04')
    }),

    ('CONFIG_FIT_SIGNATURE', _enabled_without_full_check, {
        'identifier': 'CONFIG_FIT_FULL_CHECK',
        'impact': SecurityImpact.VERIFICATION_BYPASS,
        'summary': 'Full FIT validation checks are not enabled',
        'description': dedent("""\
            CONFIG_FIT_SIGNATURE=y is intended to imply CONFIG_FIT_FULL_CHECK=y, but
            CONFIG_FIT_FULL_CHECK does not appear to be enabled in the analyzed config file. The
            "full check" is necessary to avoid security risks (e.g. verification bypasses)
            resulting from malformed FIT constructs that can otherwise be rejected.
        """),

        'recommendation': 'Ensure CONFIG_FIT_FULL_CHECK=y.',

        # This needs to be enabled in 2021.04-rc2 onward
        'affected_versions': ('2021.04-rc2', '9999.99')
    })
)
