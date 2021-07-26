# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Definitions corresponding to U-Boot's exported Jump Table
"""

import os

from .. import log

def exports(sys_malloc_simple=False) -> list:
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

    for i, value in enumerate(gd_mem[search_offset:]):

        # I've only ever seen this contain printable ASCII characters and '\0'
        if value != 0x00 and value not in range(0x20, 0x80):
            valid_count = 0
            continue

        # We expect gd->env_buf[32] to be word-aligned
        if valid_count == 0:
            if not arch.is_word_aligned(i):
                continue
            env_buf_offset = i

        valid_count += 1
        if valid_count == 32:
            return env_buf_offset + search_offset

    raise ValueError('Failed to located gd->env_buf[32]')

def _find_extras(gd_mem: bytes, new_gd_offset: int, arch) -> dict:
    """
    Return a dictionary of global data structure fields directly preceding
    the ``struct global_data *new_gd`` field.
    """
    ret = {}

    # struct global data fields preceding struct global_data *new_gd - in reverse,
    # up until the next conditionally-compiled field.
    #
    # FIXME: If CONFIG_SYS_MEM_RESERVE_SECURE (e.g. in v2016.v03) is set, then
    # we would misinterpret secure_ram as ram_size, and so forth.
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


def find(gd_address, memory_reader, arch, **kwargs) -> dict:
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
    gd_read_size = kwargs.get('gd_read_size', 384)

    # This is just a sanity check to confirm we're not off in the weeds.
    # If you're running into unexpected failures here, report it and work
    # around it by passing jt_addr_mask=0 in the meantime.
    jt_addr_mask = kwargs.get('jt_addr_mask', 0xfffffffffc000000)

    if not arch.is_word_aligned(gd_address):
        raise ValueError('Global datastructure address must be word-aligned.')

    if not arch.multiple_of_word_size(gd_read_size):
        raise ValueError("gd_read_size must be a multiple of the architecture's word size")

    msg = 'Reading {:d} bytes of global data structure (gd) to begin search for gd->jt.'
    log.note(msg.format(gd_read_size))
    gd_mem = memory_reader.read(gd_address, gd_read_size)

    # First, locate offset to new_gd structure entry, which we expect to
    # be the same gd value we're using in the post-relocation environment
    new_gd_offset = _find_new_gd(gd_address, gd_mem, arch)
    new_gd_addr = gd_address + new_gd_offset
    log.note('Located gd->new_gd @ 0x{:x} = gd + 0x{:x}'.format(new_gd_addr, new_gd_offset))

    extras = _find_extras(gd_mem, new_gd_offset, arch)

    # From there, look for gd->env_buf as a reliable jt neighbor.
    env_buf_offset = _find_gd_env_buf(gd_address, gd_mem, new_gd_offset, arch)
    log.note('Located gd->env_buf[32] @ 0x{:x}'.format(gd_address + env_buf_offset))

    # This address mask check is just intended to provided early warning if
    # our function pointer deductions are incorrect, which will lead to a crash.
    #
    # We'll try to use U-Boot's post relocation address as the basis for our check,
    # followed by the gd address if the former somehow isn't present. On many devices,
    # using either here seems to suffice. However, I found that on an AARCH64 AMLogic device
    # using a fork from 2015, the gd was at 0xd3e2.... whereas the relocaddr was 0xd7e3...,
    # which was more representative of the jump table entries @ 0xd7e9....
    check_addr = extras.get('relocaddr', gd_address)
    expected_masked_addr = check_addr & jt_addr_mask

    # gd->jt is the field before env_buf
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

    jump_table_entries = exports(**kwargs)
    table_size_bytes = len(jump_table_entries) * arch.word_size

    jump_table_data = memory_reader.read(jt_addr, table_size_bytes)

    mask_failures = 0
    for entry in jump_table_entries:
        fn_ptr, jump_table_data = arch.ptr_value_adv(jump_table_data)
        if fn_ptr & jt_addr_mask != expected_masked_addr:
            mask_failures += 1
            msg = '{:s}() function pointer (0x{:08x}) failed mask check - may be incorrect.'
            msg += os.linesep
            msg += '    ' + '(We may crash the device when we dereference it.)'
            log.warning(msg.format(entry[0], fn_ptr))


        jt['entries'].append(
            {
                'address':      fn_ptr,
                'name':         entry[0],
                'return_type':  entry[1],
                'arg_types':    entry[2]
            }
        )

    return jt
