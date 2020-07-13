Troubleshooting
---------------

U-Boot versions and configurations will vary across target devices, especially
when OEMs and vendors have introduced their own modifications. Although we'd
like to make Depthcharge as robust as time permits, we'll never be able to
ensure it works as intended on every platform out there.

Thus, we expect that users will have to do some occasional troubleshooting
when they encounter issues.  If you reach out via the `issue tracker`_,
we'll very likely ask for the two pieces of information shown here.

Debug Log Output
~~~~~~~~~~~~~~~~

Depthcharge defaults to a log level of "note", which is one level more verbose than
the "info" level. The most verbose output can be obtained by setting the log level to "debug".
Additionally, when the debug level is set, the Depthcharge scripts will print traceback
output if any unexpected errors occur.

The log level can be via the ``DEPTHCHARGE_LOG_LEVEL`` environment variable or by
the :py:func:`depthcharge.log.set_level()` function. The following example shows
the former approach being used to redirect log output to a ``log.txt``.


.. code-block:: text

    $ export DEPTHCHARGE_LOG_LEVEL=debug
    $ depthcharge-read-mem -c my_device.cfg -a 0x87f4_0124 -l 128 2> log.txt

.. _issue tracker: https://github.com/nccgroup/depthcharge/issues


Monitor Log
~~~~~~~~~~~

If an unexpected failure occurs in Depthcharge core code, it may be the case
that some logic or parsing code is not accounting for differences between the
version of U-Boot installed on your target device, and those previously tested.

The easiest way to get to the bottom of this is to capture all data communicated
over the serial console interface before and up to the failure. This can be
done using a :py:class:`~depthcharge.monitor.FileMonitor` to log this data to
a file, as shown below.

.. code-block:: text

    $ depthcharge-inspect -c my_device.cfg -m file:monitor.txt

