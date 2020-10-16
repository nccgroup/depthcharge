# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
"""
This module provides Architecture-specific information and helper functions.
"""

from copy import copy


class ArchitectureProperties(type):
    """
    Custom metaclass used to provide immutable class property accessors.
    """

    _name = None
    _word_size = None
    _phys_size = None
    _alignment = None
    _endianness = None
    _regs = None

    @property
    def name(cls) -> str:
        """
        Short, 1-word name for the architecture
        """
        return cls._name

    @property
    def description(cls) -> str:
        """
        Short description of the architecture
        """
        return cls._desc

    @property
    def alignment(cls) -> int:
        """
        Required word alignment, in bytes
        """
        return cls._alignment

    @property
    def word_size(cls) -> int:
        """
        Word size, in bytes.

        Currently, this class assumes ``word size == sizeof(int) == sizeof(void*)``,
        which is technically not consistent with the C standard.

        However, we'll cross that bridge when we get to it. (i.e., when introducing support for an
        architechture that breaks usages of :py:meth:`word_size`)

        If you're concerned about breaking changes, stick to the methods in
        this class rather than use word_size for directly.
        """
        return cls._word_size

    @property
    def phys_size(cls) -> int:
        """
        Size of phys_size_t, in bytes.
        """
        return cls._phys_size

    @property
    def endianness(cls) -> str:
        """
        Either ``'big'`` or ``'little'``

        Depthcharge does not currently support situations where an architecture supports both.
        (e.g. ARM in big-endian mode).
        """
        return cls._endianness

    @property
    def supports_64bit_data(cls) -> bool:
        """
        Indicates whether U-Boot has ``CONFIG_SYS_SUPPORT_64BIT_DATA`` for this
        architecture set.

        In general, this determines whether "qword" operations are supported by various operations
        and monitor commands.
        """
        return cls._supports_64bit_data

    @property
    def gd_register(cls) -> str:
        """
        This property provides name of the register that stores a pointer to U-Boot's global data
        structure (*gd_t*).

        A value of ``None`` is used to denote that the architecture does not store this infromation
        in a register.
        """
        for reg, info in cls._regs.items():
            if info.get('gd', False):
                return reg

        return None


class Architecture(metaclass=ArchitectureProperties):
    """
    Provides access to architecture-specific properties and conversion methods.
    """

    @classmethod
    def get(cls, arch_name):
        """
        Retrieve an architecture definition by name.

        **Example**:

        .. code:: python

            from depthcharge import Architecture

            arm = Architecture.get('arm')
            print(arm.description)
            for reg_name in arm.registers():
                print('  ' + reg_name)

        """
        for arch in cls.__subclasses__():
            if arch._name.lower() == arch_name.lower():
                return arch

        raise KeyError('No such architecture: ' + arch_name)

    @classmethod
    def supported(cls):
        """
        Returns a generator for all supported architectures.

        **Example**:

        .. code:: python

            from depthcharge import Architecture

            for arch in Architecture.supported():
                print(arch.name)

        """
        for arch in cls.__subclasses__():
            yield arch

    @classmethod
    def is_aligned(cls, address):
        """
        Returns ``True`` if *address* is word-aligned, and ``False`` otherwise.
        """
        return address & (cls._alignment - 1) == 0

    @classmethod
    def ptr_value(cls, data: bytes) -> int:
        """
        Read a pointer from the provided data and return this address as an
        integer in the host endianness.
        """
        return int.from_bytes(data[:cls._word_size], cls._endianness)

    @classmethod
    def ptr_value_adv(cls, data: bytes) -> int:
        """
        Returns a tuple *(value, data_slice)* such that the first element is the
        result of :py:meth:`ptr_value()`, and *data_slice* is *data* advanced by the size
        of the pointer.
        """
        return (cls.ptr_value(data), data[cls._word_size:])

    @classmethod
    def int_to_bytes(cls, intval: int) -> bytes:
        """
        Convert an integer value to `bytes`, according to the architecture's
        endianness and word size.
        """
        return intval.to_bytes(cls._word_size, cls._endianness)

    @classmethod
    def to_int(cls, data: bytes):
        """
        Returns the value in the provided data converted to a signed two's
        complement integer in the host endianness.
        """
        sign_bit = (1 << (cls._word_size * 8 - 1))
        mask     = (1 << (cls._word_size * 8)) - 1

        val = cls.to_uint(data)
        if val & sign_bit != 0:
            # Two's complement
            return -((~val & mask) + 1)

        return val

    @classmethod
    def to_int_adv(cls, data: bytes):
        """
        Returns a tuple *(value, data_slice)* such that the first element is the result of
        :py:meth:`to_int()`, and *data_slice* is *data* advanced by the size of the target's integer.
        """
        return (cls.to_int(data), data[cls._word_size:])

    @classmethod
    def to_uint(cls, data: bytes):
        """
        Returns the value in the provided data converted to an unsigned integer
        in the host endianness.
        """
        return int.from_bytes(data[:cls._word_size], cls._endianness)

    @classmethod
    def to_uint_adv(cls, data: bytes):
        """
        Returns a tuple *(value, data_slice)* such that the first element is the
        result of :py:meth:`to_uint()`, and *data_slice* is *data* advanced by the size of the
        target's (unsigned) integer.
        """
        return (cls.to_uint(data), data[cls._word_size:])

    @classmethod
    def hexint_to_bytes(cls, hex_str: str, num_bytes: int) -> int:
        """
        Convert a hexadecimal string representing an integer value to bytes,
        taking the architecture's endianness into account.
        """
        return int(hex_str, 16).to_bytes(num_bytes, cls._endianness)

    @classmethod
    def word_sizes(cls) -> dict:
        """
        This property provides a dictionary of word sizes supported by the
        architecture (int), mapped the command suffix used by U-Boot's memory
        commands (i.e., 'b', 'w', 'l', 'q').

        The quad-word suffix is only included if the architecture supports
        64-bit data, per :py:meth:`supports_64bit_data`.
        """
        ret = {1: 'b', 2: 'w', 4: 'l'}
        if cls.supports_64bit_data:
            ret[8] = 'q'
        return ret

    @classmethod
    def multiple_of_word_size(cls, value: int) -> bool:
        """
        Returns ``True`` if the provided *value* is a multiple of the
        architecture's word size, and ``False`` otherwise.
        """
        return value % cls._word_size == 0

    @classmethod
    def registers(cls) -> dict:
        """
        Dictionary containing registers names as keys and additional
        information (if any) in corresponding values.

        Special keys (i.e. not included with every entry) include:

            * `alias` - A string containing an alternate name for the register (e.g. `'sp'`).
            * `gd=True` if the register store's U-Boot global data structure.
            * `ident` - An integer identifier used internally (e.g. in payloads).

        """
        return copy(cls._regs)

    @classmethod
    def register(cls, name: str) -> tuple:
        """
        Look up a single register by case insensitve name or alias.

        The returned value is a tuple containing its corresponding key and value
        in the dictionary returned by :py:meth:registers()`.

        Raises :py:exc:`ValueError` for an invalid register name/alias.
        """
        for reg_name, info in cls._regs.items():
            if name in (reg_name, reg_name.upper(), reg_name.lower()):
                return (reg_name, info)

            try:
                alias = info['alias']
                if name in (alias, alias.upper(), alias.lower()):
                    return (reg_name, info)
            except KeyError:
                pass  # Not all registers have aliases

        raise ValueError('Invalid or unknown register: ' + name)
