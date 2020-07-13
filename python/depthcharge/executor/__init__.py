# flake8: noqa=F401
"""
The *depthcharge.executor* module provides :py:class:`~depthcharge.Operation`
implementations responsible for executing code. Currently, this is limited to the use of the ``go``
console command by way of the :py:class:`~deptcharge.executor.GoExecutor` implementation.

However, this module is intended of accommodate future additions, such as:

* Support for automatically wrapping payloads with image headers and executing them with ``boot*``
  family of console commands.

* Memory corruption exploitation and shellcode helper functions.

  * Given that custom vendor/oem commands will vary wildly, these would be more valuable as generic
    building blocks, rather than a collection of device-specific payloads.

  * Executor implementations pertaining to upstream vulnerabilites
    (e.g. `NFS <https://securitylab.github.com/research/uboot-rce-nfs-vulnerability>`_
    `RCEs <https://github.com/f-secure-foundry/usbarmory/blob/master/software/secure_boot/Security_Advisory-Ref_IPVR2018-0001.txt>`_)
    may however, be more practical to readily integrate.


* Similar to the above, integrating support for
  `upstream <https://labs.f-secure.com/advisories/das-u-boot-verified-boot-bypass>`_ and
  `silicon-specific <https://github.com/f-secure-foundry/usbarmory/blob/master/software/secure_boot/Security_Advisory-Ref_QBVR2017-0001.txt>`_
  secure boot bypasses may also be reasonable additions.

"""

from .executor  import Executor
from .go        import GoExecutor
