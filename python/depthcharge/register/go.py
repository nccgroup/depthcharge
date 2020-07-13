# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements GoRegisterReader
"""

from ..operation import Operation
from .reader import RegisterReader


class GoRegisterReader(RegisterReader):
    """
    Uses the "go" console command to execute a register read payload.

    Note that some regsiters are inherently tainted using this approach; it
    is not neccessarily possible to read every register.
    """
    _required = {
        'commands': ['go'],
        'payloads': ['RETURN_REGISTER'],
    }

    @classmethod
    def rank(cls, **_kwargs):
        # Not ideal - Requires payload deployment (write operation)
        return 10

    def _read(self, register: str, info) -> int:
        reg_ident = info['ident']
        (rc, _) = self._ctx.execute_payload('RETURN_REGISTER', chr(reg_ident), impl='GoExecutor')
        return rc


Operation.register(GoRegisterReader)
