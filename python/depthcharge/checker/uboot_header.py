# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

import os
import re
import subprocess
import textwrap

from copy import deepcopy
from tempfile import TemporaryDirectory

from . import ConfigChecker
from .. import log


class UBootHeaderChecker(ConfigChecker):
    """
    Inspect a platform's U-Boot build configuration header.

    This is applicable for older U-Boot version. See :py:class:`UBootConfigChecker`
    when working with version that have been more fully migrated to Kconfig.

    If you find yourself with a version of U-Boot that has some ``CONFIG_*`` items
    defined in Kconfig files, and other in headers -- worry not!

    You should first use a :py:class:`UBootConfigChecker`. Pass the configuration
    dictionary returned by :py:meth:`UBootConfigChecker.load()` to this class's
    constructor via the *config_defs* keyword argument.  These definitions may provide additional
    definitions that will be used when preprocessing the target platform header file.

    From there, you can invoke each checker's :py:meth:`audit()` method and then merge
    their reports. (See :py:meth:`Report.merge()`.)

    The *include_paths* parameter should contain a list of paths to search
    for header files when ``#include`` directives are encountered.

    Should you encounter problematic header files that prevent preprocessing
    from completed, but are not of interest to you, you can specify their
    names in the *dummy_headers* list.  This class will automatically create
    empty files in a temporary directory, placed at higher precedence in
    the include search path. You may supply eithr single file names (``regs.h``)
    or relative paths (``asm/arch/imx-regs.h``) -- whichever is needed to
    fulfil a failing ``#include``. (**Note:** *Paths with ``..`` are not currently supported.*)

    By default, this class will invoke the *cpp* program located in one's ``PATH``.
    If you would like to use a different preprocessor program, you may override this using the *cpp*
    keyword argument. Depthcharge assumes that it will take the same arguments, however.
    """

    _INDENT = 4 * ' '

    def __init__(self,
                 uboot_version: str,
                 include_paths: list,
                 config_defs: dict = None,
                 cpp: str = None,
                 dummy_headers: list = None,
                 enable_builtins=True):

        super().__init__(uboot_version, enable_builtins)

        if isinstance(include_paths, list):
            self._inc = include_paths
        elif isinstance(include_paths, str):
            self._inc = [include_paths]
        else:
            raise TypeError('Expected list or str for `include_paths` argument')

        self._cpp = cpp or 'cpp'

        if isinstance(config_defs, dict):
            self._config = config_defs
        elif config_defs is None:
            self._config = {}
        else:
            raise TypeError('Expected None or dict for `config_defs` argument.')

        if dummy_headers is None:
            self._dummy_headers = []
        elif isinstance(dummy_headers, list):
            self._dummy_headers = dummy_headers
        elif isinstance(dummy_headers, str):
            self._dummy_headers = [dummy_headers]
        else:
            raise TypeError('Expected None or list for `dummy_paths` argument.')

        self._dummy_dir = None

    def _create_dummy_headers(self):
        self._dummy_dir = TemporaryDirectory(prefix='DepthchargeDummyHeaders-')
        for hdr in self._dummy_headers:
            hdr_dir = os.path.dirname(hdr)

            # TODO: Revisit a better way to handle this input
            if hdr_dir and '..' not in hdr_dir:
                path = os.path.join(self._dummy_dir.name, hdr_dir)
                os.makedirs(path, mode=0o700, exist_ok=True)

            with open(os.path.join(self._dummy_dir.name, hdr), 'w'):
                pass

        return len(self._dummy_headers) > 0

    def _remove_dummy_headers(self):
        if self._dummy_dir is not None:
            self._dummy_dir.cleanup()

    def _report_errors(self, stderr, retcode):
        msg = 'Preprocessor ({:s}) encountered errors, shown below.'
        msg += os.linesep + self._INDENT  + 'Checker result may be incomplete.' + 2*os.linesep
        log.error(msg.format(self._cpp) + textwrap.indent(stderr, self._INDENT))

        if '#include <asm/arch' in stderr:
            msg = 'The above looks like an `#include <asm/arch/...>` issue?' + os.linesep
            msg += self._INDENT + "If so, you'll need to either attempt a build or manually create" + os.linesep
            msg += self._INDENT + "a symlink to arch/$(ARCH)/include/asm/arch-$(SOC)." + os.linesep
            msg += os.linesep
            msg += self._INDENT + 'Alternatively, if the file in question is not useful for configuration ' + os.linesep
            msg += self._INDENT + 'auditing you can specify it as a "dummy header." to skip it' + os.linesep
            log.note(msg)

        if retcode != 0:
            raise ValueError('Preprocessor returned status {:d}'.format(retcode))

    def _run_preprocessor(self, filename, cmd: list) -> dict:
        log.note('Running preprocessor to collect macro definitions')
        log.debug('Command: ' + ' '.join(cmd))

        proc = subprocess.run(cmd, capture_output=True, check=False, text=True)
        if proc.stderr:
            self._report_errors(proc.stderr, proc.returncode)

        output = proc.stdout

        pat = r'#define\s+(?P<ident>[A-Za-z0-9_]+)(?P<args>\([A-Za-z0-9_ ,\.]*\))?\s+(?P<value>.*)'
        macro_def = re.compile(pat)

        pat = r'#undef\s+(?P<ident>[A-Za-z0-9_]+)'
        macro_undef = re.compile(pat)

        # TODO: Would be nice if we could collect the *actual* filename/lineno from cpp.
        # We should have some context from the cpp -dD output..
        source = filename + ' (preprocessed), '

        for line in output.splitlines():
            match = macro_def.match(line)
            if match:
                ident = match.group('ident')
                value = match.group('value')

                # Treat `#define CONFIG_THE_THING` (sans value) as "the thing is enabled" --> True
                if not value:
                    value = True

                self._add_config_entry(ident, value, source + ident, warn=False)
                log.debug('Collected #define > ' + ident + ' = ' + str(value))
            else:
                match = macro_undef.match(line)
                if match:
                    # Treat `#undef CONFIG_THE_THING` as "disable the thing" --> False
                    ident = match.group('ident')
                    value = False
                    self._add_config_entry(ident, value, source + ident, warn=False, force=True)
                    log.debug('Collected #undef  > ' + ident + ' = ' + str(value))

        return deepcopy(self._config)

    def load(self, filename: str) -> dict:
        """
        Load and parse the specified U-Boot platform configuration header file and return a dictionary
        in the format defined by :py:meth:`ConfigChecker.load()`.

        Calling :py:meth:`load()` multiple times with different files will aggregate the
        configurations present across all loaded files.
        """

        args = [self._cpp, '-dD', '-undef', '-nostdinc']

        try:
            if self._create_dummy_headers():
                args += ['-I', self._dummy_dir.name]

            for path in self._inc:
                args += ['-I', path]

            # We'll miss definitions in U-Boot sources originating from the Linux
            # kernel without these.
            args += ['-D__KERNEL__', '-D__UBOOT__']

            for key, (value, _) in self._config.items():
                if value is False:
                    # Skip items listed as '# CONFIG_* is not set'
                    continue

                if value is True:
                    args += ['-D', key]
                elif isinstance(value, int):
                    args += ['-D', key + '=' + str(value)]
                else:
                    args += ['-D', key + '=' + '"' + str(value) + '"']

            args.append(filename)

            return self._run_preprocessor(filename, args)
        finally:
            self._remove_dummy_headers()
