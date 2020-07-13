# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# flake8: noqa=F401
"""
This module provides memory access functionality through :py:class:`.MemoryReader`
and :py:class:`.MemoryWriter` abstractions. These abstractions allow one to write
re-usable scripts and tools to interact with exposed U-Boot consoles, even when
the available commands vary platform to platform.

The underlying implementations are built atop of both U-Boot console commands
specifically intended for arbitrary memory access, as well as those often
overlooked (when deployed in production systems) as memory-access primitives.

During the initialization of a :py:class:`~depthcharge.Depthcharge` context,
the target platform is inspected to determine which memory operations are
available. In general, an API user should not need to manually instantiate
any of the classes within this *depthcharge.memory* subpackage. Instead, one only needs
to interact with higher level methods such as
:py:meth:`Depthcharge.read_memory() <depthcharge.Depthcharge.read_memory>`
and
:py:meth:`Depthcharge.write_memory() <depthcharge.Depthcharge.write_memory>`.
Familiarity with the underlying implementations, however, allows one to
choose an specific implementation (via the *impl=* keyword argument)
or introduce new implementations atop of vendor-specific commands.
"""

from .cp            import CpCrashMemoryReader, CpMemoryWriter
from .crc32         import CRC32MemoryReader, CRC32MemoryWriter
from .go            import GoMemoryReader
from .i2c           import I2CMemoryReader, I2CMemoryWriter
from .itest         import ItestMemoryReader
from .load          import LoadbMemoryWriter, LoadxMemoryWriter, LoadyMemoryWriter
from .memcmds       import MdMemoryReader
from .memcmds       import MmMemoryReader, MmMemoryWriter
from .memcmds       import MwMemoryWriter
from .memcmds       import NmMemoryReader, NmMemoryWriter
from .setexpr       import SetexprMemoryReader

from .reader        import MemoryReader, MemoryWordReader
from .data_abort    import DataAbortMemoryReader
from .stratagem     import StratagemMemoryWriter
from .writer        import MemoryWriter, MemoryWordWriter

from .patch         import MemoryPatch, MemoryPatchList
