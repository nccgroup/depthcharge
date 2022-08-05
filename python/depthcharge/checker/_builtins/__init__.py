# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# flake8: noqa=F401

"""
Built-in definitions of potential security risks.

Each submodule shall define _BUILTIN_DEFS as list/tuple containing
entries in the form ``(config_key, match, SecurityRisk)``.

"""

from .cmdline   import _BUILTIN_DEFS as _CMDLINE_DEFS
from .env       import _BUILTIN_DEFS as _ENV_DEFS
from .fit       import _BUILTIN_DEFS as _FIT_DEFS
from .fs        import _BUILTIN_DEFS as _FS_DEFS
from .lib       import _BUILTIN_DEFS as _LIB_DEFS
from .net       import _BUILTIN_DEFS as _NET_DEFS

# Aggregate builtins into a main set of definitions
_BUILTIN_DEFS = (
    _CMDLINE_DEFS +
    _ENV_DEFS +
    _FIT_DEFS +
    _FS_DEFS +
    _LIB_DEFS +
    _NET_DEFS
)

# Fill empty source field.
# Required by SecurityRisk constructor, but excessive to require in _BUILTIN_DEFS
for entry in _BUILTIN_DEFS:
    entry[2]['source'] = ''
