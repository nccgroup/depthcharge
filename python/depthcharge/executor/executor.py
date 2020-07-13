# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Provides Executor base class definition.
"""

from ..operation import Operation


class Executor(Operation):
    """
    Abstract base class for :py:class:`~depthcharge.Operation` implementations that facilitate
    arbitrary code execution on the target device.
    """

    def execute_at(self, address: int, *args, **kwargs):
        """
        Instruct the target to execute instructions at the specified `address`.

        Any additional positional and keyword arguments are passed to the
        underlying :py:class:`~depthcharge.executor.Executor` implementation.

        **Note**: This method does not perform any pre-requisite validation before
        attempting to begin execution. Use the
        :py:func:`Depthcharge.execute_payload() <depthcharge.Depthcharge.execute_payload>`
        method when executing built-in payloads.
        """
        raise NotImplementedError
