#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=redefined-outer-name,missing-function-docstring,invalid-name
# pylint: disable=global-statement # (Like salt and sugar; fine if used sparingly)
"""
Exercise all available MemoryReader and MemoryWriter operations for a platform.
"""
import sys
import time

import datetime
import os
from os import linesep
from os.path import basename

from depthcharge import log, OperationAlignmentError, Stratagem, StratagemCreationFailed
from depthcharge.cmdline import ArgumentParser, create_depthcharge_ctx
from depthcharge.memory import StratagemMemoryWriter, DataAbortMemoryReader

from test_utils import (load_resource, save_resource, create_resource_dir,
                        random_pattern, decrementing_pattern, incrementing_pattern)

SIZES           = (4, 32, 33, 34, 36, 128)
PATTERNS        = (incrementing_pattern, decrementing_pattern, random_pattern)

STRATAGEM_DATA          = random_pattern(16384, seed=1)
STRATAGEM_DATA_OFF      = 1 * 1024 * 1024
_STRATAGEM_DATA_LOADED  = False


def test_cases():
    pattern_idx = 0
    for size in SIZES:
        pattern = PATTERNS[pattern_idx]
        pattern_idx = (pattern_idx + 1) % len(PATTERNS)
        data = pattern(size)
        yield (data, pattern.__name__)


def setup_stratagem(ctx, data, pattern_name, writer):
    global _STRATAGEM_DATA_LOADED

    stratagem_input_data_addr = address + STRATAGEM_DATA_OFF

    # Only need to load the input data once
    if not _STRATAGEM_DATA_LOADED:
        log.info('Loading Stratagem input data.')
        ctx.write_memory(stratagem_input_data_addr, STRATAGEM_DATA)
        _STRATAGEM_DATA_LOADED = True

    had_resource = False
    filename = '{:s}.0x{:08x}.{:d}.stratagem'.format(pattern_name, address, len(data))
    try:
        stratagem = load_resource(filename, Stratagem.from_json_file, 'memory_test', writer.name)
        had_resource = True
    except FileNotFoundError:
        hunter = writer.stratagem_hunter(STRATAGEM_DATA, stratagem_input_data_addr, revlut_maxlen=1024)
        stratagem = hunter.build_stratagem(data)

    if not had_resource:
        save_resource(filename, stratagem.to_json_file, 'memory_test', writer.name)

    return stratagem


# Pre-allocate dict so we can pass to constructor at context-creation time
_da_read_pre_info = {}


def _da_read_pre_func(address: int, size: int, pre_info):
    impl = pre_info['writer']
    offset = address - pre_info['address']
    to_write = pre_info['data'][offset:offset + size]
    impl.write(address, to_write)


def run_test(ctx, reader, writer, address, data, stratagem):
    # Just to avoid triggering our warning to users
    wr_data = data if stratagem is None else None

    if not isinstance(reader, DataAbortMemoryReader):
        ctx.write_memory(address, wr_data, impl=writer, stratagem=stratagem)
    else:
        _da_read_pre_info['writer'] = writer
        _da_read_pre_info['data'] = data
        _da_read_pre_info['address'] = address

    data_read = ctx.read_memory(address, len(data), impl=reader)

    if data != data_read:
        now = round(time.time())
        wfile = '{}.{}.bin'.format(writer.name, now)
        rfile = '{}.{}.bin'.format(reader.name, now)

        msg  = 'Test case failed. Saving written and readback data to:' + linesep
        msg += '      {} and {}'.format(wfile, rfile)
        log.error(msg)

        fail_dir = create_resource_dir('memory_test', 'failure')
        filename = os.path.join(fail_dir, wfile)

        with open(filename, 'wb') as outfile:
            outfile.write(data)

        filename = os.path.join(fail_dir, rfile)
        with open(filename, 'wb') as outfile:
            outfile.write(data_read)

        return 'Fail'

    return 'Pass'


def run_tests(ctx, reader, writer, address):
    report = []
    log.info('  Currently testing: {} / {}'.format(reader.name, writer.name))

    for (data, pattern_name) in test_cases():
        try:
            if isinstance(writer, StratagemMemoryWriter):
                stratagem = setup_stratagem(ctx, data, pattern_name, writer)
                msg = '    Using {:d}-entry stratagem for {:d}-byte payload with {:s}'
                msg = msg.format(len(stratagem), len(data), pattern_name.replace('_', ' '))
            else:
                msg = '    Using {:d}-byte payload with {:s}'
                msg = msg.format(len(data), pattern_name.replace('_', ' '))
                stratagem = None

            log.note(msg)
            result = run_test(ctx, reader, writer, address, data, stratagem)
        except (StratagemCreationFailed, OperationAlignmentError):
            result = 'Skipped (Alignment)'
        entry = {'size': len(data), 'pattern': pattern_name, 'status': result}
        report.append(entry)

    return report


