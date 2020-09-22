#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=redefined-outer-name,missing-function-docstring,invalid-name
"""
Exercise all available scripts in an attempt to wriggle out any bugs in
command-line usage and top-level APIs.

This should be run on target with a permissive U-Boot configuration, such as a
development kit or reference design.
"""

import os
import pickle
import shutil
import sys
import time

from datetime import timedelta
from os.path import basename, dirname, realpath
from subprocess import run, DEVNULL

from depthcharge import log, string, cmdline

from test_utils import (
    create_resource_dir, now_str, load_config, load_file, save_file, random_pattern
)

_THIS_DIR = dirname(realpath(__file__))
_EXPECTED = ['inspect', 'print', 'read-mem', 'find-cmd', 'stratagem', 'write-mem']


def locate_scripts() -> dict:
    """
    Return full paths to each depthcharge script.

    Dict keys are the script names, with the 'depthcharge-' prefix removed.
    Values are the full paths to the script.

    """
    script_dir = realpath(os.path.join(_THIS_DIR, '../../scripts'))
    log.info('Searching for scripts in: ' + script_dir)

    ret = {}
    for root, _, files in os.walk(script_dir):
        for filename in files:
            script = os.path.join(root, filename)
            key = basename(script).replace('depthcharge-', '')
            ret[key] = script

    for key in _EXPECTED:
        if key not in ret:
            raise FileNotFoundError('Failed to locate depthcharge-' + key)

    return ret


def test_help(_state: dict, script: str):
    """
    Confirm that the script doesn't explode before argument parsing takes place.
    """
    log.note('  Verifying help results in 0 return status')
    run([script, '-h'], stdout=DEVNULL, check=True)
    run([script, '--help'], stdout=DEVNULL, check=True)


_ENV_TEXT = """\
bootargs=some_base_args
addip=setenv bootargs ${bootargs} ip=${ipaddr}:${serverip}:${gatewayip}:${netmask}:${hostname}:eth0:off
boot_dtb=${loadaddr} - ${dtb_addr}
dtb_addr=0x83000000
dtb_size=0x20000
gatewayip=192.168.0.1
hostname=Philbert
ipaddr=192.168.0.200
loadaddr=0x82000000
netmask=255.255.255.0
serverip=192.168.0.10
"""


def test_mkenv(state: dict, script: str):
    """
    Convert a textual environment to binary form.
    """

    output_dir = create_resource_dir(os.path.join(state['test_dir'], 'env'))
    text_env = os.path.join(output_dir, 'env.txt')
    with open(text_env, 'w') as outfile:
        outfile.write(_ENV_TEXT)

    # Do this twice just to exercise all the arg forms
    args = [
        script,
        '-H',
        '-S', '0x1000',
        '-f', text_env,
        '-o', os.path.join(output_dir, 'env_no_hdr.1.bin')
    ]
    run(args, stdout=DEVNULL, check=True)

    args = [
        script,
        '--no-hdr',
        '--size', '8K',
        '--flags', '0xa',  # Gets ignored due to --no-hdr
        '-f', text_env,
        '-o', os.path.join(output_dir, 'env_no_hdr.2.bin')
    ]
    run(args, stdout=DEVNULL, check=True)

    args = [
        script,
        '--size', '1K',
        '-f', text_env,
        '-o', os.path.join(output_dir, 'env.bin')
    ]
    run(args, stdout=DEVNULL, check=True)

    args = [
        script,
        '-S', '0x1000',
        '-F', '0xa',
        '-f', text_env,
        '-o', os.path.join(output_dir, 'env_flags_0xa.bin')
    ]
    run(args, stdout=DEVNULL, check=True)


