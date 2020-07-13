
depthcharge.memory
=======================

.. automodule:: depthcharge.memory
    :members:

Base Classes
------------

.. autoclass:: MemoryReader
    :members:
    :private-members:
    :exclude-members: rank, _describe_op

.. autoclass:: MemoryWordReader
    :members:
    :private-members:
    :exclude-members: rank, _read

.. autoclass:: DataAbortMemoryReader
    :members:
    :private-members:
    :exclude-members: rank, _read, _read_word

.. autoclass:: MemoryWriter
    :members:
    :private-members:
    :exclude-members: rank, _describe_op

.. autoclass:: MemoryWordWriter
    :members:
    :private-members:
    :exclude-members: rank, _write

.. autoclass:: StratagemMemoryWriter
    :members:

.. _apimemimpl:

Implementations
---------------

**MemoryReader** / **MemoryWordReader**

* :py:class:`CRC32MemoryReader`
* :py:class:`GoMemoryReader`
* :py:class:`I2CMemoryReader`
* :py:class:`ItestMemoryReader`
* :py:class:`MdMemoryReader`
* :py:class:`MmMemoryReader`
* :py:class:`NmMemoryReader`
* :py:class:`SetexprMemoryReader`


**DataAbortMemoryReader** 

* :py:class:`CpCrashMemoryReader`


**MemoryWriter** / **MemoryWordWriter**

* :py:class:`CRC32MemoryWriter`
* :py:class:`LoadbMemoryWriter`
* :py:class:`LoadxMemoryWriter`
* :py:class:`LoadyMemoryWriter`
* :py:class:`MmMemoryWriter`
* :py:class:`MwMemoryWriter`
* :py:class:`NmMemoryWriter`


**StratagemMemoryWriter**

* :py:class:`CpMemoryWriter`
* :py:class:`CRC32MemoryWriter`

.. autoclass:: CRC32MemoryReader
    :exclude-members: rank

.. autoclass:: CRC32MemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: CpCrashMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: CpMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: GoMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: I2CMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: I2CMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: ItestMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: LoadbMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: LoadxMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: LoadyMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: MdMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: MmMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: MmMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: MwMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: NmMemoryReader
    :members:
    :exclude-members: rank

.. autoclass:: NmMemoryWriter
    :members:
    :exclude-members: rank

.. autoclass:: SetexprMemoryReader
    :members:
    :exclude-members: rank

Memory Patching
---------------

.. autoclass:: MemoryPatch
    :members:

.. autoclass:: MemoryPatchList
    :members:
