# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Defines DataAbortRegisterReader parent class
"""

from .reader import RegisterReader


class DataAbortRegisterReader(RegisterReader):
    """
    This is a type of :py:class:`.RegisterReader` that triggers a Data Abort
    on ARM targets and parses the crash output to retrieve a register value.

    For these to work, the system must automatically reset upon crash, and
    allow re-entry into the console. Subclasses must set the
    ``crash_or_reboot=True`` property in their private ``_required`` dictionary
    in order to exclude the operation when a user has indicated that this
    should not be permitted.
    """

    _memrd = None

    @classmethod
    def rank(cls, **_kwargs):
        # Rebooting the platform isn't ideal, but it's better than
        # requiring a write operation (e.g. GoRegisterReader)
        return 20

    def __init__(self, ctx, **kwargs):
        super().__init__(ctx, **kwargs)
        self._crash_addr = kwargs.get('da_crash_addr', 1)

    # This is expected. pylint: disable=no-self-use
    def _trigger_data_abort(self) -> str:
        """
        Subclasses must implement this method.

        It should trigger a data abort and return the crash dump text
        printed to the terminal. This class will take care of parsing it
        accordingly.
        """

        msg = 'Subclass must provide a `da_memrd` name or implement _trigger_data_abort()'
        raise NotImplementedError(msg)

    def _read(self, register: str, info) -> int:
        # Calm pylint: disable=assignment-from-no-return
        da_text = self._trigger_data_abort()

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

        da_dict = self._ctx.arch.parse_data_abort(da_text)
        return da_dict['registers'][register]
