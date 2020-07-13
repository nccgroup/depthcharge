# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Miscellaneous U-Boot centric conversion and data processing functionality.
"""

import copy
import os
import re

from zlib import crc32

from . import log
from .arch import Architecture
from .operation import OperationFailed

def jump_table_exports(sys_malloc_simple=False):
    """
    Return a list of functions exported in U-Boot's "jump table".
    These are provided in the order they appear in the jump table.

    Each entry is a tuple laid out as follows:

    +----------+-----------+---------------------------------+
    |  Index   |   Type    | Description                     |
    +==========+===========+=================================+
    |    0     |  ``str``  | Function name                   |
    +----------+-----------+---------------------------------+
    |    1     |  ``str``  | Return type                     |
    +----------+-----------+---------------------------------+
    |    2     |  ``list`` | Argument types (each a ``str``) |
    +----------+-----------+---------------------------------+

    Not all functions are necessarily implemented. In most cases, a dummy function is used as a
    placeholder if it is not included by the build configuration. Bear in mind, this This is not
    always true. For example, ``CONFIG_PHY_AQUANTIA`` results in additional items, for which there
    are typically no dummies; these are not included.

    If *sys_malloc_simple=True*, the `free()` function is omitted, per U-Boot's build-time
    ``CONFIG_SYS_MALLOC_SIMPLE`` setting.  This is typically only used when building a U-Boot SPL,
    which usually do not have interactive consoles.
    """
    # flake8: noqa=E501, pylint:disable=line-too-long
    ret = [
        # Name,                 Return Type,        [Argument Types]
        ('get_version',         'unsigned long',    []),
        ('getc',                'int',              []),
        ('tstc',                'int',              []),
        ('putc',                'void',             ['const char']),
        ('puts',                'void',             ['const char *']),
        ('printf',              'int',              ['const char *', 'va_list']),
        ('irq_install_handler', 'void',             ['int', 'void*', 'void *']),
        ('irq_free_handler',    'void',             ['int']),
        ('malloc',              'void *',           ['size_t']),
    ]

    # This entry assumes CONFIG_SYS_MALLOC_SIMPLE is not defined. This is
    # generally only used in an SPL, where we generally don't have an
    # interactive console.
    if not sys_malloc_simple:
        ret +=  [('free',         'void',             ['void *'])]

    ret += [
        ('udelay',              'void',             ['unsigned long']),
        ('get_timer',           'unsigned long',    ['unsigned long']),
        ('vprintf',             'int',              ['const char *', 'va_list']),
        ('do_reset',            'int',              ['void *']),
        ('env_get',             'char  *',          ['const char *']),
        ('env_set',             'int',              ['const char *', 'const char *']),
        ('simple_strtoul',      'unsigned long',    ['const char *', 'const char **', 'unsigned int']),
        ('strict_strtoul',      'int',              ['const char *', 'const char **', 'unsigned int', 'unsigned long *']),
        ('simple_strtol',       'long',             ['const char *', 'const char **', 'unsigned int']),
        ('strcmp',              'int',              ['const char *', 'const char *']),
        ('i2c_write',           'int',              ['unsigned char', 'unsigned int', 'int', 'unsigned char *', 'int']),
        ('i2c_read',            'int',              ['unsigned char', 'unsigned int', 'int', 'unsigned char *', 'int']),
        ('spi_setup_slave',     'void *',           ['uint', 'uint', 'uint', 'uint']),
        ('spi_free_slave',      'void',             ['void *']),
        ('spi_claim_bus',       'int',              ['void *']),
        ('spi_release_bus',     'void',             ['void *']),
        ('spi_xfer',            'int',              ['void *']),
        ('ustrtoul',            'unsigned long',    ['const char *', 'char **', 'unsigned int']),
        ('ustrtoull',           'unsigned long long', ['const char *', 'char **', 'unsigned int']),
        ('strcpy',              'char *',           ['char *', 'const char *']),
        ('mdelay',              'void',             ['unsigned long']),
        ('memset',              'void *',           ['void *', 'int', 'size_t'])

        # CONFIG_PHY_AQUANTIA items omitted - these have no dummies
    ]

    return ret

def _find_new_gd(gd_address: int, gd_mem: bytes, arch):
    """
    Search for global_data.new_gd in `gd_mem` by looking for a
    pointer matching `gd_address`.

    If found, new_gd's offset into `gd_mem` is returned.
    Otherwise a `ValueError` is raised.
    """
    log.debug('Searching for gd->new_gd == 0x{:08x}'.format(gd_address))

    data = gd_mem
    value, data = arch.ptr_value_adv(data)
    offset = arch.word_size
    while data:
        value, data = arch.ptr_value_adv(data)
        if value == gd_address:
            return offset

        offset += arch.word_size

    raise ValueError('Failed to locate gd->new_gd field')


def _find_gd_env_buf(gd_address: int, gd_mem: bytes, new_gd_offset: int, arch):
    """
    Search for `struct global_data.env_buf` in `gd_mem`.

    If found, the offset of this field into `gd_mem` is returned.
    Otherwise a `ValueError` is raised.
    """
    search_offset = new_gd_offset + arch.word_size
    search_addr = gd_address + search_offset
    log.debug('Searching for gd->env_buf[32] @ 0x{:08x}'.format(search_addr))

    valid_count = 0
    env_buf_offset = 0

    for i, value in enumerate(gd_mem):

        # I've only ever seen this contain printable ASCII characters and '\0'
        if value != 0x00 and value not in range(0x20, 0x80):
            valid_count = 0
            continue

        # We expect gd->env_buf[32] to be word-aligned
        if valid_count == 0:
            if not arch.is_aligned(i):
                continue
            env_buf_offset = i

        valid_count += 1
        if valid_count == 32:
            return env_buf_offset

    raise ValueError('Failed to located gd->env_buf[32]')

def _find_extras(gd_mem: bytes, new_gd_offset: int, arch) -> dict:
    """
    Return a dictionary of global data structure fields directly preceding
    the ``struct global_data *new_gd`` field.
    """
    ret = {}

    # struct global data fields preceding struct global_data *new_gd - in reverse,
    # up until the next conditionally-compiled field.
    fields = (
        ('reloc_off',       arch.word_size),
        ('start_addr_sp',   arch.word_size),
        ('irq_sp',          arch.word_size),
        ('mon_len',         arch.word_size),
        ('ram_size',        arch.phys_size),
        ('relocaddr',       arch.word_size),
        ('ram_top',         arch.word_size),

        # TODO: Check U-Boot version and include these if appropriate.
        #       Skipping them for now for compatibility with 2016-era U-Boots
        #       that we keep seeing with i.MX6-based platforms.
        # ('ram_base',        arch.word_size),  # Added 2018-06 in 90c08fa0384
        # ('env_load_prio',   arch.word_size),  # Added 2018-07 in d30ba2315ae
        # ('env_has_init',    arch.word_size),  # Added 2018-01 in 1d4460871b4
        # ('env_valid',       arch.word_size),  # Added 2017-01 in 203e94f6c9c
        # ('env_addr',        arch.word_size),
    )

    off = new_gd_offset

    for name, size in fields:
        off -= size

        if size == arch.phys_size:
            ret[name] = int.from_bytes(gd_mem[off:off+size], arch.endianness)
        else:
            ret[name] = arch.to_uint(gd_mem[off:])

        log.note('Located gd->{:s}. Value: 0x{:08x}'.format(name, ret[name]))

    return ret


def find_jump_table(gd_address, memory_reader, arch, **kwargs) -> dict:
    """
    Search for U-Boot's exported jump table, given the address of the global
    data structure (`gd`), an instance of :py:class:`~depthcharge.memory.MemoryReader`,
    and the architecture of the target.

    Upon success, the returned dictionary will contain the following keys:

    * *address* - Address of the jump table
    * *entries* - List of jump table entries. Each entry is a dict with *name*, *value*, *suffix* keys.
    * *extras*  - Other global data structure information picked up in the process of
                  searching for the jumptable.

    If you already have a `Depthcharge` handle, consider instead invoking its
    :py:meth:`~depthcharge.Depthcharge.uboot_global_data()` method, which will take care of finding
    the location of `gd` and calling this function.
    """

    # This seems to be "good enough" for a majority of devices.
    gd_read_size = kwargs.get('gd_read_size', 256)

    # This is just a sanity check to confirm we're not off in the weeds.
    # If you're running into unexpected failures here, report it and work
    # around it by passing jt_addr_mask=0 in the meantime.
    jt_addr_mask = kwargs.get('jt_addr_mask', 0xfffffffffc000000)

    if not arch.is_aligned(gd_address):
        raise ValueError('Global datastructure address must be word-aligned.')

    if not arch.multiple_of_word_size(gd_read_size):
        raise ValueError("gd_read_size must be a multiple of the architecture's word size")

    msg = 'Reading {:d} bytes of global data structure (gd) to begin search for gd->jt.'
    log.note(msg.format(gd_read_size))
    gd_mem = memory_reader.read(gd_address, gd_read_size)

    # First, locate offset to new_gd structure entry, which we expect to
    # be the same gd value we're using in the post-relocation environment
    new_gd_offset = _find_new_gd(gd_address, gd_mem, arch)
    log.note('Located gd->new_gd @ offset 0x{:x}'.format(new_gd_offset))

    extras = _find_extras(gd_mem, new_gd_offset, arch)

    # From there, look for gd->env_buf as a reliable jt neighbor.
    env_buf_offset = _find_gd_env_buf(gd_address, gd_mem, new_gd_offset, arch)
    log.note('Located gd->env_buf[32] @ 0x{:x}'.format(gd_address + env_buf_offset))

    # gd->jt is the field before env_buf
    expected_masked_addr = gd_address & jt_addr_mask

    jt_offset = env_buf_offset - arch.word_size
    jt_addr   = arch.ptr_value(gd_mem[jt_offset:])
    log.debug('Exported jumptable potentially @ 0x{:08x}'.format(jt_addr))

    # Sanity-check the exlorted jumptable through a naive address mask
    if jt_addr & jt_addr_mask != expected_masked_addr:
        msg = 'Address mask suggests our gd->jt guess (0x{:08x}) may be incorrect.'
        msg += os.linesep
        msg += '    ' + '(We may crash the device when we dereference it.)'
        log.warning(msg.format(jt_addr))

    jt = {}
    jt['address'] = jt_addr
    jt['entries'] = []
    jt['extras'] = extras

    jump_table_entries = jump_table_exports(**kwargs)
    table_size_bytes = len(jump_table_entries) * arch.word_size

    jump_table_data = memory_reader.read(jt_addr, table_size_bytes)

    mask_failures = 0
    for entry in jump_table_entries:
        fn_ptr, jump_table_data = arch.ptr_value_adv(jump_table_data)
        if fn_ptr & jt_addr_mask != expected_masked_addr:
            mask_failures += 1
            msg = '{:s}() function pointer (0x{:08x}) fails address mask check'
            log.warning(msg.format(entry[0], fn_ptr))


        jt['entries'].append(
            {
                'address':      fn_ptr,
                'name':         entry[0],
                'return_type':  entry[1],
                'arg_types':    entry[2]
            }
        )

    # Arbitrary threshold
    if mask_failures > (len(jump_table_entries) / 4):
        msg = 'Too many jump table entries ({:d} / {:d}) failed address mask checks.'
        raise OperationFailed(None, msg.format(mask_failures, len(jump_table_entries)))

    return jt


def cmdtbl_entry_to_bytes(arch, entry: dict) -> bytes:
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


_BDINFO_NUM_REGEX = re.compile((
    r'(?P<name>[\w\d<>\s-]+)'
    r'(=)\s*'
    r'(?P<value>(0x)?[\w\d:\./@#$%-]+)'
    r'\s*'
    r'(?P<suffix>[\w\d-]+)?'
))


def bdinfo_dict(output: str) -> dict:
    """
    Convert output of U-Boot's *bdinfo* command to a dictionary.

    Technically, each item may come from a variety of locations,
    whether it be *gd*, *gd->bd*, or another structure.

    However, we'll just return everything in a single dict
    out of laziness.
    """
    ret = {}

    for line in output.splitlines():
        match = _BDINFO_NUM_REGEX.match(line)
        if not match:
            log.debug('Skipping unmatched bdinfo item: ' + line)
            continue

        try:
            name    = match.group('name').strip()
            value   = match.group('value').strip()
            suffix  = match.group('suffix') or ''

            # Fixup some known formatting
            if 'drambank' in ret:
                name = name.replace('->', 'DRAM bank')

            try:
                value = int(value, 0)
            except ValueError:
                # Try to move forward with it as-is
                pass

            # Variable names in gd->bd tend to be mached up in one word,
            # Try to follow that convention...
            key  = name.replace(' ', '').lower()
            ret[key] = { 'name': name, 'value': value, 'suffix': suffix }

        except (AttributeError, IndexError):
            log.error('Failed to parse line: ' + match.group())

    return ret


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


def expand_environment(env: dict, **kwargs) -> dict:
    """
    Return a copy of the provided U-Boot environment variable dictionary with all
    variable definitions fully resolved.

    This function supports the same keyword arguments as :py:func:`expand_variable()`.
    """
    ret = copy.deepcopy(env)

    for var in env:
        ret[var] = expand_variable(env, var, **kwargs)

    return ret

_ENV_VAR_PAT = b'(?P<name>[\x20-\x3c\x3d-\x7f]+)=(?P<value>[\x20-\x7f]+)\x00'

def raw_environment_regex(min_entries: int = 5, max_entries: int = None):
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


def raw_env_var_regex():
    """
    Return a compiled regular expression that can be used to match an
    environment variable definition in a binary.

    If you haven't already, consider using :py:class:`~depthcharge.hunter.EnvironmentHunter`
    instead, as this may already do everything you're looking to implement.
    """
    return re.compile(b'(?P<name>[\x20-\x3c\x3e-\x7f]+)=(?P<value>[\x09\x0a\x0d\x20-\x7f]+)\x00')


def parse_raw_environment(data: bytes) -> dict:
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
    regex = raw_env_var_regex()
    for match in regex.finditer(data):
        name = match.group('name').decode('ascii')
        value = match.group('value').decode('ascii')
        results[name] = value

    if not results:
        raise ValueError('No environment variables found')

    return results

def load_raw_environment(filename: str, arch: str, has_crc=True, has_flags=False) -> tuple:
    """
    Load an environment previously carved from a binary or saved with
    :py:func:`save_raw_environment()`. It is returned as a tuple: ``(env: dict, metadata: dict)``

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
    env = parse_raw_environment(data)
    return (env, metadata)