def test_find_env(state: dict, script: str):
    """
    Locate environments created by test_mkenv in a binar blob.
    """

    output_dir = create_resource_dir(os.path.join(state['test_dir'], 'env'))
    blobfile = os.path.join(output_dir, 'blob.bin')
    with open(blobfile, 'wb') as outfile:
        outfile.write(random_pattern(31, seed=0) + b'\x00')

        with open(os.path.join(output_dir, 'env_no_hdr.1.bin'), 'rb') as infile:
            data = infile.read()
            outfile.write(data)

        outfile.write(random_pattern(63, seed=1) + b'\x00')

        with open(os.path.join(output_dir, 'env_no_hdr.2.bin'), 'rb') as infile:
            data = infile.read()
            outfile.write(data)

        outfile.write(random_pattern(1023, seed=2) + b'\x00')

        with open(os.path.join(output_dir, 'env_flags_0xa.bin'), 'rb') as infile:
            data = infile.read()
            outfile.write(data)

        outfile.write(random_pattern(3, seed=3) + b'\x00')
        with open(os.path.join(output_dir, 'env.bin'), 'rb') as infile:
            data = infile.read()
            outfile.write(data)

        outfile.write(random_pattern(64, seed=4) + b'\x00')

    test_dir = create_resource_dir(os.path.join(state['test_dir'], 'find_env'))
    filename_pfx = os.path.join(test_dir, 'env')

    # Expanded text
    args = [
        script,
        '-A', 'arm',
        '-a', '0x8004_0000',
        '-E',
        '-f', blobfile,
        '-o', filename_pfx,
    ]
    run(args, stdout=DEVNULL, check=True)

    # Expanded text dup, default arch and addr
    args = [
        script,
        '--expand',
        '-f', blobfile,
        '-o', filename_pfx,
    ]
    run(args, stdout=DEVNULL, check=True)

    # Text
    args = [
        script,
        '-f', blobfile,
        '-o', filename_pfx,
    ]
    run(args, stdout=DEVNULL, check=True)

    args = [
        script,
        '-B',
        '-f', blobfile,
        '-o', filename_pfx,
    ]
    run(args, stdout=DEVNULL, check=True)

    # Dup of the above, just long-form args
    args = [
        script,
        '--binary',
        '--file', blobfile,
        '--outfile', filename_pfx,
    ]
    run(args, stdout=DEVNULL, check=True)

    results = {
        'high_exp_text': 0,
        'low_exp_text':  0,
        'text': 0,
        'bin': 0
    }

    for root, _, filenames in os.walk(test_dir):
        for filename in filenames:
            if filename.endswith('.bin'):
                results['bin'] += 1
            elif filename.endswith('exp.txt'):
                if '0x8' in filename:
                    results['high_exp_text'] += 1
                else:
                    results['low_exp_text'] += 1
            elif filename.endswith('.txt'):
                results['text'] += 1
            else:
                raise RuntimeError('Unexpected condition')

    for key, value in results.items():
        if value != 4:
            msg = '{:s}: Expected 4, got {:d}'.format(key, value)
            raise ValueError(msg)


# flake8: noqa=W191
_DTS = \
"""
/dts-v1/;

/ {
	#address-cells = <1>;
	#size-cells = <1>;

	bus@ff784000 {
		#address-cells = <1>;
		#size-cells = <1>;
		compatible = "depthcharge-bus", "simple-bus";
		ranges = <0x0 0x10000000 0x10000>;

		node@d00dfeed {
			reg = <0xd00dfeed 1>;
		};
	};

};
"""

_DTC = shutil.which('dtc')

def test_find_fdt(state: dict, script: str):
    """
    Exercises depthcharge-find-fdt
    """
    output_dir = create_resource_dir(os.path.join(state['test_dir'], 'fdt'))
    dts_file = os.path.join(output_dir, 'test.dts.input')

    with open(dts_file, mode='w') as outfile:
        outfile.write(_DTS)

    args = [_DTC, '-q', '-I', 'dts', '-O', 'dtb', dts_file]
    sub = run(args, check=True, capture_output=True)
    dtb = sub.stdout

    image_file = os.path.join(output_dir, 'image.bin')
    with open(image_file, 'wb') as outfile:
        outfile.write(random_pattern(412, seed=0))
        outfile.write(dtb)
        outfile.write(random_pattern(123, seed=1))
        outfile.write(dtb)
        outfile.write(random_pattern(4500, seed=2))
        outfile.write(dtb)
        outfile.write(random_pattern(150, seed=3))

    # Print only
    args = [script, '-f', image_file]
    run(args, check=True, stdout=DEVNULL)

    outpfx = os.path.join(output_dir, 'test')

    # Save DTB and DTS files
    args = [script, '-f', image_file, '-o', outpfx, '-a', '0x8000_0000']
    run(args, check=True, stdout=DEVNULL)

    # Save DTB only
    args = [script, '-f', image_file, '-o', outpfx, '-a', '0x9000_0000', '--no-dts']
    run(args, check=True, stdout=DEVNULL)

    # Save DTS only
    args = [script, '-f', image_file, '-o', outpfx, '-a', '0xa000_0000', '--no-dtb']
    run(args, check=True, stdout=DEVNULL)

    # Count results
    results = {'dtb': 0, 'dts': 0}
    for _, _, filenames in os.walk(output_dir):
        for f in filenames:
            if f.endswith('.dts'):
                results['dts'] += 1
            elif f.endswith('.dtb'):
                results['dtb'] += 1

    assert results['dtb'] == 6
    assert results['dts'] == 6

