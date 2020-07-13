# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
This module provides the Stratagem class and related exceptions.
"""

import json

from copy import copy
from datetime import datetime

from .operation import Operation
from .version import __version__


class StratagemRequired(TypeError):
    """
    The StratagemRequired exception is a specific kind of TypeError that is
    raised when "raw data" (e.g. ``bytes``) was passed to an Operation, but that
    Operation can only accept a Stratagem as input.
    """
    def __init__(self, name):
        msg = name + ' requires a Stratagem in order to perform the requested operation'
        super(StratagemRequired, self).__init__(msg)


class StratagemNotRequired(Exception):
    """
    This exception is raised when an attempt to create a Stratagem is made
    for an Operation that does not necessitate it.
    """


class StratagemCreationFailed(Exception):
    """
    It may be the case that a Stratagem cannot be created, given the
    inherent constraints of the input and those of the creation parameters.
    This Exception may be raised to signal that a result was not possible to create.
    """


class Stratagem:
    """
    Some :py:class:`~depthcharge.Operation` implementations, such as
    :py:class:`~depthcharge.memory.CRC32MemoryWriter`, cannot perform their objective directly (e.g.
    writing an arbitrary value to a selected memory address). Instead, they must perform a
    roundabout sequence of operation to achieve this goal.

    Within the Depthcharge project, this type of indirect operation is referred to as a
    `Stratagem <https://www.merriam-webster.com/dictionary/stratagem>`_.

    A Stratagem encapsulates a list of dictionaries, whose keys are defined and only relevant to the
    corresponding :py:class:`~depthcharge.hunter.Hunter` and :py:class:`~depthcharge.Operation`
    implementations that generate and use them, respectively.

    :py:class:`~depthcharge.Operation` subclasses that require a Stratagem are expected to provide
    a "*Stratagem specification*" via their :
    :py:meth:`Operation.stratagem_spec() <depthcharge.Operation.stratagem_spec>` method.

    API users usually do not need to instantiate a Stratagem directly, but rather receive them
    from :py:meth:`Hunter.build_stratagem() <depthcharge.hunter.Hunter.build_stratagem>`
    implementations. Nonetheless, the constructor arguments are as follows:

    * The *op_class* argument shall be an :py:class:`~depthcharge.Operation` subclass (not an
      instance of that class, but the class itself) that provides a Stratagem specification
      in its :py:meth:`stratagem_spec() <depthcharge.Operation.stratagem_spec>` method.
    * If the final size of the Stratagem is known in advance, it can be created with this initial
      capacity via the **capacity** keyword. Doing this allows the Stratagem entries to be
      set using the index (``[]``) notation implemented by ``__setitem__``. Otherwise,
      :py:meth:`append()` must be used to add entries to the Stratagem.

    """

    def __init__(self, op_class, capacity: int = -1, **kwargs):
        self._op = op_class .__name__
        self._spec = op_class.get_stratagem_spec()

        # The entries of this list describe how we achieve the desired operation
        if capacity > 0:
            self._list = capacity * [None]
        else:
            self._list = []

        # Just carried along for the ride when we generate Stratagem so we can
        # recall how it was created.
        self.comment = kwargs.get('comment', '')
        self.timestamp = kwargs.get('timestamp', datetime.now().isoformat())

    def entries(self):
        """
        Returns (a generator for) entries in the Stratagem.

        The returned elements are copies; the caller is free to modify them and
        this will not affect the state of the Stratagem.
        """
        for entry in self._list:
            yield copy(entry)

    def __getitem__(self, index):
        return copy(self._list[index])

    def _process_entry(self, entry: dict):
        """
        Iterate over items in `entry` dictionary and perform conversions
        to the expected types.

        May raise TypeError or ValueError.
        """
        for key in entry:
            # Potential KeyError for key not present in spec
            expected_type = self._spec[key]

            # Potential value for invalid type conversion
            if expected_type is int and isinstance(entry[key], str):
                # Ensure we can support hex values prefixed with 0x
                entry[key] = int(entry[key], 0)
            else:
                entry[key] = expected_type(entry[key])

        return entry

    def __setitem__(self, index, entry):
        self._process_entry(entry)
        self._list[index] = entry

    @property
    def operation_name(self) -> str:
        """
        Name of the :py:class:`depthcharge.Operation` intended for
        use with this Stratagem.
        """
        return self._op

    def append(self, entry: dict = None, **kwargs):
        """
        Append an entry to the Stratagem.

        The key-value pairs may be provided in the *entry* dictionary or as keyword arguments to
        this method.

        The key names and the value types will be validated according to the Stratagem's
        specification (obtained from the associated :py:class:`~depthcharge.Operation`).
        """

        # Support appending a list of entries
        if isinstance(entry, list):
            for e in entry:
                self.append(e)
            return

        # Otherwise we're handling a single entry defined as either a
        # dictionary or keyword arguments.
        #
        # Technically one could provide both; I'm not sure why one would want
        # to do that, but we make no guarentees right now about the result.
        # Currently, the kwargs take precedence.
        if entry is None:
            entry = {}
        else:
            entry = copy(entry)

        for key in kwargs:
            entry[key] = kwargs[key]

        self._list.append(self._process_entry(entry))

    def __len__(self):
        return len(self._list)

    @property
    def total_operations(self):
        """
        Total number of operations performed when executing this Stratagem.

        For Stratagem whose entries contain an *iterations* key denoting that multiple
        iterations of an operation are required, this will reflect the total number
        of operations performed; the result will be larger than the value returned by
        :py:meth:`len()`, which instead denotes how many entries are in the Stratagem.
        """
        count = 0
        for entry in self._list:
            try:
                count += entry['iterations']
            except KeyError:
                count += 1

        return count

    def __str__(self):
        return self.to_json(indent=4)

    @classmethod
    def from_json(cls, json_str: str):
        """
        Create a Stratagem object from a provided JSON string.
        """
        tmp = json.loads(json_str)

        try:
            op_name = tmp['operation']
            op_class = Operation.get_implementation(op_name)
        except KeyError:
            raise ValueError('Invalid Operation name encountered: ' + op_name)

        key_spec = op_class.get_stratagem_spec()
        if key_spec is None:
            raise StratagemNotRequired(op_name + ' does not require the use of Stratagem objects')

        stratagem = Stratagem(op_class,
                              comment=tmp.get('comment', ''),
                              timestamp=tmp.get('timestamp', ''))

        # Copy each entry in order to bring validation logic along for the ride
        for entry in tmp['entries']:
            stratagem.append(entry)

        return stratagem

    @classmethod
    def from_json_file(cls, filename: str):
        """
        Create a Stratagem object from the contents of the specified JSON file.
        """
        with open(filename, "r") as infile:
            data = infile.read()
            return cls.from_json(data)

    def to_json(self, **kwargs) -> str:
        """
        Convert the Stratagem to a JSON string.
        """
        keyspec = {}
        for key in self._spec:
            keyspec[key] = self._spec[key].__name__

        obj = {}
        obj['operation'] = self._op
        obj['depthcharge_version'] = __version__
        obj['timestamp'] = self.timestamp
        obj['comment'] = self.comment
        obj['entries'] = self._list

        # Default to a human readable file
        if 'indent' not in kwargs:
            kwargs['indent'] = 4

        return json.dumps(obj, **kwargs)

    def to_json_file(self, filename, **kwargs):
        """
        Conver the Stratagem to a JSON string and write it to the specified file.
        """
        with open(filename, "w") as outfile:
            outfile.write(self.to_json(**kwargs))
