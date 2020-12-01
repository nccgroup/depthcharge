# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

import re
from copy import deepcopy

from . import ConfigChecker


class UBootConfigChecker(ConfigChecker):
    """
    Inspect U-Boot build configurations present in .config files produced by more modern,
    Kconfig-driven U-Boot builds. (i.e. those produced from ``make <platform>_defconfig``)
    """

    _CONFIG_VAL = re.compile(r'^(?P<key>CONFIG_[A-Za-z0-9_]+)=(?P<value>.*)$')
    _CONFIG_UNSET = re.compile(r'^#\s?(?P<key>CONFIG_[A-Za-z0-9_]+) is not set$')

    def load(self, filename: str) -> dict:
        """
        Load and parse the specified U-Boot build configuration file and return a dictionary
        in the format defined by :py:meth:`ConfigChecker.load()`.

        The provided file should be a `.config` file produced by running ``make <platform>_defconfig``
        within the U-Boot codebase - not just the platform's *defconfig* file, doesn't include
        all the configuration items inherited by default settings.

        Calling :py:meth:`load()` multiple times will aggregate the configurations present across
        all loaded files. When re-defined configuration items are encountered their values are
        ignored and a warning is printed.
        """

        with open(filename, 'r') as infile:
            data = infile.read()

        lineno = 0
        cfg = self._config

        lines = data.splitlines()
        for line in lines:
            lineno += 1

            m = self._CONFIG_VAL.match(line)
            if m:
                source = filename + ':' + str(lineno)
                key = m.group('key')
                value = m.group('value')
                if value == 'y':
                    value = True

            else:
                m = self._CONFIG_UNSET.match(line)
                if m:
                    source = filename + ':' + str(lineno)
                    key = m.group('key')
                    value = False
                else:
                    continue

            self._add_config_entry(key, value, source)

        return deepcopy(cfg)
