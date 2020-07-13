# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
This module contains functionality pertaining to tracking
and reporting the progress of long running operations.

API users should stick to using Depthcharge.create_progress_indicator()
and Depthcharge.close_progress_indicator(), when possible.

When possible, we seek to lazily import dependencies, such that
those who cannot satisfy the dependencies can simply avoid the
use of that corresponding functionality (e.g. tqdm).
"""

from datetime import datetime
from tqdm import tqdm

from . import log


class Progress:
    """
    API users working with a :py:class:`~depthcharge.Depthcharge` context
    object should instead use :py:meth:`.Depthcharge.create_progress_indicator()`.

    This base class implementation is a no-op that can substituted in when API
    usage indicates that no progress should be presented. Otherwise, the
    :py:class:`.ProgressBar` subclass can be used to display the progress status
    of an ongoing operation.

    Basic statistics are recorded internally, however, just to support
    debugging efforts.
    """

    @staticmethod
    def create(total_operations: int, desc: str, **kwargs):
        """
        Create either a ProgressBar or a Progress instance, depending upon the
        the log level. The following levels will result in a progress bar,
        while other levels will not.

        * depthcharge.log.NOTE
        * depthcharge.log.INFO
        * depthcharge.log.WARNING

        Note that the DEBUG level is not included due to emitted information
        being likely to interfere with drawing a progress bar.

        The *total_operations* count indicates how many operations are expected to be tracked by
        this indicator. A 100% completion is displayed when the sum of values provided to
        :py:meth:`.Progress.update()` reaches this value.

        The *desc* string should briefly describe the ongoing operation, in just a few words.
        This will be shown to the user on the displayed progress indicator.

        """
        show  = kwargs.pop('show', True)
        show &= log._depthcharge_root.level in (log.NOTE, log.INFO, log.WARNING)

        if show:
            cls = ProgressBar
        else:
            cls = Progress

            # Just to track hidden progress
            log.debug(desc)

        return cls(total_operations, desc, **kwargs)

    def __init__(self, total_operations: int, desc: str, **kwargs):
        """
        Instantiate an instance of the base Progress object, which effectively
        does nothing but track information for debugging purposes.
        """
        self._desc  = desc
        self._total = total_operations
        self._count = 0
        self._last_update = None
        self._owner = kwargs.get('owner', None)

    def update(self, count=1):
        """
        Record an updated count of operations that have completed since the
        the previous invocation of update().

        i.e. This is relative, not the total since the creation.
        """
        self._last_update = datetime.now()
        self._count += count

    def reset(self, total_operations=None):
        """
        Reset the progress indicator in order to start again.

        If total_operations is not provided, it will be reset with the
        original value passed to the constructor.
        """
        self._count = 0
        self._last_update = None
        if total_operations < 0:
            self._total = total_operations

    def close(self):
        """
        Close and cleanup progress status.
        """
        # Just to detect use-after-close
        self._total = None
        self._desc  = None
        self._count = None

    @property
    def owner(self):
        """
        Value of *owner=* keyword argument provided to Progress constructor, or ``None``.
        This is used to track ownership of the top-level Progress handle in use by a
        :py:class:`depthcharge.Context` object.
        """
        return self._owner


class ProgressBar(Progress):
    """
    This is currently just a simple wrapper around tqdm, intended to maintain a consistent UX across
    usages throughout the Depthcharge codebase.

    In the future, this may migrate to use a different library for progress bar graphics.

    Unless you have a very good reason, do not instantiate this class directly. Either
    use :py:meth:`.Depthcharge.create_progress_indicator()` or :py:meth:`.Progress.create()`.
    """

    def __init__(self, total_operations, desc=None, unit='op', **kwargs):
        # I was brought up on SI unit conventions... I need a space!
        if not unit.startswith(' '):
            unit = ' ' + unit
        super().__init__(total_operations, desc, **kwargs)

        # Remove item not relevant to tqdm
        kwargs.pop('owner', None)

        self._pbar = tqdm(total=total_operations, desc=desc, unit=unit, leave=False, **kwargs)

    def update(self, count=1):
        super().update(count)
        self._pbar.update(n=count)

    def reset(self, total_operations=None):
        super().reset(total_operations)
        self._pbar.reset(total_operations)

    def close(self):
        self._pbar.close()
