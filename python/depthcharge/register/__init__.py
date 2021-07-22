# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# flake8: noqa=F401
"""
The *depthcharge.register* subpackage provides register
access functionality.

Bear in mind that not all registers will be accessible, given that some subset
will be tainted by virtue of executing code in an attempt to read them. This is
intended only for retrieving special register values, such as that reserved for
U-Boot's global data structure pointer.
"""

from .cp            import CpCrashRegisterReader
from .crc32         import CRC32CrashRegisterReader
from .fdt           import FDTCrashRegisterReader
from .itest         import ItestCrashRegisterReader

from .memcmds       import (
    MdCrashRegisterReader,
    MmCrashRegisterReader,
    MwCrashRegisterReader,
    NmCrashRegisterReader,
)

from .setexpr       import SetexprCrashRegisterReader

from .reader        import RegisterReader
from .data_abort    import DataAbortRegisterReader
