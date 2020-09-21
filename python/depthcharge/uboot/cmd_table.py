# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
U-Boot command table ("linker list") parsing and analysis functionality
"""


def entry_to_bytes(arch, entry: dict) -> bytes:
    """
    Pack a U-Boot command table *entry* (struct cmd_tbl_s), as defined by the
    following dictionary keys and return it's representation in bytes.

    +---------------+---------------+----------------------------------------------+
    | Key           | Value Type    | Description                                  |
    +===============+===============+==============================================+
    | name          | int           | Pointer to command name string               |
    +---------------+---------------+----------------------------------------------+
    | maxargs       | int           | Maximum number of arguments the command takes|
    +---------------+---------------+----------------------------------------------+
    | cmd_rep       | int           | Depending upon the U-Boot version, either a  |
    |               |               | flag or function pointer used for command    |
    |               |               | autorepeat behavior                          |
    +---------------+---------------+----------------------------------------------+
    | cmd           | int           | Function pointer for ``do_<command>``        |
    +---------------+---------------+----------------------------------------------+
    | usage         | int           | Pointer to short usage text string           |
    +---------------+---------------+----------------------------------------------+
    | longhelp      | int           | Pointer to longer command description and    |
    |               |               | help text. Only present if U-Boot was built  |
    |               |               | with ``CONFIG_SYS_LONGHELP``                 |
    +---------------+---------------+----------------------------------------------+
    | autocomplete  | int           | Function pointer to autocomplete handler.    |
    |               |               | Only present if U-Boot was built with        |
    |               |               | ``CONFIG_AUTOCOMPLETE``.                     |
    +---------------+---------------+----------------------------------------------+

    The **arch** parameter is required in order to pack the pointer values
    according to the target's endianness.
    """

    ret = bytearray()

    ret += arch.int_to_bytes(entry['name'])
    ret += arch.int_to_bytes(entry['maxargs'])
    ret += arch.int_to_bytes(entry['cmd_rep'])
    ret += arch.int_to_bytes(entry['cmd'])
    ret += arch.int_to_bytes(entry['usage'])

    if 'longhelp' in entry:
        ret += arch.int_to_bytes(entry['longhelp'])

    if 'complete' in entry:
        ret += arch.int_to_bytes(entry['complete'])

    return bytes(ret)
