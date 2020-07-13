# SPDX-License-Identifier: BSD-3-Clause
#
# flake8: noqa=F401

"""
This module provides the :py:class:`~depthcharge.hunter.Hunter` base class
and its associated implementations.

In Depthcharge parlance, a *"Hunter"* is class that searches data for items of interest
and either provides information about located instances or produces an artifact using
the located data (e.g., a :py:class:`~depthcharge.Stratagem`).

"""

from .cmdtbl import CommandTableHunter
from .cp import CpHunter
from .constant import ConstantHunter
from .env import EnvironmentHunter
from .fdt import FDTHunter
from .hunter import Hunter, HunterResultNotFound
from .revcrc32 import ReverseCRC32Hunter
from .string import StringHunter
