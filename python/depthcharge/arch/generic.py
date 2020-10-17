# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Generic architectures
"""

from .arch import Architecture


class _Generic32(Architecture):
    """
    Generic 32-bit architecture with 4-byte word alignment
    """
    _alignment = 4
    _word_size = 4
    _phys_size = 4
    _word_mask = 0xffffffff
    _supports_64bit_data = False
    _generic = True
    _regs = {}


class Generic(_Generic32):
    """
    Generic 32-bit little endian architecture with 4-byte word alignment
    """
    _desc = 'Generic 32-bit, little-endian'
    _endianness = 'little'


class GenericBE(_Generic32):
    """
    Generic 32-bit big endian architecture with 4-byte word alignment
    """
    _desc = 'Generic 32-bit, big-endian'
    _endianness = 'big'


class _Generic64(Architecture):
    """
    Generic 64-bit architecture with 8-byte word alignment
    """
    _alignment = 8
    _word_size = 8
    _phys_size = 8
    _word_mask = 0xffffffff_ffffffff
    _supports_64bit_data = True
    _generic = True
    _regs = {}


class Generic64(_Generic64):
    """
    Generic 64-bit little endian architecture with 8-byte word alignment
    """
    _desc = 'Generic 64-bit, little-endian'
    _endianness = 'little'


class Generic64BE(_Generic64):
    """
    Generic 64-bit big endian architecture with 8-byte word alignment
    """
    _desc = 'Generic 64-bit, big-endian'
    _endianness = 'big'
