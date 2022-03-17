#!/usr/bin/env python3
"""
Depthcharge installation script
"""

import os
import re

from os.path import dirname, join, realpath
from setuptools import setup, find_packages

THIS_DIR = realpath(dirname(__file__))

# This is technically more permissive than what is dictated by PEP440,
# which requires a dot for suffixes, rather than a dash. (Plus signs
# are used for local versions.)
#
# Strict compliance will matter uploads to PyPi, but I'd prefer that
# mistakes in the dev series don't break the *next* branch for users
# of the bleeding edge code in GitHub.
#
# See https://www.python.org/dev/peps/pep-0440/#public-version-identifiers
#
VERSION_REGEX = re.compile(
    r"__version__\s*=\s*'(?P<version>[0-9]+\.[0-9]+\.[0-9]+((\.|-|\+)[a-zA-Z0-9]+)*)'"
)


def get_version() -> str:
    version_file = join(THIS_DIR, 'depthcharge', 'version.py')
    with open(version_file, 'r') as infile:
        version_info = infile.read()
        match = VERSION_REGEX.search(version_info)
        if match:
            return match.group('version')

    raise ValueError('Failed to find version info')


def get_scripts() -> list:
    ret = []
    for root, _, files in os.walk('scripts'):
        for filename in files:
            if filename.startswith('.') or filename.endswith('.swp'):
                continue

            script_file = join(root, filename)
            ret.append(script_file)

    if not ret:
        raise FileNotFoundError('Depthcharge scripts not found')

    return ret


def get_description() -> str:
    with open('Depthcharge.md', 'r') as infile:
        return infile.read()


setup(
    name='depthcharge',
    version=get_version(),
    description='A U-Boot toolkit for security researchers and tinkerers',

    long_description=get_description(),
    long_description_content_type='text/markdown',

    license='BSD 3-Clause License',
    author='Jon Szymaniak (NCC Group)',
    author_email='jon.szymaniak.foss@gmail.com',
    url='https://github.com/nccgroup/depthcharge',

    # I'm only supporting Linux at the moment,
    platform='linux',

    packages=find_packages(),
    scripts=get_scripts(),

    install_requires=['pyserial >= 3.4', 'tqdm >= 4.30.0'],

    python_requires='>=3.6, <4',

    extras_require={
        'docs': ['sphinx>=4.4.0', 'sphinx_rtd_theme >=1.0.0, <2.0.0']
    },

    zip_safe=False,

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Security',
        'Topic :: System :: Boot',
        'Topic :: System :: Hardware',
    ],

    project_urls={
        'Documentation': 'https://depthcharge.readthedocs.io',
        'Source': 'https://github.com/nccgroup/depthcharge',
        'Issue Tracker': 'https://github.com/nccgroup/depthcharge/issues',
    },
)
