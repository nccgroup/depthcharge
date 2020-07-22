#!/usr/bin/env python3
"""
Depthcharge installation script
"""

import os
import re

from os.path import dirname, join, realpath
from setuptools import setup, find_packages

THIS_DIR = realpath(dirname(__file__))

VERSION_REGEX = re.compile(
    r"__version__\s*=\s*'(?P<version>[0-9]+\.[0-9]+\.[0-9]+(\.[a-zA-Z0-9]+)?)'"
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


# FIXME: Copy-paste of README in order to work around PIP/RTD issue of my own making.
# https://github.com/nccgroup/depthcharge/issues/14
#

_LONG_DESC = """\
# Depthcharge

<img align="right" src="https://raw.githubusercontent.com/nccgroup/depthcharge/master/doc/images/depthcharge-500.png" height="265" width="265">

## What is Depthcharge?

Depthcharge is a toolkit designed to support security research and
"jailbreaking" of embedded platforms using the [U-Boot] bootloader.
It consists of:

* An extensible Python 3 [depthcharge module]
* [Python scripts] built atop of the `depthcharge` module API
* [Depthcharge "Companion" firmware], which is used to perform attacks requiring a malicious peripheral device.
* Some example ["helper" payload binaries] and build scripts to get you started with U-Boot "standalone" program-esque payloads.

[U-Boot]: https://www.denx.de/wiki/U-Boot
[depthcharge module]: https://github.com/nccgroup/depthcharge/tree/master/python/depthcharge
[Python scripts]: https://github.com/nccgroup/depthcharge/tree/master/python/scripts
[Depthcharge "Companion" firmware]: https://github.com/nccgroup/depthcharge/tree/master/firmware/Arduino
["helper" payload binaries]: https://github.com/nccgroup/depthcharge/tree/master/payloads
["standalone"]: https://gitlab.denx.de/u-boot/u-boot/-/blob/v2020.01/doc/README.standalone


## Project Documention

More information can be found in the [online documentation] for the Depthcharge project.

* [Introduction](https://depthcharge.readthedocs.io/en/latest/introduction.html)
  * [What is Depthcharge?](https://depthcharge.readthedocs.io/en/latest/introduction.html#what-is-depthcharge)
  * [Will this be useful for my situation?](https://depthcharge.readthedocs.io/en/latest/introduction.html#will-this-be-useful-for-my-situation)
  * [What are some of its key features?](https://depthcharge.readthedocs.io/en/latest/introduction.html#what-are-some-of-its-key-features)
  * [How do I get started?](https://depthcharge.readthedocs.io/en/latest/introduction.html#how-do-i-get-started)
* [Python Scripts](https://depthcharge.readthedocs.io/en/latest/scripts/index.html)
* [Python API](https://depthcharge.readthedocs.io/en/latest/api/index.html)
* [Companion Firmware](https://depthcharge.readthedocs.io/en/latest/companion_fw.html)
* [Troubleshooting](https://depthcharge.readthedocs.io/en/latest/troubleshooting.html)


If you'd like to build this documentation for offline viewing, You can find the
[Sphinx]-based documentation "source" in the [doc] directory.

[doc]: https://github.com/nccgroup/depthcharge/tree/master/doc
[online documentation]: https://depthcharge.readthedocs.io
[Sphinx]: https://www.sphinx-doc.org/en/master/

## Versioning

Depthcharge uses a [Semantic versioning] scheme for both the Python API and the Companion Firmware.
The version number for published releases will follow that of the Python API version.
The [CHANGELOG] shall document the current version state of both, along
with any compatibility information.

Currently, this project uses ["unstable"] version numbers; API-breaking changes
may occur within this minor version series, if deemed to be sufficiently
beneficial for the future of the project. Refer to the
CHANGELOG for guidance on handling any API changes.

Each published release will have a "codename". This serves no real purpose,
other than to amuse the author and add a little fun to preparing releases.
(Maybe they'll even be useful to remember!) The codenames are song titles from
punk bands, increasing alphabetically with each release.

[CHANGELOG]: https://github.com/nccgroup/depthcharge/blob/master/CHANGELOG
[Semantic versioning]: https://semver.org
["unstable"]: https://semver.org/#spec-item-4

## License

All Depthcharge components are licensed under the [BSD 3-Clause License],
found in the [License.txt] file. Project files use the corresponding
[SPDX Identifier] to denote this.

[BSD 3-Clause License]: https://opensource.org/licenses/BSD-3-Clause
[LICENSE.txt]: https://github.com/nccgroup/depthcharge/blob/master/LICENSE.txt
[SPDX Identifier]: https://spdx.dev/ids

"""

setup(
    name='depthcharge',
    version=get_version(),
    description='A U-Boot toolkit for security researchers and tinkerers',

    long_description=_LONG_DESC,
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
        'docs': ['sphinx>=3.0.0', 'sphinx_rtd_theme>=0.4.0']
    },

    zip_safe=False,

    classifiers=[
        'Development Status :: 3 - Alpha',
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
