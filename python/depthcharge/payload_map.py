# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Implements PayloadMap - Although technically "public" this module
isn't documented in the API because its utility is tightly coupled
to internals of the Depthcharge class.
"""


from . import log
from . import builtin_payloads

from .operation import Operation


def _load_builtins(arch, payloads: list, exclude: set):
    """
    Load built-in payloads into `payloads`, excluding any whose
    names appear in the `exclude` set.
    """
    for attr in dir(builtin_payloads):
        if not isinstance(attr, str) or attr.startswith('_'):
            continue

        if attr in exclude:
            continue

        payload_dict = getattr(builtin_payloads, attr)
        try:
            payload = payload_dict[arch.name.lower()]
            payloads.append((attr, payload))
        except KeyError:
            msg = 'Payload "{:s}" not implemented for {:s}'
            log.warning(msg.format(attr, arch.name))


class PayloadMap:
    """
    Tracks locations of deployed payloads.

    The current implementation is simple and allocates space for all payloads,
    even if they do not ultimately need to be deployed and used.
    """

    def __init__(self, arch, base: int, **kwargs):
        self._base = base
        self._off  = 0
        self._map  = {}
        self._align = kwargs.get('align', 16)
        self._skip_deploy = kwargs.get('skip_deploy', False)

        exclude_builtins = kwargs.get('exclude_builtins', False)
        excluded = kwargs.get('exclude', set())

        payloads = []

        # Aggregate built-in payloads
        if not exclude_builtins:
            _load_builtins(arch, payloads, excluded)

        # Aggregate user-provided payloads
        user_payloads = kwargs.get('payloads', None)
        if user_payloads:
            payloads += user_payloads

        # Assign each payload to its corresponding location
        for payload in payloads:
            self.insert(payload[0], payload[1])

    def insert(self, name: str, payload: bytes, required_by=None):
        """
        Insert a `payload`, identified by `name`, into the PayloadMap.
        This will assign it the next available address in the map.

        If `required_by` is specified, the payload's association to an
        :py:class:`depthcharge.Operation` subclass will be recorded. This
        information can be provided later via :py:meth:`mark_required_by`.

        Returns `True` if the payload added. If a payload with the same
        name is already present, then `False` is returned. In this latter case,
        The `required_by` information is still added to the corresponding
        entry.
        """
        if name not in self._map:
            address = self._base + self._off
            size = len(payload)

            if self._align > 1:
                self._off += size + (self._align - 1)
                self._off = (self._off // self._align) * self._align
            else:
                self._off += size

            self._map[name] = {
                'address':      address,
                'deployed':     False,
                'skip_deploy':  self._skip_deploy,
                'data':         payload,
                'size':         size,
                'required_by':  set()
            }
        else:
            log.debug('{} is already in the PayloadMap'.format(name))

        if required_by:
            self.mark_required_by(name, required_by)

    def __iter__(self):
        return iter(self._map)

    def __getitem__(self, name):
        try:
            return self._map[name]
        except KeyError:
            msg = 'No such payload registered in PayloadMap: "{}"'.format(name)
            raise KeyError(msg)

    @property
    def base_address(self):
        """
        This property specifies the base memory address at which payloads shall
        be written to.
        """
        return self._base

    def mark_deployed(self, name, state=True):
        """
        Mark the payload referred to by `name` as being deployed.
        """
        payload = self._map[name]
        payload['deployed'] = state

    def mark_required_by(self, payload_name: str, operation):
        """
        Mark the payload referred to by `name` as being required by
        the specified `operation`, which may be the operation
        name (str) or an instance of an Operation subclass.

        A list of str or Operation instances is also permitted.
        """
        if isinstance(operation, list):
            for op_entry in operation:
                self.mark_required_by(payload_name, op_entry)
            return

        if isinstance(operation, Operation):
            operation = operation.name
        elif not isinstance(operation, str):
            msg = 'Expected operation argument to be str, Operation, or list. Got {:s}'
            raise TypeError(msg.format(type(operation).__name__))

        self._map[payload_name]['required_by'].add(operation)
