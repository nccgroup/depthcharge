#!/usr/bin/env python3
"""
Deploy and execute a simple "standalone program" that just
returns a constant value:

AARCH64: 0x666badc0ffeed00d
ARM:     0xc0ffee
"""

import sys

from depthcharge import cmdline, log
from depthcharge.cmdline  import create_depthcharge_ctx

parser = cmdline.ArgumentParser()
args = parser.parse_args()

if args.arch is None:
    log.error('Target architecture must be specified.')
    sys.exit(1)
elif args.arch.lower() == 'arm':
    # push {lr}; ldr r0, =0xc0ffee; pop {pc};
    program = bytes.fromhex('04 e0 2d e5 00 00 9f e5 04 f0 9d e4 ee ff c0 00')
elif args.arch.lower() == 'aarch64':
    # ldr x0, =0x666c0ffeed00d; ret;
    program = bytes.fromhex('40 00 00 58 c0 03 5f d6 0d d0 ee ff c0 66 06 00')
else:
    log.error("Example doesn't support arch: " + args.arch)
    sys.exit(1)

ctx = create_depthcharge_ctx(args)
ctx.register_payload('test_code', program)
ctx.deploy_payload('test_code')
(retval, _) = ctx.execute_payload('test_code')

log.info('Got return value: 0x{:x}'.format(retval))
