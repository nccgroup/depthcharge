# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements CommandTableHunter
"""

import re
from os import linesep

from .hunter import Hunter, HunterResultNotFound
from .string import StringHunter

from .. import log
from ..arch import Architecture


class CommandTableHunter(Hunter):
    """
    The CommandTableHunter searches a U-Boot memory dump for instances of `linker lists
    <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/doc/README.commands#L118>`_
    containing the `cmd_tbl_s structures
    <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/include/command.h#L30>`_
    that define console commands. Within the U-Boot source code, console commands are declared using
    `U_BOOT_CMD <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/include/command.h#L357>`_
    and related preprocessor macros. (More background information can be found in U-Boot's
    `README.commands <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/doc/README.commands>`_.)

    **Constructor**

    The :py:class:`CommandTableHunter` constructor requires that an `arch=` keyword argument be
    provided. This argument may be either a string or a value returned by
    :py:meth:`Architecture.get() <depthcharge.Architecture.get>`:

    .. code:: python

        my_hunter = CommandTableHunter(mem_dump, 0x4FF4_F000, arch='arm')

    The *address* parameter should generally refer the corresponding data's
    `post-relocation address <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/common/board_f.c#L352>`_.
    This address information is used to determine whether a potential ``cmd_tbl_s`` structure
    contains valid information. For example, ``char *`` pointers are "dereferenced" (within the
    confines of the provided image) to confirm that they lead to NULL-terminated ASCII strings.

    If the data address is not known, pass `check_ptrs=False` to :py:meth:`find()` and
    :py:meth:`finditer()`. Be aware that this will very likely result in a (potentially large)
    number of false postives.

    **Motivation**

    The presence of these command tables can serve as an indicator that `CONFIG_CMDLINE
    <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/cmd/Kconfig#L3?>`_
    is enabled. This evidence can be used to justify further analyses focusing of how a console can
    be accessed, if it is not otherwise obviously exposed or protected with standard functionality.
    For example, does vendor-specific code hide the U-Boot console unless a particular GPIO pin is
    asserted?  Is a custom functionality akin to `CONFIG_AUTOBOOT_STOP_STR and friends
    <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/cmd/Kconfig#L127>`_
    used to gate access to the console?

    The presence of **multiple unique command tables** within a U-Boot memory can also be quite
    interesting! This can be indicative of a situation in which different commands are exposed based
    upon different authorization levels (implemented by vendor-specific code). An example of this can be found in
    `examples/symfonisk_unlock_bypass.py
    <https://github.com/nccgroup/depthcharge/blob/main/python/examples/symfonisk_unlock_bypass.py#L61>`_,
    where pointers to an unauthenticated "insecure" command table are redirected to a
    post-authentication "secure" command table.

    Once the locations and layout of command tables in memory are known, they can be patched at
    runtime to insert alternative functionality (provided that a
    :py:class:`~depthcharge.memory.MemoryWriter` is available). From there, one can instrument
    the operating environment as desired to further explore a SoC, its RAM (from a prior operating state),
    storage media, and peripherals.

    """

    _target_desc = 'command table'

    def __init__(self, data: bytes, address: int, start_offset=-1, end_offset=-1, gaps=None, **kwargs):
        args = (data, address, start_offset, end_offset, gaps)
        super().__init__(*args, **kwargs)

        arch = kwargs.get('arch', None)
        if isinstance(arch, Architecture):
            self._arch = arch
        elif isinstance(arch, str):
            self._arch = Architecture.get(arch)
        else:
            err = '{:s} requires an "arch" keyword specifying the target architecture'
            raise ValueError(err.format(self.__class__.__name__))

        # Regular expression used to match command names.
        # Typically there are purely lowercase alpha, but some exceptions exist:
        #   - '?' as a 'help' alias
        #   - crc32
        #   - Use of underscore in product-specific commands has been observers
        self._cmd_regex = re.compile(kwargs.get('cmd_regex', r'^([a-z0-9_-]{2,}|\?)$'))

        # Known/common false positives
        self._cmd_fp_regex = re.compile('unknown')

        # We shouldn't be seeing format strings in help/usage text
        self._text_fp_regex = re.compile(r'\%[0-9]*[a-z]')

        # Helper for locating strings
        self._strhunt = StringHunter(*args, **kwargs)

    # Does this address fall within our data, or is NULL?
    # Used to infer that a value is a pointer.
    #
    # TODO: If we later pull in capstone as a dependency for other stuff, add a fn
    #       pointer check that confirms we can decode the first instruction.
    def _is_valid_ptr(self, addr, enable_check=True, allow_null=True):
        if not enable_check:
            return True  # Assume valid

        if addr == 0 and allow_null:
            return True

        if addr < self._address:
            return False

        offset = addr - self._address
        return self._start_offset <= offset <= self._end_offset

    def _cmd_tbl_s(self, offset, end, check_ptrs, longhelp, autocomplete):
        """
        Return true if the data at the specified offset could possibly
        be a U-Boot struct cmd_tlb_s:
                {
                    char *name
                    int  maxargs;
                    int (*cmd_rep)(struct cmd_tbl_s *, ...);
                    int (*cmd)(struct cmd_tbl_s *, ...);
                    char *usage;
            #ifdef CONFIG_SYS_LONGHELP
                    char *help;
            #endif
            #ifdef CONFIG_AUTOCOMPLETE
                    int (*complete)(int argc, ...);
            #endif
                }
        """
        arch = self._arch
        addr = self._address + offset

        if not arch.is_word_aligned(addr):
            return None

        ret = {}
        ret['address'] = addr

        try:
            data = self._data[offset:end]
            size = arch.word_size * 5

            name_ptr, data = arch.ptr_value_adv(data)
            name = self._strhunt.string_at(name_ptr)

            # Command name looks bogus             OR       it's a known false positive
            if self._cmd_regex.match(name) is None or self._cmd_fp_regex.match(name) is not None:
                return None
            ret['name'] = name

            ret['maxargs'], data = arch.to_int_adv(data)

            # A 2018 U-Boot commit (80a48dd47e3bf3ede676fae5a630cb6c80de3e69)
            # changed the ->repeatable flag to a function ptr. This access
            # assumes sizeof(ptr) == sizeof(int). However, we don't attempt to
            # dereference it here.
            #
            # TODO: Use _is_valid_ptr and set enable_check per U-Boot version?
            #       This would require users to pass it manually or point us
            #       to their config file containing whatever we've read.
            ret['cmd_rep'], data = arch.ptr_value_adv(data)

            fn_cmd, data = arch.ptr_value_adv(data)
            if not self._is_valid_ptr(fn_cmd, check_ptrs, allow_null=False):
                return None
            ret['cmd'] = fn_cmd

            usage_ptr, data = arch.ptr_value_adv(data)
            if usage_ptr != 0:
                usage = self._strhunt.string_at(usage_ptr, allow_empty=True)

                # Rule out some common false positives
                if self._text_fp_regex.search(usage) is not None:
                    return None

                # Subcommands typically have usage -> "\0"
                ret['subcmd'] = usage == ''
            else:
                # Commands like the mach-imx's "bmode" command don't even set this to
                # an empty string. >:(
                usage = ''
                ret['subcmd'] = False

            ret['usage'] = usage

            if longhelp:
                help_ptr, data = arch.ptr_value_adv(data)
                if help_ptr != 0:
                    # Some commands leave their help text blank, such as bdinfo
                    help_text = self._strhunt.string_at(help_ptr, allow_empty=True)

                    # Rule out some common false positives
                    if self._text_fp_regex.search(help_text) is not None:
                        return None

                    ret['help'] = help_text
                    ret['subcmd'] = usage == '' and help_text == ''
                else:
                    # Others, like the command 'true' leave the help pointer NULL.
                    ret['help'] = ''
                    ret['subcmd'] = False

                size += arch.word_size

            if autocomplete:
                complete_ptr, data = arch.ptr_value_adv(data)
                if not self._is_valid_ptr(complete_ptr, check_ptrs):
                    return None
                ret['autocomplete'] = complete_ptr
                size += arch.word_size

            ret['size'] = size
            return ret

        except (HunterResultNotFound, IndexError):
            # HunterResultNotFound - string_at()
            # IndexError - arch.to_*_adv() when we reach the end of self._data
            return None

    def _attempt_search_at(self, target, start, end, threshold, check_ptrs, longhelp, autocomplete):
        offset = start
        total_size = 0
        cmd_table = []

        while True:
            entry = self._cmd_tbl_s(offset, end, check_ptrs, longhelp, autocomplete)
            if entry is not None:
                cmd_table.append(entry)

                # They should all be the same...
                entry_size = entry['size']

                total_size += entry_size
                offset     += entry_size

                msg = 'Potential cmd_tbl_s @ 0x{:08x} ({:b}, {:b}) => {:s}{:s}{:s}'
                usage = entry['usage'].replace('\n', '').strip()
                sep = ' - ' if len(usage) != 0 else ''
                log.debug(msg.format(entry['address'], longhelp, autocomplete,
                                     entry['name'], sep, usage))

            elif len(cmd_table) >= threshold:
                if target:
                    target_found = False
                    for entry in cmd_table:
                        if entry['name'].lower() == target.lower():
                            target_found = True
                            break

                    if not target_found:
                        return None

                extra = {
                    'cmd_table': cmd_table,
                    'is_subcmd_table': sum([e['subcmd'] for e in cmd_table]) == len(cmd_table),
                    'autocomplete': autocomplete,
                    'longhelp': longhelp
                }

                return (start, total_size, extra)
            else:
                break

        return None

    def _search_at(self, target, start, end, **kwargs):
        # Number of valid-looking consecutive cmd_tbl_s entries we need to
        # see before we're confident we have a real result.
        threshold = kwargs.get('threshold', 5)

        # Confirm that we can de-reference pointers. Allow caller to disable
        # this, which might be valid if self._data is not a complete image.
        check_ptrs = kwargs.get('check_ptrs', True)

        # Do we have values for CONFIG_SYS_LONGHELP and CONFIG_AUTO_COMPLETE or should
        # we instead attempt to infer them?
        longhelp_iter = [kwargs['longhelp']]     if kwargs.get('longhelp')     is not None else [True, False]
        autocomp_iter = [kwargs['autocomplete']] if kwargs.get('autocomplete') is not None else [True, False]

        if end < start:
            end = self._end_offset + 1

        # Iterate over permutations of U-Boot config options
        for longhelp in longhelp_iter:
            for autocomplete in autocomp_iter:
                args = (target, start, end, threshold, check_ptrs, longhelp, autocomplete)
                result = self._attempt_search_at(*args)
                if result is not None:
                    return result

        # We don't cover the full range of [start, end]. Returning None signals
        # to our parent class that we need to iterate onto the next location.
        return None

    @staticmethod
    def _result_str_header(result: dict, table: dict, longhelp: bool, autocomplete: bool) -> str:
        tbl_type = 'Sub-command table' if result['is_subcmd_table'] else 'Command table'
        line = tbl_type + ' @ 0x{:08x} (file offset 0x{:08x}) - {:d} bytes, {:d} entries' + linesep

        ret = line.format(result['src_addr'], result['src_off'], result['src_size'], len(table))
        ret += '   CONFIG_SYS_LONGHELP={}, CONFIG_AUTO_COMPLETE={}'.format(longhelp, autocomplete) + 2 * linesep

        return ret

    @classmethod
    def result_str(cls, result: dict) -> str:
        """
        Convert :py:meth:`find()` and :py:meth:`finditer()` result dictionaries to a
        string suitable for printing to a user.
        """
        table = result['cmd_table']
        longhelp = result['longhelp']
        autocomplete = result['autocomplete']
        ret = cls._result_str_header(result, table, longhelp, autocomplete)

        i = 0
        for entry in table:
            ret += ' {:>5s} @ 0x{:08x}'.format('[' + str(i) + ']', entry['address']) + linesep
            ret += '        name: {:s}'.format(entry['name']) + linesep
            ret += '     maxargs: {:d}'.format(entry['maxargs']) + linesep
            ret += '     cmd_rep: 0x{:08x}'.format(entry['cmd_rep']) + linesep
            ret += '         cmd: 0x{:08x}'.format(entry['cmd']) + linesep

            if autocomplete:
                ret += '    complete: 0x{:08x}'.format(entry['autocomplete']) + linesep

            ret += '       usage: ' + entry['usage'].strip() + linesep

            if longhelp:
                helptext = entry['help'].replace('\n', '\n' + ' ' * 14).strip()
                if not helptext.endswith('\n'):
                    helptext += linesep
                ret += '        help: {:s} {:s}'.format(entry['name'], helptext) + linesep

            i += 1
        return ret

    @classmethod
    def result_summary_str(cls, result: dict) -> str:
        """
        This method is similar to :py:meth:`result_str()`, but returns a shorter summary string.
        """
        table = result['cmd_table']
        longhelp = result['longhelp']
        autocomplete = result['autocomplete']
        ret = cls._result_str_header(result, table, longhelp, autocomplete)

        i = 0
        for entry in table:
            ret += ' {:>5s} @ 0x{:08x} - {:s}'.format('[' + str(i) + ']', entry['address'], entry['name']) + linesep
            i += 1
        return ret