def print_report(report, t_elapsed, uboot_version, config):
    config = '<none>' if config is None else basename(config)

    report_header  = linesep + 'Test Report: {:s}' + linesep
    report_header += ' Config: ' + config + linesep
    report_header += ' Run on: ' + datetime.datetime.now().isoformat() + linesep
    report_header += ' Target: ' + uboot_version + linesep
    report_header += '=' * 72 + linesep

    report_footer  = '=' * 72 + linesep
    report_footer += '{:d} tests run. '
    report_footer += '{:d} passed, {:d} failed. '
    report_footer += 'Elapsed time: ' + str(datetime.timedelta(seconds=t_elapsed))
    report_footer += linesep

    total_tests = 0
    total_tests_passed = 0
    total_tests_failed = 0

    report_body = ''

    for test_name, results in report.items():
        test_header  = '  {:40s} {:s}' + linesep
        test_header += '  ' + '-' * 70 + linesep

        n_pass = 0
        n_skip = 0
        n_fail = 0

        test_results = ''

        for result in results:
            if result['status'] == 'Pass':
                n_pass += 1
            elif result['status'].startswith('Skipped'):
                n_skip += 1
            else:
                n_fail += 1

            pattern = result['pattern'].replace('_', ' ')

            line = '    {:>3d}-byte {:<30s} {:s}'
            line = line.format(result['size'], pattern, result['status'])
            test_results += line + linesep

        if n_fail == 0:
            total_tests_passed += 1
            pass_str = 'Test Passed'
            if n_skip > 0:
                pass_str += ' (with {:d} skipped)'.format(n_skip)

            report_body += test_header.format(test_name, pass_str)
        else:
            total_tests_failed += 1
            report_body += test_header.format(test_name, 'Test Failed')

        report_body += test_results + linesep
        total_tests += 1

    if total_tests_failed == 0 and total_tests_passed > 0:
        print(report_header.format('Pass'))
    else:
        print(report_header.format('Fail'))
    print(report_body)
    print(report_footer.format(total_tests, total_tests_passed, total_tests_failed))

    return 0 if total_tests_failed == 0 else 1


def execute_all_tests(ctx, address):
    report = {}

    try:
        log.info('Testing memory read implementations')
        for reader in ctx.memory_readers:
            default_writer = ctx.default_memory_writer()
            test_name = '{:s} / {:s}'.format(reader.name, default_writer.name)
            results = run_tests(ctx, reader, default_writer, address)
            report[test_name] = results

        log.info('Testing memory write implementations')
        for writer in ctx.memory_writers:
            default_reader = ctx.default_memory_reader()
            test_name = '{:s} / {:s}'.format(writer.name, default_reader.name)
            results = run_tests(ctx, default_reader, writer, address)
            report[test_name] = results

    except KeyboardInterrupt:
        log.warning('Memory test suite interrupted. Returning partial results.')

    return report


def execute_specific_test(args, ctx, address):
    reader_specified = False

    if args.reader is not None:
        reader_specified = True
        reader = ctx.memory_readers.find(args.reader)
    else:
        reader = ctx.default_memory_reader()

    if args.writer is not None:
        writer = ctx.memory_writers.find(args.writer)
    else:
        writer = ctx.default_memory_writer()

    if reader_specified:
        test_name = '{:s} / {:s}'.format(reader.name, writer.name)
    else:
        test_name = '{:s} / {:s}'.format(writer.name, reader.name)

    results = run_tests(ctx, reader, writer, address)

    report = {}
    report[test_name] = results
    return report


if __name__ == '__main__':
    cmdline = ArgumentParser()
    cmdline.add_argument('--reader', default=None, help='Specific reader to test')
    cmdline.add_argument('--writer', default=None, help='Specific writier to test')
    args = cmdline.parse_args()

    ctx = create_depthcharge_ctx(args,
                                 da_pre_fn=_da_read_pre_func, da_pre_info=_da_read_pre_info)

    version_str = ctx.version()[0]

    # Save state prior to running tests as a courtesy. If we error out,
    # at least some initial info read from the device can bse saved.
    if args.config:
        ctx.save(args.config)

    address = ctx.env_var('loadaddr')

    t_start = time.time()
    if args.reader is not None or args.writer is not None:
        report = execute_specific_test(args, ctx, address)
    else:
        report = execute_all_tests(ctx, address)
    t_stop = time.time()
    t_elapsed = t_stop - t_start

    status = print_report(report, t_elapsed, version_str, args.config)

    if args.config:
        ctx.save(args.config)  # Save final state

    sys.exit(status)
