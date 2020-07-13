# SPDX-License-Identifier: BSD-3-Clause
"""
Miscelaneous utility functions for unit tests.
"""
import random
import sys


def random_data(size: int, seed=0, ret_bytes=False):
    """
    Return `size` pseudorandom bytes from the random module, seeded by `seed`.

    By default, a `bytearray` is returned. If `ret_bytes=True`,
    `bytes` are returned.
    """
    random.seed(seed)
    ret = random.getrandbits(size * 8).to_bytes(size, sys.byteorder)
    if ret_bytes:
        return ret

    return bytearray(ret)
