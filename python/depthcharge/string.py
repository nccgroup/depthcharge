# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Miscellaneous string conversion and parsing functions
"""

import os
import re
import sys

# Uppercase'd for case-insensitivity
_BYTE_LENGTH_SUFFIXES = {
    'KB':   1000,
    'K':    1024,
    'KIB':  1024,
    'MB':   1000 * 1000,
    'M':    1024 * 1024,
    'MIB':  1024 * 1024,
    'GB':   1000 * 1000 * 1000,
    'G':    1024 * 1024 * 1024,
    'GiB':  1024 * 1024 * 1024,
}


def to_positive_int(string: str, string_desc='', exit_on_fail=True) -> int:
    """
    Convert a string to a postive integer and optionally:

    * Print ``'Invalid <string_desc> value: <string>'`` to  *sys.stderr*.
    * Exit the program with a return code value of 2.

    """

    try:
        ret = int(string, 0)
        if ret < 0:
            raise ValueError('Value cannot be negative. Got: ' + string)
        return ret

    except ValueError as e:
        if string_desc:
            print('Invalid ' + string_desc + ' value: ' + string, file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)

        if exit_on_fail:
            sys.exit(2)


def length_to_int(len_str: str, desc='length', exit_on_fail=True) -> int:
    """
    Convert a numeric string with one of the following (case insensitive) length suffixes
    into its corresponding integer representation.

    +-----------+---------------------------+
    |   Suffix  | Multiplication Factor     |
    +===========+===========================+
    |     kB    | 1,000                     |
    +-----------+---------------------------+
    |  K or KiB | 1,024                     |
    +-----------+---------------------------+
    |     MB    | 1,000,000 (1,000 ^ 2)     |
    +-----------+---------------------------+
    |  M or MiB | 1,048,576 (1,024 ^ 2)     |
    +-----------+---------------------------+
    |     GB    | 1,000,000,000 (1,000 ^ 3) |
    +-----------+---------------------------+
    |  G or GiB | 1,073,741,824 (1,024 ^ 3) |
    +-----------+---------------------------+

    """
    try:
        # No suffix? No problem.
        return int(len_str, 0)
    except ValueError:
        # Otherwise we'll handle it
        pass

    _len_str = len_str.replace(' ', '').upper()

    for suffix in _BYTE_LENGTH_SUFFIXES:
        if _len_str.endswith(suffix):
            factor = _BYTE_LENGTH_SUFFIXES[suffix]
            val_str = _len_str[:-len(suffix)]
            value = to_positive_int(val_str, desc, exit_on_fail)
            return value * factor

    raise ValueError('Invalid ' + desc + ': ' + len_str)


def keyval_list_to_dict(arg_list: list) -> dict:
    """
    Helper routine for converting command line argument strings in the form
    ``'key1=val1,key2=val2,...'`` into a dictionary suitable for
    passing to a function as ``**kwargs``.

    If a key is specified in the string with no value, it is assigned a value of ``True``.

    It is the responsibility of the caller or code consuming the diectionary to validate the types
    and values of the dictionary entries.
    """
    arg_dict = {}
    for arg in arg_list:
        keyvals = arg.split(',')
        for keyval in keyvals:
            fields = keyval.split('=')
            if len(fields) in (1, 2):
                key = fields[0].strip()

                if len(fields) == 1:
                    # Just a boolean setting
                    arg_dict[key] = True
                else:
                    # Attempt to interpret integer setting values
                    value = fields[1].strip()
                    try:
                        arg_dict[key] = int(value, 0)
                    except ValueError:
                        arg_dict[key] = value
            else:
                keyval = '<empty>' if len(keyval) == 0 else keyval
                err = 'Invalid argument. Expected key=val syntax: ' + keyval
                raise ValueError(err)

    return arg_dict


def str_to_property_keyval(arg: str) -> tuple:
    """
    Helper routine for converting a command-line argument string in the form:

        ``'<property>[:<key>=<value>][,<key>=<value>][...]'``

    to a tuple containing a property string and a dictionary:

        ``('<property>', {<key>: <value>, ... })``

    The returned tuple will contain an empty dictionary if
    the provided argument does not contain a key-value list.

    If keys are provided without corresponding values, they will be assigned
    a value of ``True``.

    """
    try:
        separator_idx = arg.index(':')
    except ValueError:
        return (arg, {})

    main_item = arg[:separator_idx].strip()
    keyval_str = arg[separator_idx + 1:]
    keyval_list = keyval_str.split(',')
    return (main_item, keyval_list_to_dict(keyval_list))


def xxd(address, data: bytes) -> str:
    """
    Return the provided *data* as a hex dump formatted in the style of
    ``xxd -g1 <filename>``.  The provided *address* value will be the
    base address in the hex dump.
    """
    ret = ''

    c = 0
    linebuf = bytearray()
    for i, value in enumerate(data):
        if c == 0:
            ret += '{:08x}: '.format(address + i)

        ret += '{:02x} '.format(value)
        linebuf.append(value)

        if c == 15:
            ret += ' '
            for j in linebuf:
                if 0x20 <= j < 0x7f:
                    ret += chr(j)
                else:
                    ret += '.'
            linebuf.clear()
            if i != (len(data)-1):
                ret += os.linesep

        c = (c + 1) & 0xf

    # Did not end on a 16-byte boundary
    n_empty = 16 - len(linebuf)
    if n_empty < 16:
        ret += '   ' * n_empty
        ret += ' '
        for j in linebuf:
            if 0x20 <= j < 0x7f:
                ret += chr(j)
            else:
                ret += '.'

    return ret


_XXD_REGEX = re.compile(
    r'(?P<addr>[0-9a-fA-F]{8,}):\s*'
    r'(?P<data>([0-9a-fA-F]{2}\s?){1,16})'
)


def xxd_reverse(hexdump: str) -> tuple:
    """
    Convert a well-formed hexdump produced by the :py:func:`xxd()` function
    back into bytes. (i.e., no formatting error recovery is guaranteed.)

    Returns a tuple: ``(address: int, data: bytes)``

    """
    address = None
    data = bytearray()

    for line in hexdump.splitlines():
        # Skip empty lines if we encounter them
        line = line.strip()
        if not line:
            continue

        m = _XXD_REGEX.match(line)
        if not m:
            raise ValueError('Encountered malformd line: ' + line)

        if address is None:
            address = int(m.group('addr'), 16)

        data += bytes.fromhex(m.group('data'))

    return (address, data)


def xxd_reverse_file(filename: str) -> tuple:
    """
    Load the binary data in the specified file and invoke
    :py:func:`xxd_reverse()` on the contents.

    Returns a tuple: ``(address: int, data: bytes)``
    """
    with open(filename, 'r') as infile:
        hex_dump = infile.read()

    return xxd_reverse(hex_dump)
