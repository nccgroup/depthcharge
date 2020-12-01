.. _api:

Python API
======================

The Depthcharge API is implemented as a ``depthcharge`` module, which consists of
a number of submodules. Much of the functionality one will likely want to interact
with when getting started resides in the top-level :ref:`depthcharge` module
namespace. All of the :ref:`scripts` are built atop of this API, and can be
referenced as examples (in addition to other example code
in the source repository).

.. toctree::
    :maxdepth: 3
    :caption: Contents
    
    depthcharge
    depthcharge.cmdline
    depthcharge.checker
    depthcharge.executor
    depthcharge.hunter
    depthcharge.log
    depthcharge.memory
    depthcharge.monitor
    depthcharge.register
    depthcharge.string
    depthcharge.uboot
