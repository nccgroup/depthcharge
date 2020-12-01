# Depthcharge Python Code

This directory contains the [depthcharge](./depthcharge) Python module,
a collection of [scripts](./scripts) built atop of that modules,
[example scripts](./examples), and the Sphinx-based
[documentation source](./docs).

The latest release of this code is available on the 
[Python Package Index (PyPi)](https://pypi.org/project/depthcharge),
and can be installed via `python3 -m pip install depthcharge`.

The instructions below are intended for those wishing to work with the latest
code [available on GitHub](https://github.com/nccgroup.com/depthcharge/tree/next).

## Python Dependencies

The following represent the minimum versions Depthcharge has been tested with.
Earlier versions may suffice, but are not supported.

* Python >= 3.6
* [pyserial](https://github.com/pyserial/pyserial) >= 3.4
* [tqdm](https://tqdm.github.io/) >= 4.42.1

The following dependencies are required if you'd like to build the
documentation:

* [Sphinx](https://pypi.org/project/Sphinx) >= 3.0.0
* [sphinx_rtd_theme](https://github.com/readthedocs/sphinx_rtd_theme) >= 0.4.0

## Installation

Given that the Depthcharge is still in its "beta" state, its dependencies and
API may change across version. As such, users are encouraged to install it into
a [virtual environment](https://docs.python.org/3/library/venv.html) (venv), rather
than system-wide. Below are the commands required to do this.

First, ensure you have installed `python3-venv`. For apt-based distros:

```
$ sudo apt install python3-venv
```

Next, create a virtual environment and install Depthcharge
and its dependencies in it. Note that there are `activate.csh` and
`activate.fish` scripts for users of those shells.

```
$ python3 -m venv ./venv
$ source ./venv/bin/activate
$ python3 -m pip install .
```

If you plan on modifying the source code or documentation, add the ``-e, --editable``
flag to the pip command and specify the extra ``[docs]`` option in
order to include the necessary *Sphinx* and *sphinx_rtd_theme* dependencies:

```
$ python3 -m pip install -e .[docs]
```
