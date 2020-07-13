# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Depthcharge provides simple logging functionality atop of
Python's own ``logging`` module.

The log level is initialized according to the level name (string) set in the the
``DEPTHCHARGE_LOG_LEVEL`` environment variable. If not present, the Depthcharge
logging defaults to the ``'note'`` level.

Below are the available levels in order of decreasing verbosity, and with their
associated message prefix symbols.

+----------------+-------------+------------------------------------------------------------------+
|   Level Name   | Msg. Prefix | Description                                                      |
+================+=============+==================================================================+
| debug          |   ``[#]``   | Highly verbose information used to diagnose failures in core code|
+----------------+-------------+------------------------------------------------------------------+
| note           |   ``[*]``   | Verbose status and progress information intended for end user    |
+----------------+-------------+------------------------------------------------------------------+
| info           |   ``[+]``   | Higher-level status and progress information - usually success   |
+----------------+-------------+------------------------------------------------------------------+
| warning        |   ``[!]``   | Similar to info, but for reporting undesirable status            |
+----------------+-------------+------------------------------------------------------------------+
| error          |   ``[X]``   | Describes what is failing and why to an end user                 |
+----------------+-------------+------------------------------------------------------------------+
| silent         |     N/A     | Deptcharge does not write log output to stderr                   |
+----------------+-------------+------------------------------------------------------------------+

During long running operations, Depthcharge will only display progress bars when
the log level is set to *note*, *info*, or *warning*.

The *debug* level is too verbose for progress bars to provide any value. Conversely, if one is
only interested in seeing output pertaining to failures, the progress bars become obtrusive.

In addition to setting the ``DEPTHCHARGE_LOG_LEVEL`` environment variable, Depthcharge's
log verbosity can be set using this submodule's :py:func:`set_level()` function.

"""

import os
import platform
import sys
import logging

DEBUG   = logging.DEBUG
NOTE    = logging.DEBUG + (logging.INFO - logging.DEBUG) // 2
INFO    = logging.INFO
WARNING = logging.WARN
ERROR   = logging.ERROR
SILENT  = logging.CRITICAL + (logging.CRITICAL - logging.ERROR)


class DepthchargeLog:
    """
    This class implements Depthcharge's custom logging.

    All instances of this class share the same underlying Python logger.
    """

    _level_name_map = {
        'debug':    DEBUG,
        'note':     NOTE,
        'info':     INFO,
        'warn':     WARNING,
        'warning':  WARNING,
        'error':    ERROR,
        'fatal':    ERROR,
        'critical': ERROR,
        'silent':   SILENT
    }

    def __init__(self, prefix='', logger_name='depthcharge'):
        """
        Create a Depthcharge log instance with an optional *prefix* string.

        The *logger_name* is used to obtain the underlying Python logging instance.
        """

        _pfx_debug   = '[#] '
        _pfx_note    = '[*] '
        _pfx_info    = '[+] '
        _pfx_warning = '[!] '
        _pfx_error   = '[X] '

        # Add color when a TTY that can probably handle it is in use
        if platform.system() in ('Linux', 'Darwin') and sys.stdout.isatty():
            _pfx_debug   = '\033[34m'   + _pfx_debug   + '\033[0m'
            _pfx_note    = '\033[36m'   + _pfx_note    + '\033[0m'
            _pfx_info    = '\033[32m'   + _pfx_info    + '\033[0m'
            _pfx_warning = '\033[33m'   + _pfx_warning + '\033[0m'
            _pfx_error   = '\033[31m'   + _pfx_error   + '\033[0m'

        if prefix != '' and not prefix.endswith(' '):
            prefix += ' '

        self._pfx_debug   = _pfx_debug + prefix
        self._pfx_note    = _pfx_note + prefix
        self._pfx_info    = _pfx_info + prefix
        self._pfx_warning = _pfx_warning + prefix
        self._pfx_error   = _pfx_error + prefix

        self.logger = logging.getLogger(logger_name)

    @property
    def level(self):
        """
        Current log level
        """
        return self.logger.level

    @level.setter
    def level(self, level):
        if isinstance(level, str):
            try:
                level = self._level_name_map[level.lower()]
            except KeyError:
                raise ValueError('Invalid log level: ' + level)

        self.logger.setLevel(level)

    def debug(self, *args, **kwargs):
        """
        Write a debug-level message to the log.

        This should be used for detailed diagnostic information that
        most users will never need to see.
        """
        self.logger.log(DEBUG, *((self._pfx_debug + args[0],) + args[1:]), **kwargs)

    def note(self, *args, **kwargs):
        """
        Write a note-level message to the log.

        This should be used for detailed information pertaining to an operation,
        especially for lower-level operations.
        """
        self.logger.log(NOTE, *((self._pfx_note + args[0],) + args[1:]), **kwargs)

    def info(self, *args, **kwargs):
        """
        Write an info-level message to the log.

        This should be used to notify the user of an high-level operation
        starting or completing successfully.

        Consider instead using :py:func:`note()` for messages that might be
        helpful, but not necessary for users who are familiar with Depthcharge.
        """
        self.logger.log(INFO, *((self._pfx_info + args[0],) + args[1:]), **kwargs)

    def warning(self, *args, **kwargs):
        """
        Write a warning-level message to the log.

        This should be used to report failures or undesired behavior that can be
        worked around (e.g., by using a slower, less-preferable operation), or
        to otherwise draw a user's attention to an important piece of information
        that *might* be problematic later.
        """
        self.logger.log(WARNING, *((self._pfx_warning + args[0],) + args[1:]), **kwargs)

    def error(self, *args, **kwargs):
        """
        Write an error-level message to the log.

        This should be used to report issues or unexpected behavior that will
        immediately result in a failed operation.
        """
        self.logger.log(ERROR, *((self._pfx_error + args[0],) + args[1:]), **kwargs)


# Create a root logger instance
_depthcharge_root = DepthchargeLog()  # pylint: disable=invalid-name
_depthcharge_root.logger.addHandler(logging.StreamHandler())
_depthcharge_root.level = os.getenv('DEPTHCHARGE_LOG_LEVEL', NOTE)


# Expose root logger for API users
def debug(*args, **kwargs):
    """
    Invokes Depthcharge root logger's :py:meth:`DepthchargeLog.debug()` method'
    """
    _depthcharge_root.debug(*args, **kwargs)


def note(*args, **kwargs):
    """
    Invokes Depthcharge root logger's :py:meth:`DepthchargeLog.note()` method'
    """
    _depthcharge_root.note(*args, **kwargs)


def info(*args, **kwargs):
    """
    Invokes Depthcharge root logger's :py:meth:`DepthchargeLog.info()` method'
    """
    _depthcharge_root.info(*args, **kwargs)


def warning(*args, **kwargs):
    """
    Invokes Depthcharge root logger's :py:meth:`DepthchargeLog.warning()` method'
    """
    _depthcharge_root.warning(*args, **kwargs)


def error(*args, **kwargs):
    """
    Invokes Depthcharge root logger's :py:meth:`DepthchargeLog.error()` method'
    """
    _depthcharge_root.error(*args, **kwargs)


def set_level(level):
    """
    Set Depthcharge's logger to the specified level.

    This may be one of the following integers:

        * `depthcharge.log.DEBUG`
        * `depthcharge.log.NOTE`
        * `depthcharge.log.INFO`
        * `depthcharge.log.WARNING`
        * `depthcharge.log.ERROR`
        * `depthcharge.log.SILENT`

    Alternatively the following strings may be used:

        * ``'debug'``
        * ``'note'``
        * ``'info'``
        * ``'warning'``
        * ``'error'``
        * ``'silent'``

    """
    _depthcharge_root.level = level


def get_level() -> int:
    """
    Get the current level of Depthcharge's logger.
    """
    return _depthcharge_root.level
