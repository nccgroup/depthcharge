#!/usr/bin/env python3
#
# Convert scripts installed in the venv/bin to symlinks.
# Usage: symlink_scripts.py [venv_dir]
#

import sys
import os
from os.path import join, dirname, realpath

if __name__ == '__main__':
    root = dirname(dirname(realpath(__file__)))
    scripts = realpath(join(root, 'scripts'))

    try:
        venv = sys.argv[1]
    except IndexError:
        venv = join(root, 'venv')

    venv = realpath(venv)
    venv_bin = join(venv, 'bin')

    for root, _, filenames in os.walk(scripts):
        for filename in filenames:
            source = join(root, filename)
            target = join(venv_bin, filename)

            os.remove(target)
            print('Remove ' + target)

            os.symlink(source, target)
            print('Symlink ' + target + ' -> ' + source)