def test_inspect(state: dict, script: str):
    """
    Exercises depthcharge-inspect.

    Produces state['config_file'] that is used by later scripts.
    Loads state['config_file]'.
    """
    # TODO: Still need to exercise -C, -p, -b

    # Inspect device and produce config file
    args = [
        script, '-c', state['config_file'],
        '-X', '_unused_value=foo,_unused_bar',
        '-m', 'file:/dev/null',
    ]
    run(args, check=True)

    # Run again to force loading of config
    run(args, check=True)

    # This should trigger a timeout if -P is working;
    log.note('  Inducing a timeout to test -P ... please wait')
    env = os.environ.copy()
    env['DEPTHCHARGE_LOG_LEVEL'] = 'error'

    result = run(args + ['-P', 'BAD PROMPT >'], text=True, capture_output=True, env=env, check=False)
    if result.returncode != 1:
        raise ValueError('Expected returcode = 1, got ' + str(result.returncode))

    if 'Timed out' not in result.stderr:
        raise ValueError('Did not get expected timeout: ' + result.stderr)

    state['config'] = load_config(state['config_file'])


def test_print(state: dict, script: str):
    """
    Exercise depthcharge-print.

    Requires state['config_file'].
    """

    items = (
        'all',
        'arch',
        'commands', 'commands=detail',
        'env', 'env=expand',
        'gd',
        'version'
    )

    output_dir = create_resource_dir(os.path.join(state['test_dir'], 'print'))
    for item in items:
        args = [script, '-c', state['config_file'], '-i', item]
        filename = os.path.join(output_dir, item.replace(':', '_'))
        log.note('  Printing ' + item + ' > ' + filename)
        with open(filename, 'w') as outfile:
            run(args, check=True, stdout=outfile)


def test_write_mem__pattern(state: dict, script: str):
    """
    Write a random test pattern to $loadaddr

    Loads state['config_file]'.

    Adds written data in state['write_data'].
    """
    _WRITE_SIZE = 16385

    # Split data into two parts:
    #  1. Data written from a file
    #  2. Data written from a hex string provided on the command-line

    data = random_pattern(_WRITE_SIZE)
    write_data_file = os.path.join(state['test_dir'], 'write_data.bin')

    state['write_data'] = data
    state['write_data_file'] = write_data_file

    save_file(write_data_file, data, 'wb')

    wr_data1 = data[:_WRITE_SIZE-31]
    wr_data2 = data[_WRITE_SIZE-31:]

    wr_addr = int(state['config']['env_vars']['loadaddr'], 0)

    # Part 1 data
    test_file = os.path.join(state['test_dir'], 'write_data.1.bin')

    save_file(test_file, wr_data1, 'wb')

    args = [
        script,
        '-a', hex(wr_addr),
        '-f', test_file,
        '-c', state['config_file'],
        '-X', '_unused_value=foo,_unused_bar',
        '-m', 'file:/dev/null',
        '--op', 'loady,loadx,loadb'
    ]
    run(args, check=True)

    wr_addr += len(wr_data1)

    # Part 2 data - drop the extra unused args just to have a different
    # set of cmdline args
    args = [
        script,
        '-a', hex(wr_addr),
        '-d', wr_data2.hex(),
        '-c', state['config_file'],
    ]
    run(args, check=True)


def test_read_mem__pattern(state: dict, script: str):
    """
    Read the test pattern written in test_write_mem__pattern() and
    confirm it matches config['write_data'].
    """

    # Read data to a file
    test_file = os.path.join(state['test_dir'], 'read_pattern.bin')
    loadaddr = int(state['config']['env_vars']['loadaddr'], 0)
    args = [
        script,
        '-c', state['config_file'],
        '-a', hex(loadaddr),
        '-l', str(len(state['write_data'])),
        '-f', test_file
    ]
    run(args, check=True)

    test_data = load_file(test_file, 'rb')
    assert test_data == state['write_data']
    test_data = None

    # Read data to a hex dump
    loadaddr = int(state['config']['env_vars']['loadaddr'], 0)
    args = [
        script,
        '-c', state['config_file'],
        '-a', hex(loadaddr),
        '-l', str(len(state['write_data']))
    ]

    result = run(args, check=True, capture_output=True, text=True)
    test_addr, test_data = string.xxd_reverse(result.stdout)

    assert test_addr == loadaddr
    assert test_data == state['write_data']

    # Add --op argument as list
    run(args + ['--op', 'md,itest,setexpr'], check=True)

    # Add --op argument
    run(args + ['--op', 'md'], check=True)


