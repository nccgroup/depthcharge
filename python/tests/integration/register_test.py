#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=redefined-outer-name,missing-function-docstring,invalid-name
# pylint: disable=global-statement # (Like salt and sugar; fine if used sparingly)

"""
Exercise all available RegisterReader operations for a platform.
"""

import os
import sys

from depthcharge.cmdline import ArgumentParser, create_depthcharge_ctx


def perform_reads(ctx) -> list:
    reg = ctx.arch.gd_register
    results = []

    # Get ground truth with default reader.
    expected_value = ctx.read_register(reg)

    for impl in ctx.register_readers:
        value = impl.read(reg)
        success = value == expected_value
        results.append((impl.name, value, success))

    return results


def print_results(results):
    total = len(results)
    n_pass = 0

    print()
    print(' RegisterReader                     Value      Pass/Fail')
    print('---------------------------------------------------------')

    for result in results:
        if result[2]:
            state = 'Pass'
            n_pass += 1
        else:
            state = 'Fail'

        line = ' {:32s} 0x{:08x}     {:s}'
        print(line.format(result[0], result[1], state))

    summary = os.linesep + '{:d} Tested, {:d} passed.' + os.linesep
    print(summary.format(total, n_pass))

    return n_pass == total


if __name__ == '__main__':
    success = False
    cmdline = ArgumentParser()
    args = cmdline.parse_args()
    ctx = create_depthcharge_ctx(args)

    if args.config:
        ctx.save(args.config)

    try:
        results = perform_reads(ctx)
        success = print_results(results)

    finally:
        if args.config:
            ctx.save(args.config)

    if not success:
        sys.exit(2)
