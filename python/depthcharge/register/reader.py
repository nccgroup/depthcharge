# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Implements RegisterReader base class
"""

from ..operation import Operation


class RegisterReader(Operation):
    """
    Base class for :py:class:`Operation` implementations used to read device registers.
    """

    def read(self, register: str) -> int:
        """
        Read a value from the target device register, specified by name.
        Note that registers can be obtained using :py:class:`depthcharge.Architecture`.
        """
        (reg, info) = self._ctx.arch.register(register)
        return self._read(reg, info)

    def _setup(self):
        """
        :py:class:`RegisterReader` subclasses shall override this method to perform any
        necessary setup or preparation.
        """

    def _teardown(self):
        """
        :py:class:`RegisterReader` subclasses shall override this method to perform any
        necessary deinitialization actions.
        """

    def _read(self, register: str, info) -> int:
        """
        Subclasses of RegisterReader are required to implement the _read()
        method, which performs the specific operation.

        The subclass receives both the validated register name.
        """
        raise NotImplementedError(self.name + ' does not implement _read()')