def test_read_mem__uboot(state: dict, script: str):
    """
    Read 512KiB of post-relocated U-Boot code/data to a u-boot.bin file in the
    resource directory in preparation for test_find_cmd() can be exercised.


    Populates state['config]', state['uboot_bin_file']
    """
    _READ_SIZE = 512 * 1024

    state['uboot_bin_file'] = os.path.join(state['test_dir'], 'uboot_512K.bin')
    uboot_addr = state['config']['gd']['bd']['relocaddr']['value']

    log.info('Reading 512K of U-Boot code/data to a binary file')

    args = [
        script,
        '-a', hex(uboot_addr), '-l', str(_READ_SIZE),
        '-f', state['uboot_bin_file'],
    ]
    run(args, check=True)


def test_find_cmd(state: dict, script):
    """
    Confirm that a command table is found in state['uboot_bin_file'] for
    a few different settings.
    """

    image_file = state['uboot_bin_file']
    uboot_addr = state['config']['gd']['bd']['relocaddr']['value']

    log.note('  Testing default-usage of depthcharge-find-cmd')
    args = [
        script,
        '-a', hex(uboot_addr),
        '-f', image_file,
    ]
    results = run(args, capture_output=True, text=True, check=True)
    assert 'Command table @ 0x' in results.stdout
    assert 'cmd_rep' not in results.stdout

    log.note('  Testing depthcharge-find-cmd with additional arguments')
    args = [
        script,
        '-a', hex(uboot_addr),
        '-A', state['config']['arch'],
        '-f', image_file,
        '--details',
        '--subcmds',
        '--threshold', '6'
    ]
    results = run(args, capture_output=True, text=True, check=True)
    assert 'Command table @ 0x' in results.stdout
    assert 'cmd_rep' in results.stdout

    log.note('  Testing depthcharge-find-cmd with --longhelp and --autocomplete')
    args = [
        script,
        '-a', hex(uboot_addr),
        '-A', state['config']['arch'],
        '-f', image_file,
        '--longhelp', 'Y',
        '--autocomplete', 'Y'
    ]
    results = run(args, capture_output=True, text=True, check=True)
    assert 'Command table @ 0x' in results.stdout
    assert 'cmd_rep' not in results.stdout

    log.note('  Testing depthcharge-find-cmd with incorrect --longhelp and --autocomplete')
    args = [
        script,
        '-a', hex(uboot_addr),
        '-A', state['config']['arch'],
        '-f', image_file,
        '--longhelp', 'N',
        '--autocomplete', 'N'
    ]
    results = run(args, capture_output=True, text=True, check=True)
    assert len(results.stdout) == 0


def test_stratagem(state: dict, script: str):
    """
    Produce a stratagem file to be used with depthcharge-write-mem.
    Uses state['write_data_file'] as input.

    """
    loadaddr = int(state['config']['env_vars']['loadaddr'], 0)

    stratagem = os.path.join(state['test_dir'], 'stratagem.json')
    state['stratagem'] = stratagem

    stratagem_payload = b'Hello World!'
    state['stratagem_payload'] = stratagem_payload

    state['payload_file'] = os.path.join(state['test_dir'], 'payload.bin')
    save_file(state['payload_file'], stratagem_payload, 'wb')

    log.note('  Producing CRC32MemoryWriter stratagem')
    args = [
        script,
        '-a', hex(loadaddr),
        '-f', state['write_data_file'],
        '-P', state['payload_file'],
        '-X', 'revlut_maxlen=512,max_iterations=10000',
        '-o', stratagem,
        '-s', 'crc32',
    ]
    run(args, check=True)


