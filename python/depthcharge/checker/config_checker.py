# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Base class for U-Boot configuration checker implementations.
Do not instantiate this directly. Instead, instantiate one of the subclasses:

* :py:class:`UBootConfigChecker` - Checks .config files for newer U-Boot versions using Kconfg
* :py:class:`UBootHeaderChecker` - Check platform configuration header files from older U-Boot version

The following summarizes how API users interact with the above implementations.

1. Instantiate subclass constructor.
2. (Optional) Invoke :py:meth:`register_handler()` to extend checking functionality.
3. Load and parse artifacts to inspect via :py:meth:`load()`, receive configuration dictionary.
4. (Optional) Register handlers that require knowledge of configuration dictionary.
5. Invoke :py:meth:`audit()` and receive a :py:class:`Report` instance
   containing any identified security risks.
"""

import os
import re

from copy import deepcopy

from .report import Report
from .security_risk import SecurityRisk
from ._builtins import _BUILTIN_DEFS

from .. import log
from ..uboot import UBootVersion


class ConfigChecker:
    """
    Create a new configuration checker instance.

    The *uboot_version* parameter should list the U-Boot version being inspected. This will
    be used to inform version-specific checks, such as whether a particular feature has
    CVEs associated with it.

    Examples of acceptable version strings:

    * ``2020.10`` *(A release version)*
    * ``2021.01-rc1``  *(A release candidate)*
    * ``v2020.10`` *(The `v` prefix is ignored)*
    * ``1.3.0`` *(U-Boot version prior to use of `YYYY.MM[-rcN]` convention)*

    With *enable_builtins* set to its default value of ``True``, the configuration handlers
    built into Depthcharge will be used.

    Set this to ``False`` if you want the configuration checker to only report risks identified
    by handlers registered via :py:meth:`register_handler()`.
    """

    _BUILTINS = ()  # Subclasses should define this

    _INDENT = 4 * ' '

    def __init__(self, uboot_version: str, enable_builtins=True):
        self._handlers = {}
        self._config = {}
        self._version = UBootVersion(uboot_version)

        if enable_builtins:
            for (key, match, risk) in _BUILTIN_DEFS:
                risk = SecurityRisk.from_dict(risk)
                self.register_handler(key, match, risk, self._config)

                # A huge swath of configuration options have an SPL variant.
                #
                # Rather than have to account for this in all the builtin definitions,
                # register an additional handler that fires on the SPL variant.
                if 'CONFIG_SPL_' not in key and key.startswith('CONFIG_'):
                    spl_key = key.replace('CONFIG_', 'CONFIG_SPL_')
                    self.register_handler(spl_key, match, risk, self._config)

    def _add_config_entry(self, key: str, value: str, source: str, warn=True, force=False):
        """
        Method intended for use in :py:class:`ConfigChecker` subclasses only.

        Add a configuration key-value pair to `self._config` if *key* is not present in the
        dictionary or if `self._config[key] is None`.

        Otherwise, if *warn* is `True`, this prints a warning about the ignored redefinition, noting
        the original location that provided the pre-existing definition.
        """
        if key not in self._config or force:
            self._config[key] = (value, source)
        elif warn:
            other = self._config[key][1]
            msg = source + ' - ' + key + ' redefined.' + os.linesep
            msg += self._INDENT + 'Keeping definition from: ' + other
            log.warning(msg)

    def register_handler(self, config_key: str, match, security_risk, user_data=None):
        """
        This method allows :py:class:`UBootConfigChecker` to be extended in order to
        report additional configuration-related security risks, beyond those built in to
        Depthcharge. For instance, one could leverage this to maintain their own out-of-tree
        collections of :py:class:`SecurityRisk` definitions and corresponding handlers specific to
        certain silicon or product vendors' U-Boot forks.

        Given a configuration item named ``config_key`` (e.g. ``'CONFIG_SOME_FEATURE'``),
        the ``match`` parameter shall determine whether the specified ``security_risk``
        -- an instance of the :py:class:`SecurityRisk` class -- shall be reported.

        The ``match`` parameter may be one of the following:

        * A boolean (``True`` or ``False``) value. A value of ``True`` corresponds to
          a configuration value being enabled and ``False`` if it is disabled. This
          should only be used for options that have a boolean state.

        * A string that is compared with the configuration value in question.
          The comparison is case-sensitive.

        * A compiled regular expression. This can be used to match a value whose format is
          known in advance, but not easily matched with a string literal.

        * A callable function or method that takes two parameters: the configuration value and
          the ``user_data`` parameter supplied to this method.  The registered handler must return
          ``True`` if the ``security_risk`` should be reported and ``False`` otherwise. This
          provides the most flexibility, with a bit more complexity.

        For :py:class:`SecurityRisk` objects that contain affected version ranges, the
        provided match criteria will only be evaluated if the U-Boot version provided to
        the :py:class:`ConfigChecker` constructor falls within the relevant range.

        Handlers may be registered either before or after a call to :py:meth:`load()`. The
        latter allows allows function-based handlers to have access to configuration information
        (by way of ``user_data``) collected when the checker parses the file.

        More than one handler can be registered for a given configuration item. All of the
        handlers will be executed, allowing a single configuration item to have multiple
        risks associated with it.
        """

        if not isinstance(security_risk, SecurityRisk):
            raise TypeError('Invalid type for security_risk: ' + type(security_risk).__name__)

        if isinstance(match, (bool, str, re.Pattern)) or callable(match):
            pass
        else:
            raise TypeError('match argument is not a supported type.')

        entry = (match, security_risk, user_data)
        if config_key in self._handlers:
            self._handlers[config_key].append(entry)
        else:
            self._handlers[config_key] = [entry]

    def load(self, filename: str) -> dict:  # pylint: disable=no-self-use,unused-argument
        """
        Subclasses implement this function to load the relevant
        file, parse it, and return a dictionary describing the U-Boot configuration settings.

        The keys in this dictionary are the `CONFIG_*` items ingested from the loaded file.
        The value associated with each key is a tuple: ``(cfg_val, source)``.

        The *cfg_val* is ``True`` or ``False`` for boolean configuration items. Otherwise,
        it is a verbatim string from the source file, containing any quotation marks.

        The *source* item is a string describing where *cfg_val* was obtained from
        (e.g. line number).

        """
        return NotImplementedError('Subclass does not provide load() implementation')

    def audit(self):
        """
        Audit the loaded file(s) and return a :py:class:`Report` instance containing
        any identified potential security risks.
        """
        report = Report()

        for key, (value, source) in self._config.items():
            try:
                report_risk = False

                handlers = self._handlers[key]
                for (match, risk, user_data) in handlers:

                    log.debug('Checking key=' + key + ', risk=' + risk.identifier)

                    if not risk.applicable_to_version(self._version):
                        log.debug(risk.identifier + ' is not not applicable to this version')
                        continue

                    if isinstance(match, bool):
                        report_risk = match == bool(value)
                    elif isinstance(match, str):
                        report_risk = (match == value)
                    elif isinstance(match, re.Pattern):
                        report_risk = match.match(value) is not None
                    elif callable(match):
                        report_risk = match(value, user_data)
                    else:
                        err = "Invalid 'match' type encountered in handler: "
                        raise TypeError(err + type(match).__name__)

                    if report_risk:
                        # Return a copy that specifies the source of the risk item
                        finding = deepcopy(risk)
                        finding.source = source
                        report.add(finding)

            except KeyError:
                pass

        return report
