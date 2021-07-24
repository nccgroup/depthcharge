# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
The "top-level" of the Depthcharge's target interaction API is implemented by the
:py:class:`~depthcharge.Depthcharge` class. This encapsulates all underlying state and exposes
wrappers to functionality implemented by the various submodules. An
instance of :py:class:`~depthcharge.Depthcharge` effectively represents a "context handle".
One will perform most, if not all, actions on a target using this handle and should
prefer its use over direct instantiation and interaction with the lower-level classes.
(*There will be exceptions; this is just best practice guidance offered to encourage portability
and compatibility over any API updates.*)


In the simplest case, creating a handle consists of two steps:

1. Attaching to the target console by creating a :py:class:`~depthcharge.Console` instance.
2. Creating a :py:class:`~depthcharge.Depthcharge` context, passing the
   :py:class:`~depthcharge.Console` instance as an argument.

The creation of the :py:class:`~depthcharge.Depthcharge` context results in an initial inspection
of the target device so that Depthcharge can determine what functionality is available. If
any inspection operations require deployment of executable payloads (and any necessary memory write
operations are detected) these payload will be deployed to memory at this time. Otherwise, payloads
will be deployed on an as-needed basis when :py:class:`~depthcharge.Depthcharge` methods are
invoked.

A boilerplate example is shown below:

.. literalinclude:: ../../../python/examples/boilerplate_create_ctx.py

Observe that the :py:class:`Depthcharge.save() <depthcharge.Depthcharge.save>` method is used
to save information collected in the context object to a *"device configuration file"*.
This is a JSON-formatted file that can be used to later create a
:py:class:`~depthcharge.Depthcharge` object using the static
:py:class:`Depthcharge.load() <depthcharge.Depthcharge.load>` method. This results in a much
quicker object creation, given that device inspection is not needed to
initialize the context state. Below is an example usage of :py:class:`Depthcharge.load()
<depthcharge.Depthcharge.load>`.

.. code:: python

    console = Console('/dev/ttyUSB0', baudrate=115200)
    ctx = Depthcharge.load('my_device.cfg', console)

With a context object in hand, one can being interacting with a target device using
the API methods documented here. Refer to both the scripts present in
Depthcharge's `python/examples <https://github.com/nccgroup/depthcharge/python/examples>`_
directory, as well as the implementation of its various utility scripts for some additional
examples.

Context creation involving the use of a :py:class:`~depthcharge.Companion` device or a console
monitor (via :py:mod:`depthcharge.monitor`) is discussed in their respective modules and classes.

As a final note, the Depthcharge API makes a fairly heavy usage of keyword arguments (``**kwargs``).
These are propagated downward these from top-level calls to lower level implementations.
While this isn't a great design practice for most software projects, this decision was made to
better facilitate the use of Depthcharge as "a tool for quickly building your own tools." The intent
is to allow API users to pass parameters (whether programmatically or as obtained from command-line
arguments) to underlying operations in order to tweak behavior without much effort.

