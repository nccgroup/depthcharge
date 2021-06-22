depthcharge.hunter
==================

.. automodule:: depthcharge.hunter

Base Class
----------

.. autoclass:: Hunter
    :members:

    .. method:: _search_at(target, start_offset: int, end_offset: int, **kwargs) -> dict
        
        **Private Method**: *Not to be called directly by API users*

        Hunter implementations that wish to leverage the aforementioned
        facilities of the default :py:meth:`.find()`, :py:meth:`.finditer()`, and
        :py:meth:`.build_stratagem()` methods should implement this. 

        The implementation should search for the *target* information within
        the Hunter's *data* (provided via its constructor).  The search should
        be performed within the bounds of *start_offset* and *end_offset*, which
        will be guaranteed to be within the bounds of *data*.

        If a result is found, this method should return a dictionary per the
        description of :py:meth:`.find()`.

        If no result is found and the implementation searched the **entire
        range** of *[start_offset, end_offset]* in a single call, it should
        raise a :py:exc:`.HunterResultNotFound` exception.

        Otherwise, if no result is found and the implementation only checked
        that no match was present at *start_offset*, it should return ``None``.
        The parent class will take care care of repeatedly calling
        :py:meth:`_search_at()` to complete a search of the full range.


Implementations
---------------

* :py:class:`.CommandTableHunter`
* :py:class:`.ConstantHunter`
* :py:class:`.CpHunter`
* :py:class:`.EnvironmentHunter`
* :py:class:`.FDTHunter`
* :py:class:`.ReverseCRC32Hunter`
* :py:class:`.StringHunter`

.. autoclass:: CommandTableHunter
    :members:

    .. method:: find(target, start=-1, end=-1, **kwargs) -> dict

        This :py:class:`~.Hunter` searches for a command table containing the command
        specified by *target*.  If *target* is ``None`` or an empty string, the first
        table found in the search range will be returned.

        The following keyword arguments can be used to further configure
        the search behavior.

        +---------------+-------+---------+-------------------------------------------------------+
        | Name          | Type  | Default | Description                                           |
        +===============+=======+=========+=======================================================+
        | threshold     |  int  |   5     | Number of valid-looking consecutive cmd_tbl_s entries |
        |               |       |         | to observe before a table is considered valid.        |
        +---------------+-------+---------+-------------------------------------------------------+
        | check_ptrs    | bool  | True    | Follow pointers in order to confirm whether data at a |
        |               |       |         | given search location is a command table entry.       |
        |               |       |         | Setting this to ``False`` will result in false        |
        |               |       |         | positives.                                            |
        +---------------+-------+---------+-------------------------------------------------------+
        | longhelp      | bool  | None    | Denotes state of U-Boot's `CONFIG_SYS_LONGHELP`_.     |
        |               |       |         | Keep this set to ``None`` if you do not know it; the  |
        |               |       |         | Hunter will attempt to infer the right value.         |
        +---------------+-------+---------+-------------------------------------------------------+
        | autocomplete  | bool  | None    | Denotes state of U-Boot's `CONFIG_AUTO_COMPLETE`_.    |
        |               |       |         | Keep this set to ``None`` if you do not know it; the  |
        |               |       |         | Hunter will attempt to infer the right value.         |
        +---------------+-------+---------+-------------------------------------------------------+

        .. _CONFIG_SYS_LONGHELP: https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/cmd/Kconfig#L41
        .. _CONFIG_AUTO_COMPLETE: https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/cmd/Kconfig#L34

    .. method:: finditer(self, target, start=-1, end=-1, **kwargs)

        Returns an iterator that provides each command table found in the search range.

        Refer to :py:meth:`.find()` for a description of *target* and supported keyword arguments.

        Otherwise, it behaves as described in :py:meth:`Hunter.finditer()`.
    
.. autoclass:: ConstantHunter
    :members:

    .. method:: find(target, start=-1, end=-1, **kwargs) -> dict

    Searches for constant specified by *target*.

    .. method:: finditer(target, start=-1, end=-1, **kwargs) -> dict

    Returns an iterator over all occurrences of *target* in the search range.

.. autoclass:: CpHunter
    :members:

.. autoclass:: EnvironmentHunter
    :members:

    .. method:: find(target, start=-1, end=-1, **kwargs) -> dict

    If *target* is an empty string or ``None``, the first environment encountered
    in the search range is returned. Otherwise, only an environment containing the
    string or byte specified by *target* will be returned.

    In addition to the standard keys returned by :py:meth:`.Hunter.find()`, EnvironmentHunter
    includes the additional items:

    * *arch* - The architecture of the platform. (This will inform the endianness of checksum.)
    * *type* - One of: 'Built-in environment', 'Stored environment', 'Stored redundant environment'
    * *crc* - The CRC32 checksum of the environment (if one of the 'Stored' types)
    * *flags* - Only present for 'Stored redundant environment'. Contains monotonically increasing (modulo 256)
      integer value used to determine which redundant environment is "freshest".
    * *dict* - The environment contents as a dictionary, with the variable names as keys.
    * *raw* - The raw environment data as NULL-terminated ASCII strings (type: *bytes*). 

    .. method:: finditer(self, target, start=-1, end=-1, **kwargs)

        Returns an iterator that provides each environment instance found in the search range.

        Refer to :py:meth:`.find()` for a description of *target* and supported keyword arguments.

        Otherwise, it behaves as described in :py:meth:`Hunter.finditer()`.

.. autoclass:: FDTHunter
    :members:

    .. method:: find(target, start=-1, end=-1, **kwargs) -> dict

    If a device tree containing a specific string or byte sequence is desired,
    this can be specified via *target*. Otherwise it can be left as ``None`` to
    search for any device tree.
    
    The returned dictionary will contain the binary representation of the device tree
    in a ``'dtb'`` entry.  If the Device Tree Compiler is installed on your machine,
    a source representation will additionally be provided in a ``'dts'`` entry.

    A *no_dts=True* keyword argument can be used to prevent the :py:class:`.FDTHunter`
    from attempting to convert a DTB to a DTS.

    .. method:: finditer(self, target, start=-1, end=-1, **kwargs)

        Returns an iterator that provides each Flattened Device Tree instance found in the search range.

        Refer to :py:meth:`.find()` for a description of *target* and supported keyword arguments.


.. autoclass:: ReverseCRC32Hunter
    :members:
    
.. autoclass:: StringHunter
    :members:

    .. method:: find(target, start=-1, end=-1, **kwargs) -> dict

        The *target* argument should contain a regular expression pattern of type
        ``str`` or ``bytes``. The following keyword arguments may be used to constrain
        the length of the desired string. 

        
        +---------------+-------+---------+-------------------------------------------------------+
        | Name          | Type  | Default | Description                                           |
        +===============+=======+=========+=======================================================+
        | min_len       | int   | -1      | If > 0, places a lower bound on the string to locate  |
        +---------------+-------+---------+-------------------------------------------------------+
        | max_len       | int   | -1      | If > 0, places an upper bound on the string to locate |
        +---------------+-------+---------+-------------------------------------------------------+

        If one is only looking for **any printable string** within a search range, *target* can be
        specified as ``None`` or an empty string. The above keyword arguments
        can be used to constrain results.

        The *start* and *end* parameters are used as described in :py:meth:`Hunter.find()`.
    

    .. method:: finditer(self, target, start=-1, end=-1, **kwargs)

        Returns an iterator that provides each Flattened Device Tree instance found in the search range.

        Refer to :py:meth:`.find()` for a description of *target* and supported keyword arguments.


Exceptions
----------

.. autoexception:: HunterResultNotFound