def test_write_mem__deploy_stratagem(state: dict, script: str):
    """
    Append to our write payload using a Stratagem produced by CRC32MemoryWriter.

    Uses state['stratagem'] and state['stratagem_payload'] produced by test_stratagem.
    """

    loadaddr = int(state['config']['env_vars']['loadaddr'], 0)
    target_addr = loadaddr + len(state['write_data'])

    # We'll begin zeroizing memory here to <this address> + 32 bytes
    # The deployed payload will land within this region
    zero_addr = target_addr
    state['zeroized_addr'] = zero_addr

    # Align on an 8-byte boundary to ensure this works across architectures...
    target_addr = (target_addr + 7) // 8 * 8

    state['write_append_addr'] = target_addr

    # This just aims to ensure we're working from a clean memory state, such
    # that a previously run successful test test doesn't result in a false
    # negative for a failure in the current test to actually write any data.
    log.note('  Zeroizing target memory')
    state['zeroized_len'] = 32
    args = [
        script,
        '-c', state['config_file'],
        '-a', hex(zero_addr),
        '-d', '00' * state['zeroized_len'],
    ]
    run(args, check=True)

    log.note('  Executing CRC32MemoryWriter stratagem')
    args = [
        script,
        '-c', state['config_file'],
        '-a', hex(target_addr),
        '-s', state['stratagem'],
    ]
    run(args, check=True)


def test_read_mem__readback(state: dict, script: str):
    """
    Read back data written by test_write_mem__deploy_stratagem()
    and verify it.

    Writes data to a file whose name is stored in state['readback_file']
    """
    zeros_preceeding = state['write_append_addr'] - state['zeroized_addr']
    zeros_following  = state['zeroized_len'] - zeros_preceeding - len(state['stratagem_payload'])

    expected = b'\x00' * zeros_preceeding + state['stratagem_payload'] + b'\x00' * zeros_following
    read_len = len(expected)

    expected_file = os.path.join(state['test_dir'], 'readback.expected.bin')
    with open(expected_file, 'wb') as outfile:
        outfile.write(expected)

    state['readback_file'] = os.path.join(state['test_dir'], 'readback.bin')

    addr = state['zeroized_addr']

    log.note('  Reading back data at $loadaddr.')
    args = [
        script,
        '-c', state['config_file'],
        '-a', hex(addr),
        '-l', str(read_len),
        '-f', state['readback_file'],
        '-D',
    ]
    run(args, check=True)

    readback_data = load_file(state['readback_file'], 'rb')
    assert readback_data == expected


_TESTS = [
    # Do not require a device
    test_mkenv,
    test_find_env,
    test_find_fdt,

    # Requires device
    test_inspect,
    test_print,
    test_write_mem__pattern,
    test_read_mem__pattern,
    test_read_mem__uboot,
    test_find_cmd,
    test_stratagem,
    test_write_mem__deploy_stratagem,
    test_read_mem__readback,
]


def test_name_to_script(test: str) -> str:
    ret = test.replace('test_', '')

    try:
        suffix_idx = ret.index('__')
        ret = ret[:suffix_idx]
    except ValueError:
        pass

    return 'depthcharge-' + ret.replace('_', '-')


def handle_cmdline():
    parser = cmdline.ArgumentParser([])
    parser.add_argument('--state', help='State file from previous run to use.')
    parser.add_argument('--test', help='Test to resume execution at')
    return parser.parse_args()


def load_tests(args):
    if args.test is None:
        return _TESTS

    test_idx = None
    for i, test in enumerate(_TESTS):
        if test.__name__ == args.test:
            test_idx = i

    if test_idx is None:
        raise ValueError('Invalid test name: ' + args.test)

    return _TESTS[test_idx:]


def load_state(args):
    if args.state is None:
        state = {}

        state['test_dir'] = create_resource_dir('launch_scripts-' + now_str())
        state['config_file'] = os.path.join(state['test_dir'], 'test.cfg')

        # We'll populate this during test_inspect
        state['config'] = None

        return state

    with open(args.state, 'rb') as infile:
        return pickle.load(infile)


def save_state(state):
    state_file = os.path.join(state['test_dir'], 'state.bin')
    with open(state_file, 'wb') as outfile:
        pickle.dump(state, outfile)


if __name__ == '__main__':
    args = handle_cmdline()

    try:
        scripts = locate_scripts()
    except FileNotFoundError as error:
        log.error(str(error))
        sys.exit(1)

    tests = load_tests(args)
    state = load_state(args)

    t_start = time.time()

    for test in tests:
        script = test_name_to_script(test.__name__)
        log.info('Running ' + test.__name__)
        test_help(state, script)
        test(state, script)
        save_state(state)

    t_end = time.time()
    t_elapsed = timedelta(seconds=(t_end - t_start))
    print(os.linesep + '=' * 76)
    print('Tests complete successfully.')
    print('Elapsed: ' + str(t_elapsed))
    print()
