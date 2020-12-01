# SPDX-License-Identifier: BSD-3-Clause
"""
Miscelaneous utility functions for unit tests.
"""
import hashlib
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


def verify_md5sum(filename: str, expected: str, test_case):
    """
    Invokes ``test_case.assertEqual()`` with loaded file's checksum
    and the expected value (as hex strings), in that order.
    """
    with open(filename, 'rb') as infile:
        data = infile.read()
        md5sum = hashlib.new('md5')
        md5sum.update(data)
        test_case.assertEqual(md5sum.hexdigest(), expected)
