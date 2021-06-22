# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Execution of U-Boot "stand alone" programs via the "go" console command.
"""

import re

from .executor      import Executor
from ..operation    import Operation, OperationFailed

_GO_RC_RE = re.compile(r'##[\w\s,]+rc = 0x(?P<rc>[0-9a-fA-F]+)')


class GoExecutor(Executor):
    """
    This class implements the :py:class:`Executor` interface atop of U-Boot's
    builtin functionality for executing
    `U-Boot standalone programs <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/doc/README.standalone>`_
    via the ``go`` console command.
    """
    _required = {
        'commands': ['go']
    }

    @classmethod
    def rank(cls, **_kwargs):
        return 90

    def execute_at(self, address: int, *args, **kwargs):
        cmd = 'go 0x{:08x} '.format(address) + ' '.join(args)

        read_response = kwargs.get('read_response', True)

        if not read_response:
            self._ctx.send_command(cmd, read_response=False)
            return None

        resp = self._ctx.send_command(cmd)
        for line in reversed(resp.splitlines()):
            m = _GO_RC_RE.match(line)
            if m is not None:
                rc = int(m.group('rc'), 16)
                return (rc, resp)

        raise OperationFailed('Did not find standalone application return code.')


Operation.register(GoExecutor)
