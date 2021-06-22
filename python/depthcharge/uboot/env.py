# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
U-Boot environment variable parsing and handling functionality
"""

import copy
import os
import re

from zlib import crc32

from .. import log
from ..arch import Architecture

# This is a bit bonkers because U-Boot let's you run pretty wild with
# your variable naming...
#
# Here's a few examples to ruin your day:
#   setenv ' ' true
#   setenv '' :)
#   setenv '\$ foo' 'bar ${ }'
#   setenv '\$\{bar\} ' 'run echo ${\$ foo}'
#   setenv '\$omg \$stahp\}' \#cursed
#   setenv \{test\$\{test 42
#
# See U-Boot's lib/hashtable.c for name handling.

_VAR_NAME_RE = re.compile(r"""
    \$\{(.*?)\}|           # ${foo}
    \$([^\$\s\{][^\$\s]*)  # $bar
""", re.VERBOSE)


# Representation of an environment variable stored in NV memory
_ENV_VAR_PAT = b'(?P<name>[\x20-\x3c\x3d-\x7f]+)=(?P<value>[\x20-\x7f]+)\x00'


def raw_regex(min_entries: int = 5, max_entries: int = None):
    """
    Return a compiled regular expression for locating a U-Boot environment
    in a binary. This does not include ``env_t`` metadata, such as the
    environment's CRC32 word and optional flags byte.

    The *min_entries* and *max_entries* parameters can be used to bound
    the size (in number of entries) of the environment to be matched.

    If you haven't already, consider using :py:class:`~depthcharge.hunter.EnvironmentHunter`
    instead, as this may already do everything you're looking to implement.
    """
    min_entries = min_entries or ''
    max_entries = max_entries or ''

    pattern = b'(' + _ENV_VAR_PAT + b'){'
    pattern += str(min_entries).encode('ascii')
    pattern += b','
    pattern += str(max_entries).encode('ascii')
    pattern += b'}'

    return re.compile(pattern)


def raw_var_regex():
    """
    Return a compiled regular expression that can be used to match an
    environment variable definition in a binary.

    If you haven't already, consider using :py:class:`~depthcharge.hunter.EnvironmentHunter`
    instead, as this may already do everything you're looking to implement.
    """
    return re.compile(b'(?P<name>[\x20-\x3c\x3e-\x7f]+)=(?P<value>[\x09\x0a\x0d\x20-\x7f]+)\x00')


def parse(text: str) -> dict:
    """
    Parse the contents of the environment contained in the provided *text*
    (e.g. obtained through the console interface) and return the environment as
    a dictionary.

    A :py:exc:`ValueError` is raised if no environment variables are found.
    """
    results = {}
    prev_name = None
    expect_continuation = False

    for line in text.splitlines():

        if expect_continuation:
            results[prev_name] += os.linesep + line
            expect_continuation = line.endswith('\\')
        else:
            if not line or line.startswith('Environment size: '):
                continue

            try:
                delim_idx = line.index('=')
            except ValueError:
                # Try to be resilient and ignore bizzare or malformed lines...
                continue

            name  = line[:delim_idx]
            value = line[delim_idx+1:]

            results[name] = value

            prev_name = name
            expect_continuation = value.endswith('\\')

    if not results:
        raise ValueError('No environment variables found')

    return results


def expand_variable(env: dict, to_expand: str, **kwargs) -> str:
    """
    Return the environment variable named *to_expand* with all variable definitions
    contained within it fully expanded.

    A :py:exc:`KeyError` is raised if *to_expand* is not present in the provided
    *env* dictionary.

    **Optional Keyword Arguments**:

        *limit* - Maximum expansion iterations to peform. Default: ``100``

        *warn_only* - Print a warning, but do not raise an exception, if the variable definition
        cannot be fully expended due to an undefined environment variable.  This situtaion is
        possibly indicative of an issue with the U-Boot environment itself, rather than Depthcharge
        or anything the user has done incorrectly; it may be the case that some incomplete
        development cruft or reference design vestiges are present in the environment. If this
        occurs and this setting is set to ``False``, a :py:exc:`ValueError` will be raised.
        Default: ``True``

        *quiet* - Suppress the above warning. (Requires *warn_only=True*.)

    """
    result = None

    limit = kwargs.get('limit', 100)
    warn_only = kwargs.get('warn_only', True)
    quiet = kwargs.get('quiet', False)

    value = env[to_expand]
    for _ in range(0, limit):
        prev = value

        for match in _VAR_NAME_RE.finditer(value):
            var_name = match.group(1) or match.group(2)
            if var_name in env:
                expansion = env[var_name]

                if match.group(1):
                    value = value.replace('${' + var_name + '}',  expansion)
                else:
                    value = value.replace('$' + var_name,  expansion)

        if prev == value:
            result = value
            break

    if result is None:
        raise ValueError('Expansion iteration limit reached')

    # Are there any unexpanded definitions remaining?
    match = _VAR_NAME_RE.search(value)
    if match:
        var_name = match.group(1) or match.group(2)
        msg = 'No definition for environment variable "{:s}" found when expanding "{:s}"'
        msg = msg.format(var_name, to_expand)
        if warn_only:
            if not quiet:
                log.warning(msg)
        else:
            raise ValueError(msg)

    return result


def expand(env: dict, **kwargs) -> dict:
    """
    Return a copy of the provided U-Boot environment variable dictionary with all
    variable definitions fully resolved.

    This function supports the same keyword arguments as :py:func:`expand_variable()`.
    """
    ret = copy.deepcopy(env)

    for var in env:
        ret[var] = expand_variable(env, var, **kwargs)

    return ret


def parse_raw(data: bytes) -> dict:
    """
    Parse the contents of an environment retrieved from flash or memory
    and provide an equivalent dictionary.

    The provided *data* should being at the start of the variable definitions.
    It **must not** contain the ``env_t`` metadata, such as the CRC32 word
    and the ``flags`` value (only present when compiled with
    "``CONFIG_SYS_REDUNDAND_ENVIRONMENT``".

    A :py:exc:`ValueError` is raised if no environment variables are found.
    """
    results = {}
    regex = raw_var_regex()
    for match in regex.finditer(data):
        name = match.group('name').decode('ascii')
        value = match.group('value').decode('ascii')
        results[name] = value

    if not results:
        raise ValueError('No environment variables found')

    return results


def load(filename: str) -> dict:
    """
    Load a U-Boot environment from a text file and return it as a dictionary.

    The text file is expected to be in the same format as that used by U-Boot's
    ``printenv`` command output.

    A :py:exc:`ValueError` is raised if no environment variables are found.
    """
    with open(filename, 'r') as infile:
        text = infile.read()
        return parse(text)


def load_raw(filename: str, arch: str, has_crc=True, has_flags=False) -> tuple:
    """
    Load an environment previously carved from a binary or saved with
    :py:func:`save_raw()`. It is returned as a tuple: ``(env: dict, metadata: dict)``

    This function expects the environment (metadata) to begin at offset 0 in
    the opened file. The name of the target architecture (*arch*) must be
    provided.

    The *has_crc* and *has_flags* boolean parameters should be used to
    specify whether the file contains a U-Boot env_t header.
    """
    with open(filename, 'rb') as infile:
        data = infile.read()

    metadata = {}

    start = 0
    if has_crc:
        arch = Architecture.get(arch)
        crc = int.from_bytes(data[0:4], arch.endianness)
        start += 4

        metadata['crc'] = crc

        if has_flags:
            metadata['flags'] = data[start]
            start += 1

        data = data[start:]
        metadata['actual_crc'] = crc32(data)

    metadata['size'] = len(data)
    env = parse_raw(data)
    return (env, metadata)


def save(filename: str, env: dict):
    """
    Write the contents of an environment to a text file that can later
    be loaded via :py:func:load()`.
    """
    with open(filename, 'w') as outfile:
        for name in sorted(env.keys()):
            value = env[name]
            outfile.write(name + '=' + value + os.linesep)


def save_raw(filename: str, env: dict, size: int, arch: str, flags: int = None, no_header=False):
    """
    Convert the environment information stored in *env* and save it to *filename*.

    Refer to :py:func:`create_raw_environment` for more information about this function's arguments.
    """
    env_data = create_raw(env, size, arch, flags, no_header)
    with open(filename, 'wb') as outfile:
        outfile.write(env_data)


def create_raw(env: dict, size: int, arch: str, flags: int = None, no_header=False) -> bytes:
    """
    Convert the environment contained the *env* dictionary to the binary format that can be used to
    replace an environment in non-volatile storage.

    The *size* parameter must match the target's compile-time ``CONFIG_ENV_SIZE`` definition.
    The environment is zero-padded to this length prior to the computation of its CRC32
    checksum. If you don't know this value and can extract flash contents, you can use
    :py:class:`~depthcharge.hunter.EnvironmentHunter` to locate environment instances. The ``src_size``
    entry in the results for of :py:meth:`~depthcharge.hunter.EnvironmentHunter.find()`
    and :py:meth:`~depthcharge.hunter.EnvironmentHunter.finditer()` correspond to this size.

    The *arch* parameter must name the target architecture that will be processing the environment.

    Finally, an optional *flags* value can be provided. This is an ``env_t``
    structure field present only when U-Boot is compiled with the
    `CONFIG_SYS_REDUNDAND_ENV <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/env/Kconfig#L394>`_
    (sic) option.  This option enables the use of two environment copies, should
    one become corrupted during the programming operation (e.g. via unexpected power-loss).
    Although called "flags", it's basically a monotonic modulo-256 counter that's incremented
    by one at each write to denote the freshest copy. (See `env/common.c
    <https://source.denx.de/u-boot/u-boot/-/blob/v2020.04/env/common.c#L181>`_)

    If you are replacing an environment that uses this feature, be sure to provide either the same
    *flags* value or a greater value.

    Setting *no_header=True* will create the environment contents without any header metadata
    (i.e., no CRC word, no flags).
    """
    ret = bytearray()

    endianness = Architecture.get(arch).endianness
    env_bin = b''
    for name in sorted(env.keys()):
        env_bin += name.encode('ascii')
        env_bin += b'='
        env_bin += env[name].encode('ascii')
        env_bin += b'\x00'

    padding = size - len(env_bin)
    if no_header is False:
        padding -= 4  # CRC word

        if flags is not None:
            padding -= 1

    if padding < 0:
        msg = 'Environment contents ({:d} bytes) exceed storage size ({:d} bytes)'
        raise ValueError(msg.format(len(env_bin) - padding, size))

    env_bin += b'\x00' * padding

    crc_bytes = crc32(env_bin).to_bytes(4, endianness)

    if no_header is not True:
        ret += crc_bytes

        if flags is not None:
            ret += flags.to_bytes(1, 'big')

    ret += env_bin
    return bytes(ret)