def save_raw_environment(filename: str, env: dict, size: int, arch: str, flags: int = None, no_header=False):
    """
    Convert the environment information stored in *env* and save it to *filename*.

    Refer to :py:func:`create_raw_environment` for more information about this function's arguments.
    """
    env_data = create_raw_environment(env, size, arch, flags, no_header)
    with open(filename, 'wb') as outfile:
        outfile.write(env_data)


def create_raw_environment(env: dict, size: int, arch: str, flags: int = None, no_header=False) -> bytes:
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
    `CONFIG_SYS_REDUNDAND_ENV <https://gitlab.denx.de/u-boot/u-boot/-/blob/v2020.04/env/Kconfig#L394>`_
    (sic) option.  This option enables the use of two environment copies, should
    one become corrupted during the programming operation (e.g. via unexpected power-loss).
    Although called "flags", it's basically a monotonic modulo-256 counter that's incremented
    by one at each write to denote the freshest copy. (See `env/common.c
    <https://gitlab.denx.de/u-boot/u-boot/-/blob/v2020.04/env/common.c#L181>`_)

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

def parse_environment(text: str) -> dict:
    """
    Parse the contents of the environment contained in the provided *text* and
    return the environment as a dictionary.

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

            delim_idx = line.index('=')

            name  = line[:delim_idx]
            value = line[delim_idx+1:]

            results[name] = value

            prev_name = name
            expect_continuation = value.endswith('\\')

    if not results:
        raise ValueError('No environment variables found')

    return results

def load_environment(filename: str) -> dict:
    """
    Load a U-Boot environment from a text file and return it as a dictionary.

    A :py:exc:`ValueError` is raised if no environment variables are found.
    """
    with open(filename, 'r') as infile:
        text = infile.read()
        return parse_environment(text)

def save_environment(filename:str, env: dict):
    """
    Write the contents of an environment to a text file that can later
    be loaded via :py:func:load_environment()`.
    """
    with open(filename, 'w') as outfile:
        for name in sorted(env.keys()):
            value = env[name]
            outfile.write(name + '=' + value + os.linesep)
