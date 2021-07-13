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


Console Quirks
~~~~~~~~~~~~~~

As documented in the :py:class:`~depthcharge.Console` class, there are
two timing parameters that you may find yourself needing to adjust if a device
is inducing strange failures: the Console *timeout* and an optional
intra-character delay (*intrachar*). Both can be specified programatically 
as keyword arguments to the 

Timeout
=======

If you feel that operations are just running sluggishly, but there's not
any particular failure, you can try reducing the Console timeout via the
`DEPTHCHARGE_CONSOLE_TIMEOUT` environment variable. The following (Bash)
example sets a timeout of 15 ms prior to invoking `depthcharge-readmem`.

.. code-block:: text

    $ export DEPTHCHARGE_CONSOLE_TIMEOUT=0.015
    $ depthcharge-readmem -c mydevice.cfg -a 0xa800_6000 -l 1024


However, if you set this timeout too low, you may find that Depthcharge
is reporting timeouts before a device has responded with all of the
expected output. 

Intracharacter Delay
====================

Another snag one might encounter is that a device's UART FIFO may `fill and drop data`_
if the device isn't able to consume console input quickly enough. From Depthcharge's
perspective, this will likely manifest as commands failing with the commands
being partially echoed (incorrectly) in Monitor output.

The optional *intrachar* Console parameter and associated
`DEPTHCHARGE_CONSOLE_INTRACHAR` environment variable can be used to add an
intra-byte delay between each byte sent via the UART. No such delay is 
added by default.

The value of this parameter is treated as a lower bound because there will be
some implicit added overhead just by virtue of performing `write()` and
`flush()` on a per-byte basis when sending data to the serial port.  
*(In contrast, when this feature is not enabled - i.e. the default - data is written
in its entirety to the host's corresponding serial device. The underlying driver and
hardware ultimately is responsible for how much time, if any, occurs between succesive
bytes.*)

In cases where you need to use this, you may find that it's sufficient to
specify value of `0` - this will just incur the implicit overhead without
performing any additional `sleep()` between attempts to write to the serial
port.

.. _fill and drop data: https://twitter.com/sz_jynik/status/1414989128245067780
