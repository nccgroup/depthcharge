# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
This module provides the base Operation class atop which different types of operation
implementations (e.g. memory read, memory write) are constructed, along with related
exceptions and peripheral classes.
"""

import shutil

from copy import deepcopy

from .log import DepthchargeLog


class OperationFailed(Exception):
    """
    Raised when an operation did not complete successfully.

    The exception message should further explain the nature and circumstances
    of the failure.
    """


class OperationNotSupported(OperationFailed):
    """
    Raised to denote that a requested operation is not supported in the current device state or
    configuration.
    """
    def __init__(self, cls, msg, *args):
        if cls is not None:
            if isinstance(cls, Operation):
                msg = cls.name + ' - ' + msg
            else:
                msg = cls.__name__ + ' - ' + msg
        super().__init__(msg.format(*args))


class OperationAlignmentError(OperationFailed):
    """
    Raised when an operation is attempted, but would (unintentionally) violate architecture-specific
    alignment data or memory address alignment requirements.

    When raising this exception, the *alignment* parameter must indicate the alignment size in
    bytes. If a class is passed via the *cls* parameter, its name will be prefixed to the exception
    message.
    """

    def __init__(self, alignment: int, cls=None):
        msg = ' requires address to be aligned on a {:d}-byte boundary'
        if cls is None:
            msg = 'Operation' + msg
        elif isinstance(cls, Operation):
            msg = cls.name + msg
        else:
            msg = cls.__class__.__name__ + msg

        super().__init__(msg.format(alignment))


class Operation:
    """
    This class provides a common base for different types of target device interactions.

    Generally, the direct subclasses of Operation will themselves be abstract base
    classes providing some common functionality for a particular type of operation. Examples
    of this include :py:class:`~depthcharge.memory.MemoryReader` and
    :py:class:`~depthcharge.memory.MemoryWriter`.

    """

    # Runtime registry of all available operations, accessed by name.
    _registered_ops  = {}

    # Operation-specific requirements. To be overridden by subclass.
    _required = {}

    # Operations requiring a Stratagem shall populate a spec and list which
    # Hunter subclass is used to create the stratagem
    _stratagem_spec   = None
    _stratagem_hunter = None

    def __init__(self, ctx, **_kwargs):
        self._ctx = ctx
        self._req = self.check_requirements(self._ctx)
        self.log = DepthchargeLog('(' + self.name + ') ')
        self.comment = ''

    @classmethod
    def register(cls, *args):
        """
        Register one or more available :py:class:`~depthcharge.Operation` implementations, by class.

        Once registered, Operations are accessible via :py:meth:`implementations()` and
        :py:meth:`get_implementation()`. These methods allow for more programmatic discovery and
        are intended to support command-line scripts that allow a user to choose an implementation.
        (*See the ``--op`` argument used in the Depthcharge scripts.*)

        This registration mechanism is used by Depthcharge modules themselves to present
        their implementation to core code. Most API users need not to concern themselves with this
        method unless they are writing their own :py:class:`depthcharge.Operation` implementations
        that they wish to load at runtime.

        By convention, the name of the class you register should contain a suffix associated with
        its parent class.  For example, if your *foo* class implements :py:class:`MemoryWriter`, it
        should be named ``FooMemoryWriter``.  As with the built-in operations, it will still be
        accessible from the command-line as ``foo`` and ``FooMemoryWriter``.
        """
        for arg in args:
            if not issubclass(arg, Operation):
                raise TypeError('Expected Operation subclass, got {}'.format(arg))
            cls._registered_ops[arg.__name__] = arg

    @classmethod
    def implementations(cls):
        """
        Return an iterable collection registered implementations, for a given
        abstract Operation class (e.g. :py:class:`~depthcharge.memory.MemoryWriter`).

        Calling this on :py:class:`~depthcharge.Operation` results in all available operations being
        returned.
        """
        all_ops = cls._registered_ops.values()
        if cls is Operation:
            return all_ops

        return [impl for impl in all_ops if issubclass(impl, cls)]

    @classmethod
    def get_implementation(cls, name: str):
        """
        Retrieve an :py:class:`~depthcharge.Operation` implementation by case-insensitive name.
        """
        try:
            return cls._registered_ops[name]
        except KeyError as e:
            lower_name = name.lower()
            for op_name in cls._registered_ops:
                if op_name.lower() == lower_name:
                    return cls._registered_ops[op_name]

            # Didn't find it. Just re-raise our exception as-is
            raise e

    @property
    def name(self) -> str:
        """
        Operation name (string)
        """
        return self.__class__.__name__

    @classmethod
    def class_name(cls) -> str:
        """
        Returns the operation name (string). Unlike the :py:meth:`name` property, which requires a
        class instance, this can be invoked on an :py:class:`~depthcharge.Operation` subclass
        itself.
        """
        return cls.__name__

    @property
    def required(self) -> dict:
        """
        Return a dictionary that describes the requirements and dependencies of a given
        :py:class:`~depthcharge.Operation` subclass.
        """
        return deepcopy(self._req)

    @classmethod
    def get_stratagem_spec(cls) -> dict:
        """
        Return this class's :py:class:`~depthcharge.Stratagem` specification,
        which is a dictionary defining the keys and their respective value types that are required
        in :py:class:`~depthcharge.Stratagem` entries.

        ``None`` is returned if the class does not use :py:class:`~depthcharge.Stratagem` objects.

        This baseline specification generally consists of the following the keys, all of which map to integers.

        * *src_addr* - Absolute address of source data.
        * *src_size* - Size of data at source location, in bytes.
        * *dst_off*  - Offset into destination location.

        Other keys may be present, however. For example, if an output size is not implicit, a
        `dst_size` parameter may be included.
        """
        return cls._stratagem_spec

    @classmethod
    def stratagem_hunter(cls, *args, **kwargs):
        """
        Returns a :py:class:`~depthcharge.hunter.Hunter` instance that can be used to create
        a :py:class:`~depthcharge.Stratagem` for a given :py:class:`~depthcharge.Operation`.
        The ``*args``, and ``**kwargs`` parameters are passed directly to the
        corresponding :py:class:`~depthcharge.hunter.Hunter` constructor.

        ``None`` is returned if the :py:class:`~depthcharge.Operation` does not require the use
        of a :py:class:`~depthcharge.hunter.Hunter`-generated :py:class:`~depthcharge.Stratagem`.
        """
        if cls._stratagem_spec is None or cls._stratagem_hunter is None:
            return None

        # Let PyLint know we that we are aware of the non-callable None case.
        #   pylint: disable=not-callable
        return cls._stratagem_hunter(*args, **kwargs)

    @staticmethod
    def _create_stratagem_spec(**kwargs):
        """
        Helper for creating consistent Stratagem specifications.

        This joins the baseline spec with the spec provided via ``**kwargs``.
        """
        ret = {
            'src_addr': int,
            'src_size': int,
            'dst_off':  int,
        }

        ret.update(kwargs)
        return ret

    @classmethod
    def check_requirements(cls, ctx):
        """
        Inspect the provided :py:class:`~depthcharge.Depthcharge` context object (*ctx*)
        to determine if the pre-requisites required to use a given :py:class:`~depthcharge.Operation`
        are satisfied.

        If they are not, a :py:exc:`depthcharge.OperationNotSupported` exception is raised.
        """

        s = {
            'arch': None,
            'companion': False,
            'crash_or_reboot': False,
            'commands': [],
            'variables': [],
            'payloads': [],
            'host_programs': {}
        }

        # Architecture restrictions
        s['arch'] = cls._required.get('arch', None)
        if s['arch']:
            err = False
            if isinstance(s['arch'], (list, tuple)):
                err = ctx.arch.name not in s['arch']
            elif isinstance(s['arch'], str):
                err = ctx.arch.name.lower() != s['arch'].lower()

            if err:
                raise OperationNotSupported(cls, 'Not available for ' + ctx.arch.description + ' architecture.')

        # Does this operation require that we're allowed to induce a crash / reset / reboot?
        # If so, is the user permitting this?
        s['crash_or_reboot'] = cls._required.get('crash_or_reboot', False)
        if s['crash_or_reboot'] and not ctx._allow_reboot:
            err = 'Operation requires crash or reboot, but opt-in not specified.'
            raise OperationNotSupported(cls, err)

        # Required command check
        for c in cls._required.get('commands', []):
            if isinstance(c, tuple):
                # Any of the items in the tuple are acceptable
                acceptable = [a for a in c if a in ctx._cmds]
                if len(acceptable) == 0:
                    msg = 'Requires at least one of: {:s}'
                    raise OperationNotSupported(cls, msg, ' '.join(c))

                s['commands'] += acceptable

            else:
                if c not in ctx._cmds:
                    msg = 'Command "{:s}" required but not detected.'
                    raise OperationNotSupported(cls, msg, c)

                s['commands'].append(c)

        # Companion device check
        s['companion'] = cls._required.get('companion', False)
        if s['companion'] and ctx.companion is None:
            err = 'Depthcharge companion device required, but none specified.'
            raise OperationNotSupported(cls, err)

        # Environment variable checks
        for v in cls._required.get('variables', []):
            if v not in ctx._env:
                msg = 'Environment variable "{:s}" required but not detected.'
                raise OperationNotSupported(cls, msg, v)
            s['variables'].append(v)

        # Binary payload checks
        for p in cls._required.get('payloads', []):
            if p not in ctx._payloads:
                msg = 'Invalid or unsupported payload "{:s}" required.'
                raise OperationNotSupported(cls, msg, p)
            s['payloads'].append(p)

        # Required host programs
        for p in cls._required.get('host_programs', []):
            p_full = shutil.which(p)
            if not p_full:
                msg = 'Host program "{:s}" required but not found in PATH.'
                raise OperationNotSupported(cls, msg, p)

            s['host_programs'][p] = p_full

        # Return descriptions of what has satisfied our requirements
        return s

    @classmethod
    def rank(cls, **kwargs) -> int:
        """
        Rank an :py:class:`Operation`, considering any criteria specified in *kwargs*.

        This ranking is represented by an integer value within the range of 0 to 100.
        A higher value implies that a particular :py:class:`~depthcharge.Operation` is better suited
        for performing a given task than alternative options with lower rankings.

        The ranking system is fairly subjective and subject to change, but roughly is defined as
        follows:

        +-------------------+----------------------------------------------------------------------+
        | Range (Inclusive) | Description                                                          |
        +===================+======================================================================+
        |      75 - 100     | A great choice.                                                      |
        |                   | Performs operation quickly and cleanly, with no major side effects.  |
        +-------------------+----------------------------------------------------------------------+
        |      50 - 74      | A pretty good choice.                                                |
        |                   | It gets the job done, but might not be the fastest.                  |
        +-------------------+----------------------------------------------------------------------+
        |      25 - 49      | An okay choice.                                                      |
        |                   | It might be quite slow and dirty the runtime state of the device.    |
        +-------------------+----------------------------------------------------------------------+
        |       0 - 24      | Suitable as a last-ditch effort.                                     |
        |                   | May be very slow, have some undesirable side-effects, or require     |
        |                   | a :py:class:`~depthcharge.Companion` device that's not needed by     |
        |                   | other Operations that could achieve the same result.                 |
        +-------------------+----------------------------------------------------------------------+

        Currently, one keyword argument is supported.

        The *data_len* keyword argument can be used to denote how many bytes of data are being
        handled. Some operation implementations may be better options for larger payloads do to some
        setup overhead, while not being a great choice for operating on just a couple bytes. This
        parameter is used to inform the ranking in this situation.

        The reason this class method supports arbitrary keyword arguments in order to accommodate
        the introduction of different Operations types in the furture.
        """
        raise NotImplementedError('Operation subclasses are required to implement rank()')


class OperationSet:
    """
    This class represents a set of :py:class:`~depthcharge.Operation` objects, allowing different
    types of operation instances to be grouped into respective collections.
    """

    def __init__(self, suffix=None):
        self._names = []
        self._obj = {}
        self._suffix = suffix

    def __len__(self):
        return len(self._obj)

    def __iter__(self):
        return iter([x[1] for x in self._obj.items()])

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._obj[key]

        if isinstance(key, int):
            return self._obj[self._names[key]]

        raise TypeError('Key expected to be str or int')

    def add(self, op):
        """
        Add an :py:class:`Operation` instance to the set.
        """
        if op.name not in self._obj:
            self._names.append(op.name)
            self._obj[op.name] = op

    def _find_by_name(self, op_name, try_suffix):
        op_name_lower = op_name.lower()

        # First try without suffix
        for n in self._names:
            n_lower = n.lower()
            if op_name_lower == n_lower:
                return self._obj[n]

        if try_suffix and self._suffix is not None and len(self._suffix) != 0:
            try:
                return self._find_by_name(op_name_lower + self._suffix, try_suffix=False)
            except ValueError:
                # Suppress this because the error message will have the appended suffix,
                # rather than exactly what the user entered. Fall through to the below
                # exception to deal with this.
                pass

        raise ValueError('No operation named "{:s}" available'.format(op_name))

    def _find_by_type(self, op):
        for (_, op_instance) in self._obj.items():
            if isinstance(op_instance, op):
                return op_instance

        return None

    def find(self, op, try_suffix=True):
        """
        Search the set for the specified operation. The requested :py:class:`~depthcharge.Operation`
        instance will be returned if present in the set. Otherwise, a :py:exc:`ValueError` is raised.

        The *op* argument can be specified as a class name of the desired
        :py:class:`~depthcharge.Operation` (i.e. a string).  The search is performed in a
        case-insensitive manner.  When *try_suffix=True*, the provided name does not need to contain
        the suffix associated with the particular :py:class:`~depthcharge.Operation` type. For
        example, the "*MemoryWriter*" can be omitted from the operation name when searching a set
        containing :py:class:`~depthcharge.memory.MemoryWriter`. For example, the following are
        equivalent:

        .. code:: python

            op = ctx.memory_writers.find('crc32')
            op = ctx.memory_writers.find('CRC32')
            op = ctx.memory_writers.find('CRC32MemoryWriter')

        The set can also be searched using a class as the *op* parameter:

        .. code:: python

            from depthcharge.memory import CRC32MemoryWriter

            op = ctx.memory_writers.find(CRC32MemoryWriter)

        Finally, the *op* argument can be provided as a list. The search of the set will be
        performed over each entry in the list until a matching :py:class:`~depthcharge.Operation`
        is found and returned.

        .. code:: python

            from depthcharge.memory import CRC32MemoryWriter

            op = ctx.memory_writers.find(['crc32', 'mw', 'nm'])

        """

        if isinstance(op, list):
            # Command-line parsing might give us a 1-element list.
            # The error message is more user-friendly this way.
            if len(op) == 1:
                self.find(op[0])

            # Otherwise, we have at least a couple options
            for entry in op:
                try:
                    return self.find(entry)
                except ValueError:
                    # Try the next entry
                    pass

            raise ValueError('Operations not available: ' + str(op))

        if isinstance(op, str):
            op_name = op
            result = self._find_by_name(op, try_suffix)
        elif isinstance(op, Operation):
            op_name = op.name
            result = self._find_by_type(type(op))
        elif isinstance(op, type) and issubclass(op, Operation):
            op_name = op.__class__.__name__
            result = self._find_by_type(op)
        else:
            msg = 'Expected string, list, or depthcharge.Operation. Got {:s}.'
            raise TypeError(msg.format(type(op).__name__))

        if result is None:
            msg = 'Operation "{:s}" not available'
            raise ValueError(msg.format(op_name))

        return result

    def default(self, **kwargs):
        """
        Return the best available default :py:class:`Operation` instance from the set.
        The "best" option is chosen based upon
        :py:meth:`Operation.rank() <depthcharge.Operation.rank>` and the following
        optional keyword arguments, specified here with their default values.

        Any keyword arguments beside those listed below are passed to :py:meth:`Operation.rank()`.
        (e.g. the *data_len=<n>* keyword argument)

        * The `exclude_reqts` keyword is a list or tuple that denotes that an :py:class:`Operation`
          should be excluded if it requires any of the items named in its list.  For example,
          ``exclude_reqts=('stratagem', 'payloads', 'companion')`` implies that any options that require
          the use of a :py:class:`Stratagem`, depend upon already-deployed payloads, or need to use a
          :py:class:`Companion` device should be excluded. The default value is
          ``exclude_reqts=('stratage')``.
        * An *exclude_op* keyword can be used to exclude specific instances of
          :py:class:`~depthcharge.Operation` from being returned. If an :py:class:`Operation` uses
          another to bootstrap itself, this can be used to exclude itself from the available
          options. A single object, list, or set may be provided. The default value is ``None``.
        """
        exclude_reqts  = kwargs.pop('exclude_reqts', ('stratagem'))
        exclude_op     = kwargs.pop('exclude', None)

        if exclude_op is None:
            exclude_op = []
        elif not isinstance(exclude_op, (list, tuple, set)):
            exclude_op = [exclude_op]

        candidates = []
        for (_, op) in self._obj.items():
            # Enforce exclusion of specific object instances
            if op in exclude_op:
                continue

            # Enforce exclusion of Operations based upon their requirements
            for item in exclude_reqts:
                try:
                    value = op._required.get(item)
                    if value:  # True or a non-empty list/dict
                        continue
                except KeyError:
                    # This is fine. It implies no requirement.
                    pass

            candidates.append(op)

        if not candidates:
            msg = 'No default {:s} available.'
            if self._suffix:
                msg = msg.format(self._suffix)
            else:
                msg = msg.format('operation')

            raise OperationNotSupported(None, msg)

        candidates = sorted(candidates, key=lambda c: c.rank(**kwargs), reverse=True)
        return candidates[0]
