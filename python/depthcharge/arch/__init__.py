# SPDX-License-Identifier: BSD-3-Clause
#
# flake8: noqa=F401

"""
Support for various target architectures
"""

from .arch import Architecture

from .arm import ARM
from .aarch64 import AARCH64
from .generic import Generic, GenericBE, Generic64, Generic64BE
