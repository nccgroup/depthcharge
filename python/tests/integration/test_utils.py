# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
"""
Utility functions for integration tests
"""

import json
import random
import time

from os      import makedirs, path
from os.path import dirname, realpath

from depthcharge import log

_THIS_DIR = dirname(realpath(__file__))


def create_resource_dir(test_dir, test_subdir='') -> str:
    """
    Create a test-specific resource directory and subdirectory.

    The resulting path is returned.
    """
    resource_dir = path.join(_THIS_DIR, 'resources', test_dir, test_subdir)
    makedirs(resource_dir, 0o770, exist_ok=True)
    return resource_dir


def load_resource(filename: str, load_file_func, test_dir='', test_subdir='', msg_pfx=''):
    """
    Load a resource file a test-specific specific directory and subdirectory.

    `load_file_func` should take a single filename argument. This function
    returns that of `load_file_func()`.
    """
    resource_dir = create_resource_dir(test_dir, test_subdir)

    file_path = path.join(resource_dir, filename)
    ret = load_file_func(file_path)

    if msg_pfx is not None:
        if msg_pfx == '':
            msg_pfx = 'Loaded resource from prior test: {:s}'
        log.note(msg_pfx.format(file_path))

    return ret


def save_resource(filename: str, save_file_func, test_dir='', test_subdir='', msg_pfx=''):
    """
    Save a resource to a test-specific directory and subdirectory.

    This mirrors the usage of load_resource().
    """
    # Just wrapping a more sensible name - it ends up being the same for now
    msg_pfx = 'Saving resource for future tests: {:s}'
    load_resource(filename, save_file_func, test_dir, test_subdir, msg_pfx=msg_pfx)


def random_pattern(size: int, seed: int = 0) -> bytes:
    """
    Return `size` random bytes.
    """
    ret = bytearray(size)
    random.seed(seed)
    for i in range(0, size):
        ret[i] = random.randint(0, 255)
    return bytes(ret)


def decrementing_pattern(size: int) -> bytes:
    """
    Return `size` bytes with a pattern of decrementing byte values.
    """
    ret = bytearray(size)
    for i in range(size - 1, -1, -1):
        ret[i] = i & 0xff
    return bytes(ret)


def incrementing_pattern(size: int) -> bytes:
    """
    Return `size` bytes with a pattern of incrementing byte values.
    """
    ret = bytearray(size)
    for i in range(0, size):
        ret[i] = i & 0xff
    return bytes(ret)


def now_str() -> str:
    """
    Return the current time in seconds since the Unix Epoch.
    """
    return str(int(time.time()))


def load_file(filename: str, mode='r'):
    """
    Open a file and return its contents.
    Return type depends on whether the mode is 'r' or 'rb'.
    """
    with open(filename, mode) as infile:
        return infile.read()


def save_file(filename: str, data, mode='w'):
    """
    Write data to the specified file.
    """
    with open(filename, mode) as outfile:
        outfile.write(data)


def load_config(filename: str) -> dict:
    """
    Load a Depthcharge device configuration file and return its corresponding
    dictionary representation.
    """
    return json.loads(load_file(filename))
