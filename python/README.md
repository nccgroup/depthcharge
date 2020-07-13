# Depthcharge Python Code

This directory contains the [depthcharge](./depthcharge) Python module,
a collection of [scripts](./scripts) built atop of that modules, 
[example scripts](./examples), and the Sphinx-based 
[documentation source](./docs).

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

Given that the Depthcharge is still in its "alpha" state, its dependencies and
API may change across version. As such, users are encouraged to install it into
a [virtual environment](https://docs.python.org/3/library/venv.html) (venv), rather
than system-wide. Below are the commands required to do this.

First, ensure you have installed `python3-venv`. For apt-based distros:

```
$ sudo apt install python3-venv
```

If you planning to use, but not modify, Depthcharge, create a venv and install
into it using the commands. Note that there are `activate.csh` and
`activate.fish` scripts for users of those shells.

```
$ python3 -m venv ./venv
$ source ./venv/bin/activate
$ pip install .
```

If you plan on building the documentation, add the extra ``[docs]`` option in
order to include the necessary *Sphinx* and *sphinx_rtd_theme* dependencies:

```
$ pip install .[docs]
```

However, if you are planning to modify the module or scripts, it is recommended that 
you instead run pip with the `-e, --editable` flag. If you will be modifying the
Depthcharge scripts, you may also want to symlink items in `venv/bin/` to the
corresponding files in `scripts/` using `dev/symlink_scripts.py`

```
$ pip install -e .
$ ./dev/symlink_scripts.py
```
