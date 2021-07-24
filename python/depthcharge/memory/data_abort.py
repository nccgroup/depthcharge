# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Provides DataAbortMemoryReader base class
"""

import os
import sys

from .reader import MemoryWordReader
from ..operation import OperationNotSupported

# TODO: The "Code:" line was added to the U-Boot ARM interrupt code in
# bd2a13f32959a851d43d9681d9dc9b8bb3eec398, circa May 2018. We can perhaps leverage this to turn
# what were previously only *CrashRegisteReaders into DataAbortMemoryReader implementations.


class DataAbortMemoryReader(MemoryWordReader):
    """
    Available only for ARM targets.

    This is a :py:class:`.MemoryWordReader` that extracts memory contents by triggering Data Aborts
    and parsing the relevant value from the register dump printed by U-Boot when this occurs.

    A *da_data_reg* keyword argument may be provided to specify the name of the register that is
    expected to contain memory read contents. It defaults to an architecture-specific value.
    This value can be overridden by a *DEPTHCHARGE_DA_DATA_REG* environment variable.

    A *da_crash_addr* keyword argument can be used to specify a memory address to access in
    order to induce a data abort. It defaults to an architecture-specific value.
    This value can be overridden by a *DEPTHCHARGE_DA_ADDR* environment variable.

    Given that this reader causes the platform to reset, it may be the case that the data you're
    attempting to read is overwritten during the crash-reset-init series of operations. Two
    workaround for this situation are provided:

    1. A *da_pre_fn* keyword argument, which will be executed before each word read. This function
       must accept the following parameters: ``(address: int, size: int, pre_info)``

       Note that the final argument is any value passed as to this constructor as *da_pre_info*
       keyword argument. You'll likely want to use a type that can be instantiated early
       and populated later, such as a dictionary. This allows items such as a
       :py:class:`~depthcharge.Depthcharge` context to be added following the completion
       of initialization code.


    2. A *da_pre_cmds* keyword argument may be specified as a semicolon-delimited command string
       or as a tuple/list of commands. These will be executed before each word-read.

    If both are provided, they will be executed in the order shown here.
    """

    def __init__(self, ctx, **kwargs):
        da_data_reg_env = os.getenv('DEPTHCHARGE_DA_DATA_REG')
        if da_data_reg_env is not None:
            data_reg = da_data_reg_env
        else:
            data_reg = kwargs.get('da_data_reg', ctx.arch.data_abort_data_reg)

        da_crash_addr_env = os.getenv('DEPTHCHARGE_DA_ADDR')
        if da_crash_addr_env is not None:
            crash_addr = int(da_crash_addr_env, 0)
        else:
            crash_addr = kwargs.get('da_crash_addr', ctx.arch.data_abort_address)

        if data_reg is None:
            err = 'No data abort register target is defined for ' + ctx.arch.description
            raise OperationNotSupported(self.__class__, err)

        if crash_addr is None:
            err = 'No data abort address is defined for ' + ctx.arch.description
            raise OperationNotSupported(self.__class__, err)

        super().__init__(ctx, **kwargs)

        self._data_reg = data_reg
        self._crash_addr = crash_addr

        self._pre_fn = kwargs.get('da_pre_fn', None)
        if self._pre_fn and not callable(self._pre_fn):
            raise TypeError('pre_fn must be callable')

        self._pre_info = kwargs.get('da_pre_info', None)

        self._pre_cmds = kwargs.get('da_pre_cmds', ())
        if isinstance(self._pre_cmds, str):
            self._pre_cmds = (self._pre_cmds,)

    def _trigger_data_abort(self, address, **kwargs) -> str:
        """
        Sub-classes must implement this method and return the data abort text.
        """
        raise NotImplementedError

    def _read_word(self, addr: int, size: int, handle_data):
        if self._pre_fn:
            self._pre_fn(addr, size, self._pre_info)

        for pre_cmd in self._pre_cmds:
            self._ctx.send_command(pre_cmd)

        arch = self._ctx.arch
        da_text = self._trigger_data_abort(addr)


        # Run user-provided post-reboot callback, if configured
        if self._ctx._post_reboot_cb is not None:
            # Callback is responsible for interrupt() call, if they want it.
            # This is intended to allow them to perform any necessary actions
            # before we allow interrupt() to time out. (e.g. attempt to enter
            # an autoboot "STOP_STR".
            self._ctx._post_reboot_cb(self._ctx._post_reboot_cb_data)
        else:
            # Catch console on reset
            self._ctx.interrupt()

        da_dict = arch.parse_data_abort(da_text)
        value = da_dict['registers'][self._data_reg]
        data = value.to_bytes(arch.word_size, sys.byteorder)

        handle_data(data[:size])