This is exemplified by the ``depthcharge-stratagem`` script providing the ``-X, --extra``
command-line parameter, which allows the user to tweak the values of the ``revlut_maxlen`` parameter
of the :py:class:`~depthcharge.hunter.ReverseCRC32Hunter` constructor and the ``max_iterations``
parameter of
:py:meth:`ReverseCRC32Hunter.build_stratagem() <depthcharge.hunter.ReverseCRC32Hunter.build_stratagem>`.
Thus, familiarity with other parts of the Depthcharge API documentation is still very helpful,
even if you're only using provided scripts.
"""

import json
import os
import re

from copy import deepcopy
from datetime import datetime

from .version import __version__

from . import log
from . import uboot

from .arch          import Architecture
from .console       import Console
from .executor      import Executor
from .memory.reader import MemoryReader
from .memory.writer import MemoryWriter
from .memory.patch  import MemoryPatch, MemoryPatchList
from .operation     import OperationSet, OperationFailed, OperationNotSupported
from .payload_map   import PayloadMap
from .progress      import Progress
from .register      import RegisterReader
from .stratagem     import Stratagem


_FAILURE_STRINGS = (
    'data abort',
    '## Error',
    ' ERROR',
    'Unknown command',
    'Usage:'
)


class Depthcharge:
    """
    This class represents a context handle for the top-level target interaction API.

    The *console* argument is required by the Depthcharge constructor. It will be used
    by the context handle to interact with the target in future operations. It may either be an
    initialized :py:class:`~depthcharge.Console` instance or a string that can be passed directly to the
    :py:class:`~depthcharge.Console` constructor to create a new instance.

    If a companion device is necessary to perform desired actions, an initialized
    :py:class:`~depthcharge.Companion` device handle can be passed via *companion*.

    **Keyword Arguments:**

    :Retrieve detailed help text: When inspecting a device, the Depthcharge constructor will not
        read detailed help text. This can be achieved by passing a *detailed_help=True*
        keyword argument to the constructor or by making a later call to
        :py:meth:`commands()` with *detailed=True*.

    :Allow payload deployment & execution: If *allow_deploy=True*, Depthcharge will attempt
        to deploy and execute payloads in memory, when neccessary. Specifying
        *allow_deploy=True* will always force payloads to be deployed; this overrides
        (and therefore ignores) whatever is set for the following *skip_deploy* parameter.

    :Skip payload deployment, but allow execution: When performing the same operations on a device
        repeatedly, the deployment of executable payloads may be redundant and waste time.  This can
        be disabled by providing a *skip_deploy=True* keyword argument.

        **Important**, the target will crash if an attempt is made to execute a payload that has not
        been previously deployed.

        Specifying *skip_deploy=True` implies that one wishes to execute payloads.
        If this is not true -- you want no payload deployment and no execution --
        then *allow_deploy=False* is what you're looking for.

    :Payload location: By default, payloads are staged 32 MiB beyond the
        target's ``$loadaddr`` location. To override this location, either
        alternative absolute address can be provided in a *payload_base*
        keyword argument.  Alternatively, the offset from the payload base address can
        be provided via *payload_offset*.

    :Crash/Reboot behavior: Some operations, such as
        :py:class:`~depthcharge.register.DataAbortRegisterReader` subclasses,
        need to crash platform (assuming it will automatically reboot) in order
        to perform their duty. If crashing or rebooting the platform is
        undesirable, specify *allow_reboot=False* to exclude these from the
        "available operations" lists. Alternatively, a user-provided callback
        function can be specified via the *post_reboot_cb* keyword argument.
        This function will be invoked after the reboot occurs. **The callback
        function is responsible for calling** :py:meth:`interrupt()` in order
        to catch the U-Boot prompt. (This is intended to allow any other
        prerequisites, such as sending an autoboot "stop string", to occur
        within the callback.) The callback function takes a single argument,
        which can be provided via the *post_reboot_cb_data* keyword argument.
        If you would like to pass the Depthcharge context being created by this
        constructor, specify the string ``'self'``.
    """

    _default_arch = 'generic'  # 32-bit, little endian
    _ver_re   = re.compile(r'^U-Boot\s+[0-9]{4}\.[0-9]{2}')

    def __init__(self, console, companion=None, **kwargs):
        self.args = kwargs
        self.companion = companion

        if isinstance(console, str):
            self.console = Console(console)
        elif console is None:
            self.console = Console()
        else:
            self.console = console

        self.arch = Architecture.get(kwargs.get('arch', self._default_arch) or self._default_arch)
        log.debug('Architecture: ' + self.arch.description)

        # Is the user allowing us to reboot or reset the platform?
        self._allow_reboot = kwargs.get('allow_reboot', False)

        self._post_reboot_cb = kwargs.get('post_reboot_cb', None)
        self._post_reboot_cb_data = kwargs.get('post_reboot_cb_data', None)

        # Bit of a hack to allow user to pass the context that they're in the process of creating.
        if self._post_reboot_cb_data == 'self':
            self._post_reboot_cb_data = self

        # Reference to object currently displaying status
        self._progress_owner = None

        # The following '_<kwarg>` items are used when creating a
        # Depthcharge context from a JSON file. These are not intended
        # for use by API users.

        # Expected prompt, if already known
        if self.console.prompt is None and '_prompt' in kwargs:
            self.console.prompt = kwargs['_prompt']

        if self.console.prompt is not None:
            log.note('Expected U-Boot prompt: ' + self.console.prompt)

        # Available commands
        self._cmds = kwargs.get('_cmds', None)

        # Executable payloads we can jump into
        # "Standalone Applications" in U-Boot parlance
        self._payloads = None

        # Contents of U-Boot environment
        self._env = kwargs.get('_env', None)

        # Target device version number
        self._version = kwargs.get('_version', None)

        # Our collections of available operations. These are initialized
        # as empty sets, which we will fill later in this constructor.
        #
        # Important: Do not rename these attributes.
        # Common logic in _enumerate_operations() uses setattr and getattr.
        self._exec  = OperationSet(suffix='Executor')
        self._memrd = OperationSet(suffix='MemoryReader')
        self._memwr = OperationSet(suffix='MemoryWriter')
        self._regrd = OperationSet(suffix='RegisterReader')

        # Our rough interpretation of the bootloaders' global data structure...
        # or rather, what little of it we're interested in. This will be
        # populated as-needed by operations or when related methods are invoked
        # to collect information.
        self._gd = kwargs.get('_gd', {})

        # Are we permitted to deploy executable payloads as-needed?
        self._allow_deploy_exec = kwargs.get('allow_deploy', False)

        # Should we assume that payloads are already deployed?
        self._skip_deployment = kwargs.get('skip_deploy', False)

        # Reconcile desired behavior, based upon what was explicitly
        # specified, implied, or being defaulted. See the function doc comments.

        if 'allow_deploy' in kwargs:  # User specified, not default value
            self._skip_deployment = False
            # For any explicit usage, whether True or False, allow_deploy takes precendence and
            # resuls in deployment + exec skip_deploy only has an effect when the user does not
            # specify this param.

        elif self._skip_deployment:
            # Skipping deployment still implies exec
            self._allow_deploy_exec = True

        # Our payload map will be initializde during the following active
        # initialization portion of this constructor.
        self._payloads = None

        # Where should we place our payloads?
        # If not specified, we'll used an offset from ${loadaddr} as to avoid
        # stomping on stuff that we actively may wish to tamper wtih.
        self._payload_base = kwargs.get('payload_base', 'loadaddr')
        if 'payload_base' not in kwargs:  # We used the loadaddr default...
            log.note('Using default payload base address: ${loadaddr} + 32MiB')
            self._payload_off = 32 * 1024 * 1024
        else:
            self._payload_off = kwargs.get('payload_offset', 0)

        # Perform initializations involve interaction with the underlying
        # device. This has been split just to afford us an opportunity to
        # suppress or defer this, should such an API change ever be necessary.
        self._perform_active_init(**kwargs)

        # With some future additions, we could either directly determine
        # or deduce the architecture here, if we're still using a Generic* arch.
        #
        # From there, we can re-init accordingly.
        #
        # For now, just warn that functionality may be limited with Generic*
        if 'Generic' in self.arch.name:
            m = 'Using {:s} architecture. Functionality may be limited without more specific architecture.'
            log.warning(m.format(self.arch.name))

    def _perform_active_init(self, **kwargs):
        """
        Helper for __init__() that performs active initialization operations.
        (i.e. those that interact with a target and mutate state.)
        """
        # Attempt to interrupt device and attach to console
        self.console.interrupt()

        # Read and cache available commands and environment variables
        # if we didn't already pull them in from "private" keyword args
        self.commands(detailed=kwargs.get('detailed_help', False))
        self.environment()

        # Establish our payload base address by resolving either an environment
        # variable read from the target device or using a user-provided address
        try:
            payload_map_base = self._resolve_payload_base()
        except OperationFailed:
            self._allow_deploy_exec = False
            self._skip_deploy = False
            payload_map_base = 0
            log.warning('Disabling payload deployemnt and execution due to error(s).')

        self._payloads = PayloadMap(self.arch, payload_map_base,
                                    skip_deploy=self._skip_deployment)

        # Retrieve and cache version information, if not provided earlier
        self.version()

        # Enumerate available operations
        #
        # The order in which this is performed is intentional, and according to
        # inherent dependencies - i.e. we must write memory to execute custom
        # code. If things get more complicated, we might have to do some
        # smarter dependency resolution.
        self._enumerate_memory_writers(**kwargs)
        self._enumerate_operations(MemoryReader, '_memrd', **kwargs)
        self._enumerate_operations(Executor, '_exec', **kwargs)
        self._enumerate_operations(RegisterReader, '_regrd', **kwargs)

        # Attempt inspection of gd structure and substructures of interest
        try:
            _ = self.uboot_global_data(**kwargs)
        except OperationNotSupported as error:
            log.warning(str(error))

    def _resolve_payload_base(self):
        """
        Resolve self._payload_base string based upon environment vars, if needed.
        """
        if isinstance(self._payload_base,  str):
            try:
                expanded = uboot.env.expand_variable(self._env, self._payload_base)
                self._payload_base = int(expanded, 0)
            except KeyError:
                msg = 'Environment variable used for payload_base does not exist: {:s}'
                raise OperationFailed(msg.format(self._payload_base))
            except ValueError:
                msg = 'Encountered invalid expansion of payload_base: ' + expanded
                raise OperationFailed(msg)

        msg = 'Depthcharge payload base (0x{:08x}) + payload offset (0x{:08x}) => 0x{:08x}'
        actual_base = self._payload_base + self._payload_off
        log.note(msg.format(self._payload_base, self._payload_off, actual_base))
        return actual_base

    @staticmethod
    def _log_not_supported(err):
        # Warn for situations where more functionality would be available if
        # the user had provided
        msg = '  Excluded:  ' + str(err)
        if 'companion' in msg or 'opt-in not specified' in msg:
            log.warning(msg)
        else:
            log.note(msg)

    def _enumerate_memory_writers(self, **kwargs):
        """
        Determine the available MemoryWriter implementations based upon
        available commands and their dependencies.

        This is an __init__() helper that modifies the context state.
        Usage elsewhere may have unintended side-effects.
        """
        log.note('Enumerating available MemoryWriter implementations...')
        for cls in MemoryWriter.implementations():
            try:
                writer = cls(self, **kwargs)
                if len(writer.required['payloads']) != 0:
                    # TODO: Check if we have a dep-less writer to bootstrap a
                    # payload-based writer. If we have a lot of data to write,
                    # but only a limited write primitive, this might make sense
                    # to add. Not doing this until there's a clear
                    # need or use-case, though...
                    err = 'A memory writer with a payload requirement is not currently supported'
                    raise OperationNotSupported(writer, err)

                self._memwr.add(writer)
                log.note('  Available: ' + writer.name)
            except OperationNotSupported as e:
                self._log_not_supported(e)

    def _enumerate_operations(self, base_cls, attr_pfx, **kwargs):
        """
        Determine the available Operation implementations based upon
        available commands and their dependencies.

        This is an __init__() helper that modifies the context state.
        Usage elsewhere may have unintended side-effects and will
        almost certainly result in you Having a Bad Time.
        """
        base_name = base_cls.__name__
        op_set = getattr(self, attr_pfx)

        log.note('Enumerating available ' + base_name + ' implementations...')

        # Resolve available implementations
        for subclass in base_cls.implementations():
            try:
                impl = subclass(self, **kwargs)
                required_payloads = impl.required['payloads']
                if len(required_payloads) > 0:
                    if len(self._memwr) == 0:
                        msg = 'No MemoryWriter available to deploy required payload(s)'
                        raise OperationNotSupported(impl, msg)

                    if not self._allow_deploy_exec:
                        msg = 'Payload deployment+execution opt-in not specified'
                        raise OperationNotSupported(impl, msg)

                for payload in required_payloads:
                    self._payloads.mark_required_by(payload, impl)

                if issubclass(subclass, Executor) and not self._allow_deploy_exec:
                    msg = 'Payload deployment+execution opt-in not specified'
                    raise OperationNotSupported(impl, msg)

                op_set.add(impl)
                log.note('  Available: ' + impl.name)

                if required_payloads:
                    log.debug('    Requires payloads: ' + str(required_payloads))

            except OperationNotSupported as e:
                self._log_not_supported(e)

    def create_progress_indicator(self, owner, total_operations: int, desc: str, **kwargs):
        """
        Create a progress indicator and register it with the Depthcharge context.

        By using this method, as opposed to invoking :py:meth:`.Progress.create()` manually,
        it ensures that only this progress indicator will be displayed. Any progress indicators
        associated with underlying operations will be hidden.

        The *owner* argument must be an object instance or a unique identifier. This is used to
        track progress indicator registration. As an API user, you may simply use a string
        such as ``'user'`` or ``'script'`` -- these will not collide with values used by
        internal code.

        The *total_operations* count indicates how many operations are expected to be tracked by
        this indicator. A 100% completion is displayed when the sum of values provided to
        :py:meth:`.Progress.update()` reaches this value.

        The *desc* string should briefly describe the ongoing operation, in just a few words.
        This will be shown to the user on the displayed progress indicator.

        The return value is a :py:class:`~depthcharge.Progress` handle, initialized according to the
        provided keyword arguments.

        .. code-block:: python

            from time import sleep

            progress = ctx.create_progress_indicator('script', 64, 'Example Operation')
            for i in range(0, 64):
                progress.update()  # Passes default count value of 1 when not specified
                sleep(0.25)

            ctx.close_progress_indicator(progress)

        """
        if owner is None:
            raise ValueError('The owner argument cannot be None')

        kwargs['owner'] = owner
        if self._progress_owner is None:
            self._progress_owner = owner
            return Progress.create(total_operations, desc, **kwargs)

        kwargs['show'] = False
        return Progress.create(total_operations, desc, **kwargs)

    def close_progress_indicator(self, progress):
        """
        Close and relinquish control over a progress indicator. This will allow other progress
        indicators to be displayed again.

        All :py:meth:`create_progress_indicator()` invocations must have a corresponding call to
        this method.
        """
        progress.close()
        if isinstance(progress.owner, (str, int)) and self._progress_owner == progress.owner:
            self._progress_owner = None
        elif self._progress_owner is progress.owner:
            self._progress_owner = None

    @staticmethod
    def _check_response_for_error(resp: str):
        """
        Raise an OperationFailed exception if `resp` contains an
        entry from _FAILURE_STRINGS.
        """
        for err in _FAILURE_STRINGS:
            if err in resp:
                raise OperationFailed(resp)

    @staticmethod
    def load(filename: str, console, **kwargs):
        """
        Create and return a Depthcharge object from the JSON data included in the
        specified file, previously generated by :py:meth:`save()`.
        """
        with open(filename, 'r') as infile:
            return Depthcharge.from_json(infile.read(), console, **kwargs)

    @classmethod
    def from_json(cls, json_str: str, console, **kwargs):
        """
        Create and return a Context object from the provided JSON data,
        previously created by :py:meth:`to_json()`.
        """
        ctx = json.loads(json_str)

        # Allow these items to be overridden on load
        if 'payload_base' not in kwargs and 'payload_base' in ctx:
            kwargs['payload_base'] = ctx['payload_base']

        if 'payload_offset' not in kwargs and 'payload_offset' in ctx:
            kwargs['payload_offset'] = ctx['payload_offset']

        return cls(console,
                   arch=kwargs.pop('arch', ctx['arch']),
                   _version=ctx['version'],
                   _cmds=ctx['commands'],
                   _env=ctx['env_vars'],
                   _prompt=ctx['prompt'],
                   _gd=ctx['gd'],
                   **kwargs)

    def to_json(self, timestamp=True, comment=None, **kwargs) -> str:
        """
        Serialize a depthcharge Depthcharge object so that it can be later recreated
        via the :py:meth:`from_json()` method.
        """
        output = {
            'arch': self.arch.name,
            'baudrate': self.console.baudrate,
            'version': self._version,
            'prompt': self.console.prompt,
            'commands': self._cmds,
            'env_vars': self._env,
            'payload_base': self._payload_base,
            'payload_offset': self._payload_off,
            'gd': self._gd,
        }

        if timestamp:
            output['depthcharge_timestamp'] = datetime.now().isoformat()

        if comment is not None:
            output['depthcharge_comment'] = comment

        output['depthcharge_version'] = __version__

        # Default to a human readable file
        if 'indent' not in kwargs:
            kwargs['indent'] = 4

        return json.dumps(output, **kwargs)

    def save(self, filename, timestamp=True, comment=None):
        """
        Serialize the current configuration of the current Depthcharge context
        to a JSON object and write it to the provided filename.
        """
        log.note('Saving depthcharge configuration state to ' + filename)
        s = self.to_json(timestamp, comment)
        with open(filename, 'w') as outfile:
            outfile.write(s)

    @property
    def prompt(self) -> str:
        """
        Target's (expected) U-Boot console prompt string, as provided by
        the underlying :py:class:`depthcharge.Console` object.
        """
        return self.console.prompt

    def send_command(self, *args, **kwargs) -> str:
        """
        Send a command to the target console.

        If a *check=True* keyword argument is provided, this method will check the response data for
        strings indicative of a failure and raise an :py:exc:`~depthcharge.OperationFailed`
        exception on error. Otherwise, it is the caller's responsibility to inspect the returned
        response data for content indicative of success or failure.

        If an *expected=<str>* keyword argument is provided, this method will raise a
        :py:exc:`ValueError` if the response does not match the expected value. If a
        string is provided, a string comparison is performed in a case-insensitive manner, with
        leading and trailing whitespace stripped.

        If *expected=<re.Pattern>* is provided with a compiled regular expression, then the
        :py:meth:`re.match()` will be applied to the response. A :py:exc:`ValueError` will
        be raised if the response does not match the provided pattern.

        **Example:** *Retrieving a Device Tree from NAND*

        .. code:: python

            # Determine command success based upon re.match() of expected response
            success_pattern = re.compile(r'NAND read:.*: OK.*', re.MULTILINE|re.DOTALL)
            ctx.send_command('nand read $dtb_addr $dtb_offset $dtb_size', expected=success_pattern)

            # Check for success using Depthcharge's limited builtin failure response checks
            ctx.send_command('fdt addr $dtb_addr', check=True)

            # Alternatively, we could confirm success by verifying that the response is
            # an empty string.
            # ctx.send_command('fdt addr $dtb_addr', expected='')

            # Just take the response data without checks
            dts = ctx.send_command('fdt print')
            print(dts)

        """
        check = kwargs.pop('check', False)
        expected = kwargs.pop('expected', None)

        resp = self.console.send_command(*args, **kwargs)
        if resp is not None:
            if check:
                self._check_response_for_error(resp)

            if expected is not None:
                failure = False

                if isinstance(expected, str):
                    failure = resp.lower().strip() != expected.lower().strip()
                elif isinstance(expected, re.Pattern):
                    failure = not expected.match(resp.strip())
                else:
                    raise TypeError('Invalid type provided for `expected` keyword')

                if failure:
                    msg = 'Did not receive expected response. Got: ' + resp
                    raise ValueError(msg)

        elif expected is not None:
            raise ValueError('Did not receive a response. Expected: ' + expected)

        return resp

    def interrupt(self, interrupt_str='\x03', timeout=30.0):
        """
        This is a convenience wrapper around :py:meth:`depthcharge.Console.interrupt()`.
        """
        self.console.interrupt(interrupt_str, timeout)

    def commands(self, cached=True, detailed=False) -> dict:
        """
        Return a dictionary containing information about commands supported by
        the target's U-Boot console environment.

        If *cached=True*, any previously recorded information is returned. Otherwise,
        it will be actively obtained from the device.

        The command names are stored as dictionary keys. Each command entry
        is its own dictionary containing a *summary* value, which is a
        brief description of the command. If *detailed=True*, additional help
        text is stored in a *details* value.
        """

        if self._cmds is not None and cached:
            if not detailed:
                # We may or may not have detailed info. Excess info
                # is fine; the user can ignore it.
                return deepcopy(self._cmds)

            # Use any command to determine if we have detailed help info
            name = list(self._cmds)[0]
            have_details = 'details' in self._cmds[name]

            # We have the requested details
            if have_details:
                return deepcopy(self._cmds)

            # Otherwise, we need to carry on to collect more info.

        regex = re.compile(r'(?P<cmd>[a-zA-Z0-9_]+)\s*-?\s*(?P<summary>.*)')

        if detailed:
            log.note('Retrieving detailed command info via "help"')
        else:
            log.note('Retrieving command list via "help"')

        cmds = {}
        help_text = self.send_command('help')
        for line in help_text.splitlines():
            entry = {}
            m = regex.match(line)
            if m is not None:
                cmd = m.group('cmd')
                entry['summary'] = m.group('summary')

                cmds[cmd] = entry

        if not cmds:
            raise IOError("Failed to retrieve command list via help")

        if detailed:
            desc = 'Reading console command help text'
            unit = 'cmd'
            progress = self.create_progress_indicator(self, len(cmds), desc, unit=unit)
            try:
                for cmd in cmds:
                    log.debug('Reading help text for: ' + cmd)
                    progress.update()
                    entry['details'] = self.send_command('help ' + cmd)
            finally:
                self.close_progress_indicator(progress)

        # Update write-through cache
        self._cmds = cmds
        return deepcopy(self._cmds)

    def environment(self, cached=True) -> dict:
        """
        Return the target's environment variables as a dictionary.

        By default, any previously cached results are returned. Specify *cached=False* in order to
        force their retrieval from the target device.

        Note that all values in the returned dictionary are strings. The caller is responsible for
        performing any necessary type conversions.

        Upon failure, an error will be logged and an empty dictionary will be returned.
        """

        if self._env is not None and cached:
            return self._env

        log.note('Reading environment via "printenv"')

        self.console.interrupt()
        env_text = self.send_command('printenv')

        try:
            self._env = uboot.env.parse(env_text)
        except ValueError as e:
            log.error('Failed to parse environment: ' + str(e))
            self._env = {}

        return self._env

    def env_var(self, name: str, expand=True, cached=True, convert_int=True, **kwargs):
        """
        Retrieve the value of an environment variable, specified by *name*.

        If *expand=True*, the environment variable definition will be "expanded"
        such that any other variables in its definitions will be fully resolved.

        If *cached=True* (default), the result is returned from cached environment data.
        Otherwise, the device will be queried for this information.

        If *convert_int=True*, this method will attempt to return environment
        variables containing only an integer as an ``int`` type. Otherwise, the
        value will be returned as a ``str``.
        """
        if not cached:
            # Might as well just grab the entire env while we're at it.
            # Can't think of a use-case for repeated non-cached reads.
            # I suppose ${filesize} will change each time certain commands are run...
            self.environment(cached=False)

        if expand:
            ret = uboot.env.expand_variable(self._env, name, **kwargs)
        else:
            ret = self._env[name]

        if convert_int:
            try:
                return int(ret, 0)
            except ValueError:
                pass

        return ret

    def set_env_var(self, name: str, value, invalidate_cache=True):
        """
        Set the environment variable (whose name is specifeid by *name*) to the provided *value*.

        If *value* is an integer, it will be convered to a string, formatted as a hexadecimal value
        prefixed with *0x*.

        Otherwise, the value is assumed to be a string and is set as-is.

        The caller is responsible for escaping the variable contents appropriately.

        The *invalidate_cache* argument forces readback of the entire environment
        into Depthcharge's local cache when set to ``True.``  When setting a handful
        of variables in succession, you may set it to ``False`` for all but the final
        :py:meth:`set_env_var()` call.

        """
        if isinstance(value, int):
            value = '0x{:08x}'.format(value)
        elif isinstance(value, str):
            pass
        else:
            raise TypeError('Value must be a string or integer. Got ' + type(value).__name__)

        self.send_command('setenv ' + name + ' ' + value, check=True)
        log.note('Set environment variable: {:s}={:s}'.format(name, value))

        # Re-read entire environment so we can update out cache and expand future vars appropriately
        if invalidate_cache:
            # cached=False forces update of self._env
            self.environment(cached=False)

    def version(self, cached=True, allow_reset=True) -> list:
        """
        Return the target's version information as a list.

        By default, this is cached information. Set *cached=False* to force it to be actively
        retrieved from a device.

        If the `version` command is not available and *allow_reset=True* (the default),
        the target will be reset in an attempt to retrieve this information.
        """

        if self._version is not None and cached:
            return self._version

        if 'version' in self._cmds:
            # Preferred, as we get some compiler and linker versions
            resp = self.console.send_command('version')
            self._version = resp.splitlines()
            if len(self._version) >= 1:
                log.note('Version: ' + self._version[0])
            return self._version

        if 'reset' in self._cmds and allow_reset:
            log.note('Reseting device to search for version string.')
            self.console.send_command('reset', read_response=False)
            lines = self.console.interrupt().splitlines()
            for line in lines:
                if self._ver_re.match(line):
                    self._version = [line.strip()]
                    log.note('Version: ' + self._version[0])
                    return self._version

            log.warning('Did not see U-Boot version string. Old or non-standard version format?')

        else:
            log.warning('Unable to query U-Boot version string.')
            self._version = ['unknown']

        self._version = ['unknown']
        return self._version

    @property
    def register_readers(self):
        """
        An iterable collection of all available :py:class:`~depthcharge.register.RegisterReader`
        implementations.
        """
        return self._regrd

    def _reg_rd_impl(self, args_dict):
        try:
            impl = args_dict.pop('impl')
            return self._regrd.find(impl)
        except (KeyError, TypeError):
            return self._regrd.default()

    def _read_memory_impl(self, data_len, args_dict):
        try:
            impl = args_dict.pop('impl')
            return self._memrd.find(impl)
        except (KeyError, TypeError):
            return self._memrd.default(data_len=data_len)

    def default_register_reader(self, **kwargs):
        """
        Return the :py:class:`~depthcharge.register.RegisterReader` that will be used if no
        implementation is specified via the `impl=` keyword argument when :py:meth:`read_register()`
        is invoked.

        Raises :py:exc:`~depthcharge.OperationNotSupported` if no register readers are available.
        """
        return self._regrd.default(**kwargs)

    def read_register(self, register, **kwargs) -> int:
        """
        Read a register and return its value.
        """
        impl = self._reg_rd_impl(kwargs)
        return impl.read(register)

    @property
    def memory_readers(self):
        """
        This property provides an iterable collection of all available
        :py:class:`~depthcharge.memory.MemoryReader` implementations.
        """
        return self._memrd

    def default_memory_reader(self, **kwargs):
        """
        Return the :py:class:`~depthcharge.memory.MemoryReader` that will be used if no
        implementation is specified via the `impl=` keyword argument when :py:meth:`read_memory()`
        is invoked.

        This most suitable default may change with respect to the amount of data being read.  If the
        amount of data to read is known, pass this integer value via a *data_len* keyword argument.

        Raises :py:exc:`~depthcharge.OperationNotSupported` if no memory readers are available.
        """
        return self._memrd.default(**kwargs)

    def read_memory(self, address: int, size: int, **kwargs) -> bytes:
        """
        Read *size* bytes at the specified memory *address* and return the data.

        An optional *impl* keyword argument may specified to override the default memory read
        operation and use a specific :py:class:`~depthcharge.memory.MemoryReader` implementation (by
        name) to perform this operation. Either a single name or a list of names, can be provided.

        .. code:: python

            # Read 16 KiB from 0x8780_0000 using any available memory read implementation
            data = ctx.read_memory(0x8780_0000, 16384)

            # Read 16 KiB 0x8780_0000 using the GoMemoryReader implementation
            # Observe that this is case-insensitive and the suffix can be omitted.
            data = ctx.read_memory(0x8780_0000, 16384, impl='GoMemoryReader')
            data = ctx.read_memory(0x8780_0000, 16384, impl='go')

            # Use one of GoMemoryReader, MdMemoryReader, or I2CMemoryReader.
            data = ctx.read_memory(0x8780_0000, 16384, impl=['go', 'md', 'i2c'])


        If *impl* is not specified, or if a specified implementation is not available,
        one will be selected using :py:meth:`default_memory_reader` and the requested read size.

        """
        impl = self._read_memory_impl(size, kwargs)
        return impl.read(address, size, **kwargs)

    def read_memory_to_file(self, address: int, size: int, filename: str, **kwargs):
        """
        Read *size* bytes at the specified memory *address* and write the data
        to a file named *filename*.

        Refer to :py:meth:`read_memory()` regarding the use of the optional *impl*
        keyword argument.
        """
        impl = self._read_memory_impl(size, kwargs)
        return impl.read_to_file(address, size, filename, **kwargs)

    @property
    def memory_writers(self):
        """
        This property provides an iterable collection of all available
        :py:class:`~depthcharge.memory.MemoryWriter` implementations.
        """
        return self._memwr

    def default_memory_writer(self, **kwargs):
        """
        Return the :py:class:`~depthcharge.memory.MemoryWriter` that will be used
        if no implementation is specified via the *impl=* keyword argument when
        `write_memory` is invoked.

        This most suitable default may change with respect to the amount of data being written.  If
        the amount of data to write is known, pass this integer value via a *data_len* keyword
        argument.

        Raises :py:exc:`~depthcharge.OperationNotSupported` if no memory writers are available.
        """
        return self._memwr.default(**kwargs)

    def _write_memory_impl(self, data_len, args_dict):
        """
        Determine the :py:class:`depthcharge.memory.MemoryWriter` implementation to use.
        Checks for and removes *impl* keyword argument from *args_dicts*
        (which is presumably the caller's un-expanded *kwargs* dict).
        """
        try:
            impl = args_dict.pop('impl')
            return self._memwr.find(impl)
        except (KeyError, TypeError):
            return self.default_memory_writer(data_len=data_len)

    def write_memory(self, address: int, data: bytes, **kwargs):
        """
        Write the provided *data* to the specified memory *address*.

        Similar to :py:meth:`read_memory()`, this method supports an optional *impl* keyword
        argument.

        If a memory write operation requires the use of a :py:class:`depthcharge.Stratagem`,
        provide this via a *stratagem=* keyword argument and set *data=None*.
        """
        stratagem = kwargs.get('stratagem', None)
        if stratagem and isinstance(stratagem, Stratagem):
            impl = self._memwr.find(stratagem.operation_name)
        else:
            impl = self._write_memory_impl(len(data), kwargs)

        impl.write(address, data, **kwargs)

    def write_memory_from_file(self, address: int, filename: str, **kwargs):
        """
        Write the contents of the binary file accessed via *filename* to the
        specified memory *address*.

        If the file contains a Stratagem (as opposed to raw data to write), set
        the keyword argument *stratagem=True* to indicate this.

        Similar to :py:meth:`read_memory()`, this method supports an optional *impl* keyword
        argument.
        """
        if kwargs.get('stratagem', False):
            stratagem = Stratagem.from_json(filename)
            impl = self._memwr.find(stratagem.operation_name)
            impl.write(address, None, stratagem=stratagem)
        else:
            with open(filename, 'rb') as infile:
                file_size = os.fstat(infile.fileno().st_size)
                impl = self._write_memory_impl(file_size, kwargs)
                impl.write_from_file(address, infile)

    def patch_memory(self, patch_list, dry_run=False, **kwargs):
        """
        Patch a series of memory locations, as described in the provided *patch_list*.

        This argument may be one of:

            * A :py:class:`~depthcharge.memory.MemoryPatchList`
            * A ``list`` containing :py:class:`~depthcharge.memory.MemoryPatch` objects, tuples, or
              dictionaries. Refer to :py:class:`~depthcharge.memory.MemoryPatch` for the required
              layout of the tuples and dictionaries.

        This method will first iterate over the list of memory locations to patch and verify
        that each contains the expected value (if the corresponding
        :py:class:`~depthcharge.memory.MemoryPatch` contains an expected value).  If a target memory
        location does not match an expected value, a :py::`ValueError` is raised. This behavior
        is intended to help avoid applying patches in cases where a target is executing a new or
        unexpected firmware revision. If this is not desired, checks can be disabled by providing a
        *skip_checks=True* keyword argument.

        Next, each patch's data will be written to their corresponding memory locations. If
        *dry_run=True*, this write step is skipped.

        Similar to the :py:meth:`read_memory` and :py:meth:`write_memory` methods,
        an *impl* keyword argument can be used to specify, by name, which specific memory
        access implementations should be used (if available). Otherwise, Depthcharge
        will attempt to use the most reasonable defaults.

        Below is an example invocation that specifies that
        :py:class:`~depthcharge.memory.CRC32MemoryReader` and
        :py:class:`~depthcharge.memory.NmMemoryWriter`.

        .. code:: python

            ctx.patch_memory(patch_list, impl=['CRC32MemoryReader', 'NmMemoryWriter'])

        Technically, the *"MemoryReader"* and "*MemoryWriter*" suffixes can be
        omitted in the above example. However, it is recommended that they be used when specifying
        both readers and writers, as suffixless names may be ambiguous (as in the case of
        :py:class:`~depthcharge.memory.NmMemoryReader` and
        :py:class:`~depthcharge.memory.NmMemoryWriter`).

        """

        if isinstance(patch_list, MemoryPatchList):
            pass
        elif isinstance(patch_list, list):
            patch_list = MemoryPatchList(patch_list)
        elif isinstance(patch_list, (MemoryPatch, dict, tuple)):
            patch_list = MemoryPatchList([patch_list])
        else:
            actual = type(patch_list).__name__
            raise TypeError('Expected MemoryPatchList, got: ' + actual)

        avg_patch_size = 0
        for patch in patch_list:
            avg_patch_size += len(patch.value)
        avg_patch_size //= len(patch_list)

        # Both of theses helpers pop('impl'), so this is a bit of a kludge
        impl = kwargs.get('impl', None)
        read_impl  = self._read_memory_impl(avg_patch_size, kwargs)
        write_impl = self._write_memory_impl(avg_patch_size, {**kwargs, **{'impl': impl}})

        skip_checks = kwargs.get('skip_checks', False)

        do_writes = True
        if dry_run or not skip_checks:
            do_writes = self._check_patch_expectations(read_impl, patch_list)

        if dry_run or not do_writes:
            return

        progress = self.create_progress_indicator(self, len(patch_list), 'Applying patches')
        try:
            for i, patch in enumerate(patch_list):
                # Setup operation only on the first write
                no_setup = i != 0
                kwargs['suppress_setup'] = no_setup

                # Teardown operation only on the final write
                no_teardown = i < (len(patch_list) - 1)
                kwargs['suppress_teardown'] = no_teardown

                write_impl.write(patch.address, patch.value, **kwargs)
                progress.update()
        finally:
            self.close_progress_indicator(progress)

    def _exec_impl(self, args_dict):
        try:
            impl = args_dict.pop('impl')
            return self._exec.find(impl)
        except (KeyError, TypeError):
            return self._exec.default()

    def register_payload(self, name: str, payload: bytes, required_by=None):
        """
        Register an executable payload that can later be deployed and executed.
        The payload's *name* must be unique.

        If you wish to manually deploy and execute the payload, refer to
        :py:meth:`deploy_payload()` and :py:meth:`execute_payload()`.

        Otherwise, the payload can be automatically deployed and
        executed as-needed by specifying one or more :py:class:`~depthcharge.operation.Operation`
        classes that require this payload to function. These can be specified
        by class name (str) or an instance of the class. Either a single
        item or a list can be provided.
        """
        self._payloads.insert(name, payload, required_by)

    def deploy_payload(self, name: str, **kwargs):
        """
        Write the builtin payload identified by *name* to its corresponding address
        (determined during execution of the :py:class:`~depthcharge.Depthcharge` constructor).

        If the payload is already deployed, this method performs no action.

        The keyword argument *force=True* can be used to force (re)deployment.
        """
        if self._allow_deploy_exec is False:
            # Shouldn't happen
            raise OperationFailed('Not performing payload deployment. Requires opt-in.')

        payload     = self._payloads[name]
        addr        = payload['address']
        deployed    = payload['deployed']
        skip_deploy = payload['skip_deploy'] and not deployed
        force       = kwargs.get('force', False)

        if skip_deploy and not force:
            payload['deployed'] = True
            log.note('Payload deployment skipped: assuming \"{:s}\" @ 0x{:08x}'.format(name, addr))
            return

        if not deployed or force:
            if 'dcache' in self._cmds:
                self.send_command('dcache flush')
            else:
                log.warning('Command to flush data cache (dcache) not available. Device may crash.')

            if 'icache' in self._cmds:
                self.send_command('icache flush')
            else:
                log.warning('Command to flush instruction cache (icache) not available. Device may crash.')

            log.note('Deploying payload \"{:s}\" @ 0x{:08x}'.format(name, addr))
            self.write_memory(addr, payload['data'])
            self._payloads.mark_deployed(name)

    def execute_payload(self, name: str, *args, **kwargs):
        """
        Execute the builtin payload identified by *name*.

        This method will invoke :py:meth:`deploy_payload()` as-needed to
        ensure the payload is deployed before attempting to execute it.

        Positional and keyword arguments are passed to the underlying
        :py:class:`~depthcharge.executor.Executor` implementation, which will
        determine which of these (if any) are passed to the payload (and how).
        This of course, also depends upon the payload code itself.

        Returns a tuple: *(return code: int, response data: bytes)*

        The keyword argument *read_response=False* can be passed to suppress
        reading of response data, should the caller want to do so manually
        through raw console accesses. In this case, this method returns ``None``.
        """
        if self._allow_deploy_exec is False:
            msg = ('Not attempting payload execution. '
                   'Requires opt-in of payload deployment and execution.')
            raise OperationFailed(msg)

        payload = self._payloads[name]

        # Deploy payload as-needed. (No-op if already deployed.)
        self.deploy_payload(name, **kwargs)

        # Used by deploy. Don't pass to Executor.
        _ = kwargs.pop('force', False)

        return self.execute_at(payload['address'], *args, **kwargs)

    def execute_at(self, address: int, *args, **kwargs):
        """
        Instruct the target to execute instructions at the specified `address`.

        Any additional positional and keyword arguments are passed to the
        underlying :py:class:`~depthcharge.executor.Executor` implementation.

        **Important:** This method does not perform any pre-requisite validation before
        attempting to begin execution. Favor the use of :py:meth:`execute_payload()`.
        """
        impl = self._exec_impl(kwargs)
        return impl.execute_at(address, *args, **kwargs)

    def _check_patch_expectations(self, read_impl, patch_list, **kwargs):
        matches_expected = 0
        already_applied  = 0

        desc = 'Verifying expected pre-patch state'
        show = kwargs.get('show_progress', True)

        progress = self.create_progress_indicator(self, len(patch_list), desc, show=show)

        # Pre-determine our first and last reads so that we can determine when we
        # need to set the suppress_setup and supress_teardown flags.
        first_read_idx = None
        last_read_idx = None
        for i, patch in enumerate(patch_list):
            if patch.expected is not None:
                if first_read_idx is None:
                    first_read_idx = i
                last_read_idx = i

        try:
            for i, patch in enumerate(patch_list):
                if patch.expected is None:
                    progress.update()
                    continue

                # Perform operation setup only on the first read
                kwargs['suppress_setup'] = (i != first_read_idx)

                # Perform operation teardown only on the final read
                kwargs['suppress_teardown'] = (i != last_read_idx)

                read_data = read_impl.read(patch.address, len(patch.expected), **kwargs)
                if read_data == patch.expected:
                    log.debug(patch.description + ' matches expected pre-patch value.')
                    matches_expected += 1
                elif read_data == patch.value:
                    log.debug(patch.description + ' is already patched.')
                    already_applied  += 1
                else:
                    log.debug('Expected:  ' + patch.expected.hex())
                    log.debug('Read data: ' + read_data.hex())

                    err = patch.description + ' does not match expected value.'
                    raise ValueError(err)

                progress.update()

        finally:
            self.close_progress_indicator(progress)

        if matches_expected == len(patch_list):
            log.note('Target memory matches expected pre-patch values.')
            return True

        if already_applied == len(patch_list):
            msg = 'Target memory appears to be already patched. No writes needed.'
            log.note(msg)
            return False

        msg = 'Target memory appears to have been only partially patched.'
        log.note(msg)
        return True

    def uboot_global_data(self, cached=True, **kwargs) -> dict:
        """
        Inspect U-Boot's global data structure and return a dictionary describing elements relevant
        to Depthcharge's usage of it.

        The :py:class:`~depthcharge.Depthcharge` constructor includes this inspection if sufficient
        information and operations are available. This method returns the cached results are
        returned if *cached=True*. Otherwise, executing this method with *cached=False* will force
        Depthcharge to explore the target to obtain this information.

        Below is a summary of how this method operates and how optional keyword arguments
        can be used to modify its behavior.

        First, information is gathered from the console ``bdinfo`` command if it is available.

        Next, an attempt is made to retrieve the global data structure (*gd_t*) address
        and read memory at this location. These memory contents are used to infer the locations of
        functions exported in its jump table.

        An :py:class:`~depthcharge.OperationNotSupported` exception is raised if requisite
        underlying operations are not available to retrieve any (partial) information.

        If platform- or version-specific differences resulting in failures, the following two
        keyword arguments can be used to skip portions of this implementation, as a workaround:

            * *skip_bdinfo=True* - Skip ``bdinfo`` invocation and parsing of output
            * *skip_gd_jt=True*  - Skip access of global data pointer and jump table inspection

        Upon success, returned information will be also recorded within the
        :py:class:`~depthcharge.Depthcharge` object and made available to successive calls.
        This information is included in the device configuration file exported via
        :py:meth:`save()`.

        Refer to U-Boot's *include/asm-generic/global_data.h* header and its *README.standalone*
        document for more information about the data structures and tables discussed above.
        """
        if '_done' in self._gd and cached:
            ret = deepcopy(self._gd)
            ret.pop('_done')
            return ret

        if 'bdinfo' in self._cmds and not kwargs.get('skip_bdinfo', False):
            resp = self.console.send_command('bdinfo')
            bdinfo = uboot.board.bdinfo_dict(resp)
            if bdinfo:  # Don't insert any empty dict if things go awry
                self._gd['bd'] = bdinfo
        else:
            log.warning('Device does not support bdinfo command.')

        if not kwargs.get('skip_gd_jt', False):
            try:
                self._uboot_gd_addr()  # Sets _gd['address']
                self._gd['jt'] = self._uboot_jump_table()
            except OperationNotSupported as error:
                log.warning(str(error))

        if self._gd:
            ret = deepcopy(self._gd)
            self._gd['_done'] = True
            return ret

        err = 'Cannot inspect global data structure with available functionality.'
        raise OperationNotSupported(None, err)

    def _uboot_gd_addr(self, register_reader=None):
        """
        Internal helper for retrieving the register value used to store a pointer
        to the global data structure.

        Sets _gd['address'] and returns this value.

        Raises OperationNotSupported if the target architecture doesn't use
        a register for this purpose. Depthcharge does not currently provide
        other ways in which gd is accessed (e.g. stack on X86).

        If you're on an x86 platform, have access to the bdinfo console command,
        and have a memory read operation available, consider inspecting the stack,
        which starts at the location indicated by the `bdinfo` `sp_start` value.
        """
        gd_reg = self.arch.gd_register
        if gd_reg is None:
            msg = 'Accessing gd pointer on ' + self.arch.name + ' is not currently supported.'
            raise OperationNotSupported(None, msg)

        try:
            return self._gd['address']
        except KeyError:
            if register_reader is None:
                register_reader = self._regrd.default()

            self._gd['address'] = register_reader.read(gd_reg)
            msg = 'Located U-boot global data structure (*gd) @ 0x{:08x}'
            log.note(msg.format(self._gd['address']))
            return self._gd['address']

    def _uboot_jump_table(self, memory_reader=None):
        """
        Helper function for locating U-Boot jump table.
        Assumes knowledge of gd pointer.

        Sets _gd['jt'] and returns this dict (not a copy!)

        """
        # Non-public argument used to guide the MemoryReader choice in cases
        # where lower-level code already knows what's best to use here.
        if memory_reader is None:
            memory_reader = self._memrd.default()

        self._gd['jt'] = uboot.jump_table.find(self._gd['address'], memory_reader, self.arch)
        return self._gd['jt']
