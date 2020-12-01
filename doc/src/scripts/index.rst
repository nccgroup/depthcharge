.. _scripts:

Python Scripts
==============

This section presents the help and usage text for each of the scripts
included with Depthcharge.  This same information can be viewed by
invoking these scripts with a ``-h`` or ``--help`` argument.

When the U-Boot source code for a platform is readily accessible,
the :ref:`audit_config` script can be used to check a platform's
`.config` file (or header file, for older U-Boot versions) for known 
security risks and common product security pitfalls. 

Note that this script is largely just a wrapper around the
:py:class:`~depthcharge.checker.ConfigChecker` functionality in the API. One can
further extend the nature of checks performed by defining more
:py:class:`~depthcharge.checker.SecurityRisk` definitions, registering
additional checks (:py:meth:`~depthcharge.checker.ConfigChecker.register_handler()`)
at runtime, or by creating new :py:class:`~depthcharge.checker.ConfigChecker`
subclasses to perform different types of configuration analyses.

The first script one will usually want to run when working with a 
device is :ref:`inspect`. This script collects information from a device
and stores it into a *device configuration* file specified by a ``-c, --config``
command-line argument. This configuration can be passed other Depthcharge
scripts in order to allow them to skip redundant device inspections before
performing their requested actions. 

The configuration file itself is a simple JSON file, which contains
much of the information one would normally jot down in notes about a device. 
The :ref:`print` script can be used to quickly view all, or a subset of,
information stored in the device configuration file. For example, one might use
this to view a target's environment variables in a fully expanded form (i.e.,
with all variable definitions recursively resolved).

Given the availability of necessary operations, the :ref:`read` and :ref:`write`
scripts can be used to extract data from and write data to target memory
locations. By default, these select the "best" available implementation to do
so. However, those familiar with the :doc:`/api/index` can exercise full
control over these scripts and their underling behavior using the ``--op`` and
``-X, --extra`` arguments.

Once a memory of flash dump has been obtained, either using :ref:`read` or
through a chip-off approach, a few different scripts can be used to locate
different types of data.

The :ref:`cmd` script can be used to locate the U-Boot "linker lists"
containing the console command structures. In situations where a
limited-functionality console is observed, the presence of more than one unique
command table may suggest that functionality is "hidden" or otherwise gated
based upon some form of vendor-specific authentication or "debug enable"
functionality (e.g., GPIO state, a value in a specific flash location).

U-Boot environments (collections of variable definitions) can be
identified and extracted using :ref:`env`. Even when platform designers have
attempted to "lock down" or remove their console interfaces, it is often
the case that these unauthenticated collections of commands can be
tampered with offline and re-written to storage media in order to perform
arbitrary actions on the target. Always keep a lookout for console messages
denoting that a built-in default environment is being used due to an 
invalid CRC32 checksum -- this may indicate that you can inject an environment
at an address normally defined by the U-Boot compile-time ``CONFIG_ENV`` definition, 
with a size defined by ``CONFIG_ENV_SIZE``. The :ref:`mkenv` script can be
used to convert a textual environment description (as seen in ``printenv`` output)
in to its binary form, padded to the correct size and prefixed with the correct
CRC32 checksum. In situations where redundant environments are store, an optional
``--flags`` argument can be used to insert the counter value in the environment
header in order to ensure that your environment is the one marked as in-use.


Flattened `Device Tree <https://www.devicetree.org>`_ (FDT) data structures are
used by U-Boot and the Linux kernel to describe the availability and
configuration of hardware. When taken at face value, these data structures may seem
"uninteresting" to an attacker, but they do provide quite a bit of insight into
memory-mapped peripheral subsystems, drivers in use, and oftentimes pin
multiplexing configurations. Like externally-stored environments, these too
can be overlooked when a platform vendor seeks to authenticate data in a
secure boot flow. In these situations, opportunities to add or tamper with
a `bootargs entry in a chosen node
<https://www.kernel.org/doc/html/latest/devicetree/usage-model.html#runtime-configuration>`_
can be interesting. These data structures can be carved from a binary and converted
to their textual "source" form using the :ref:`fdt` script. Note that the
Device Tree Compiler (dtc) must be installed on your system in order to leverage
dtb-to-dts conversion functionality.

Finally, :ref:`stratagem` allows :py:class:`depthcharge.Stratagem` files to
be produced. These are used by operations such as 
:py:class:`~depthcharge.memory.CRC32MemoryWriter` and
:py:class:`~depthcharge.memory.CpMemoryWriter` to perform the request action,
despite not being able to do so directly. In the case of :py:class:`~depthcharge.memory.CRC32MemoryWriter`,
these means identifying sequences of CRC32 operations that can write a desired
payload to a target memory location. (Refer to the
:py:class:`~depthcharge.hunter.ReverseCRC32Hunter` documentation for information about how
this is achieved.)

As discussed in the :ref:`introduction <intro_api>`, the Depthcharge
:doc:`/api/index` is the primary focus of this project. The scripts presented
here are largely thought of as a means to more conveniently expose the API
functionality for quicker use. As such, users are strongly encouraged to
explore and understand these scripts, along with the underlying API
functionality they use.

.. _audit_config:


depthcharge-audit-config
------------------------

.. literalinclude:: depthcharge-audit-config.txt
    :language: text

.. _inspect:

depthcharge-inspect
-------------------

.. literalinclude:: depthcharge-inspect.txt
    :language: text

.. _print:

depthcharge-print
-------------------

.. literalinclude:: depthcharge-print.txt
    :language: text

.. _read:

depthcharge-read-mem
--------------------

.. literalinclude:: depthcharge-read-mem.txt
    :language: text

.. _write:

depthcharge-write-mem
----------------------

.. literalinclude:: depthcharge-write-mem.txt
    :language: text


.. _cmd:

depthcharge-find-cmd
----------------------

.. literalinclude:: depthcharge-find-cmd.txt
    :language: text


.. _env:

depthcharge-find-env
----------------------

.. literalinclude:: depthcharge-find-env.txt
    :language: text

.. _mkenv:

depthcharge-mkenv
------------------

.. literalinclude:: depthcharge-mkenv.txt
    :language: text


.. _fdt:

depthcharge-find-fdt
----------------------

.. literalinclude:: depthcharge-find-fdt.txt
    :language: text


.. _stratagem:

depthcharge-stratagem
----------------------

.. literalinclude:: depthcharge-stratagem.txt
    :language: text
