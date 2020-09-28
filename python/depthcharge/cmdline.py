# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
The *depthcharge.cmdline* module provides functionality to help create consistent
command line interfaces atop of the Depthcharge API. This includes a set of
common argument flags and handlers.

This module includes Depthcharge's own :py:class:`ArgumentParser` class that wraps the standard
Python :py:class:`argparse.Argumentparser` as well as custom :py:class:`argparse.Action` classes.
"""

import argparse

from depthcharge import log
from depthcharge.context    import Depthcharge
from depthcharge.companion  import Companion
from depthcharge.console    import Console
from depthcharge.monitor    import Monitor
from depthcharge.string     import keyval_list_to_dict, length_to_int, str_to_property_keyval


def create_depthcharge_ctx(args, **kwargs):
    """
    Create and return an initialized :py:class:`~depthcharge.Depthcharge` handle based upon
    command-line arguments.  Examples of this function's usage can be found in the Depthcharge
    scripts.

    The *args* parameter should contain the results of :py:class:`ArgumentParser.parse_args()`.

    The following must be included in the **args** Namespace, even if set to their
    unspecified (e.g. default, ``None``) values.

    * *monitor* - From :py:meth:`ArgumentParser.add_monitor_argument()`
    * *iface* - From :py:meth:`ArgumentParser.add_interface_argument()`
    * *prompt* - From :py:meth:`ArgumentParser.add_prompt_argument()`
    * *extra* - From :py:meth:`ArgumentParser.add_extra_argument()`

    The following items are optional:

    * *config* - From :py:meth:`ArgumentParser.add_config_argument()`
    * *companion* - From :py:meth:`ArgumentParser.add_companion_argument()`
    * *allow_deploy* - From :py:meth:`ArgumentParser.add_allow_deploy_argument()`
    * *skip_deploy* - From :py:meth:`ArgumentParser.add_skip_deploy_argument()`
    * *no_reboot* - From :py:meth:`ArgumentParser.add_no_reboot_argument()`

    """
    monitor = Monitor.create(args.monitor)

    # Added as a quick way to sneak in a timeout=... value to increase down
    # intra-command time for demos.
    #
    # TODO: Mull this over a bit more, clean it up if needed, and document this.
    console_kwargs = kwargs.get('console_kwargs', {})

    console = Console(args.iface,
                      prompt=args.prompt,
                      monitor=monitor,
                      **console_kwargs)

    if hasattr(args, 'companion') and args.companion:
        device, companion_kwargs = args.companion
        companion = Companion(device, **companion_kwargs)
    else:
        companion = None

    # Join any "extra" arguments destined for depthcharge.Operation **kwargs
    # to out existing kwargs.
    if args.extra:
        kwargs = {**kwargs, **args.extra}

    # Insert the specified boolean flag items into kwargs if args contains corresponding keys
    bool_flags = ('allow_deploy', 'skip_deploy', 'no_reboot')

    for key in bool_flags:
        if hasattr(args, key) and getattr(args, key):
            kwargs[key] = getattr(args, key)

    if hasattr(args, 'config') and args.config:
        try:
            log.info('Loading existing config: ' + args.config)
            return Depthcharge.load(args.config,
                                    console,
                                    companion=companion,
                                    **kwargs)
        except FileNotFoundError:
            # We'll create it when we call save()
            pass

    return Depthcharge(console,
                       companion=companion,
                       **kwargs)


class AddressAction(argparse.Action):
    """
    ArgumentParser Action for validating memory and device addresses.

    The following suffixes are supported:

        * kB = 1000
        * K or kiB = 1024
        * MB = 1000 * 1000
        * M or MiB = 1024 * 1024
        * GB = 1000 * 1000 * 1000
        * G or GiB = 1024 * 1024 * 1024

    """
    def __call__(self, parser, namespace, address, option_string=None):
        value = length_to_int(address, desc='address')
        setattr(namespace, self.dest, value)


class CompanionAction(argparse.Action):
    """
    ArgumentParser Action for handling Companion arguments.

    This may be used to convert ``args.companion`` converted to a tuple in the form:

    ``(device, params={key: value})``

    """
    def __call__(self, parser, namespace, companion_str, option_string=None):
        setattr(namespace, self.dest, str_to_property_keyval(companion_str))


class ListAction(argparse.Action):
    """
    ArgumentParser action for creating lists from comma-separated strings.

    For example, ``--op foo,bar,baz``  ``--op fizz,buzz`` would result in the list
    `[foo, bar, baz, fizz, buzz]`.

    """
    def __call__(self, parser, namespace, arg, option_string=None):
        fields = arg.split(',')
        for i, entry in enumerate(fields):
            fields[i] = entry.strip()

        if fields:
            curr_list = getattr(namespace, self.dest) or []
            setattr(namespace, self.dest, curr_list + fields)


class KeyValListAction(argparse.Action):
    """
    ArgumentParser Action for converting arguments of the form:

        ``-X foo=bar,baz -X hello=world -X fortytwo``

    to a dictionary containing:

        ``{'foo': 'bar', 'baz': True, 'hello': 'world', 'fortytwo': True }``

    """
    def __call__(self, parser, namespace, info_str, option_string=None):
        info_list = info_str.split(',')
        info_dict = keyval_list_to_dict(info_list)

        # Namespace overrides something such that getatter with a default
        # parameter still returns None and doesn't raise AttributeError?
        keyval_dict = getattr(namespace, self.dest) or {}

        setattr(namespace, self.dest, {**keyval_dict, **info_dict})


class LengthAction(argparse.Action):
    """
    ArgumentParser action for parsing length values with support for the
    same suffixes supported by :py:class:`AddressAction`.
    """
    def __call__(self, parser, namespace, length, option_string=None):
        value = length_to_int(length)
        setattr(namespace, self.dest, value)


class ArgumentParser(argparse.ArgumentParser):
    """
    This class is an extension of Python's own :py:class:`argparse.ArgumentParser`
    that adds Depthcharge-specific argument handler initializations.

    The *init_args* parameter provides a simple way to configure the parser
    in situations where ``add_<x>_argument()`` methods would only be called
    with their default arguments. Instead, *init_args* can be provided as a list
    of strings, with each string corresponding to the ``<x>`` in ``add_<x>_argument``.

    When using this *init_args* approach, keyword arguments prefixed
    with ``<x>_`` will be to the corresponding ``add_<x>_argument``, sans prefix.

    """
    # Supress this for consistency with the ArgumentParser keyword names:
    #  pylint: disable=redefined-builtin

    #: :obj:`list` :
    #: Default list used by :py:meth:`ArgumentParser.__init__()` unless
    #: otherwise overridden with a caller-provided list.
    DEFAULT_ARGS = [
        'config',
        'interface',
        'companion',
        'monitor',
        'extra',
        'prompt',
        'allow_deploy',
        'skip_deploy',
        'no_reboot',
    ]

    def _perform_arg_handler_init(self, init_args: list, kwargs_dict: dict):
        """
        Helper for __init__() to aggregate the requested add_<x>_argument()
        operations, as inidicated by `init_args`.

        Keyword arguments are handled as a dict so that items can be pop()'d
        before we allow them to be expanded and passed to the "real"
        ArgumentParser.
        """

        # Pull out kwargs that are intended for our add_<x>_argument() calls
        # and assign them to their corresponding init calls.
        init_operations = []
        for name in init_args:
            to_pop = []
            fn_kwargs = {}
            for key in kwargs_dict:
                if key.startswith(name + '_'):
                    to_pop.append(key)
                    fn_keyword = key.replace(name + '_', '')
                    fn_kwargs[fn_keyword] = kwargs_dict[key]

            # Remove items from kwargs so that the super class doesn't raise
            # a TypeError over unexpected keyword arguments
            for key in to_pop:
                kwargs_dict.pop(key)

            fn_name = 'add_' + name + '_argument'
            init_fn = getattr(self, fn_name)

            init_operations.append((init_fn, fn_kwargs))

        return init_operations

    def __init__(self, init_args='default', **kwargs):
        """
        Construct a ArgumentParser and initialize Depthcharge-specific
        argument handlers according to the contents of the `init_args` keyword.

        The `init_args` parameter can be used to specify which of this class's
        `add_<x>_argument()` methods should be invoked. This can be specified
        as a list of names, each of which corresponds to the `<x>` in the
        Depthcharge-specific `add_<x>_argument()` methods.

        For example, if one wishes to configure only the *iface* and *monitor*
        arguments (`-i` and `-m`), `init_args` would need to be set to
        `['iface', 'monitor']`.

        The special exception is the string `'default'`, which may be passed
        instead of a customized list in order to use all of the items in the
        `DEFAULT_ARGS` list.

        Either `None` or an empty list may be passed if you do not wish to
        include any of the Depthcharge-specific command-line arguments.

        In order to pass keyword arguments to individual `add_<x>_argument()`
        functions, simply prefix each  `kwarg` key with `<x>`. For example,
        to require a user to specify *iface* (`-i`)
        upon the previous example, if you want to require that the user provide
        the *baudrate* option, specify `baudrate_required=True`. This will
        result in `add_baudrate_argument()` being called with `required=True`.

        Any other `kwargs` items are passed directly to the underlying
        argparse.ArgumentParser. Items specific to Depthcharge will be removed
        from `kwargs` before being passed to Python's underlying
        ArgumentParser.

        If any values in `init_args` are invalid, a :py:class:`AttributeError` is rai
        :Raises: :py:class:`AttributeError` if a name in `init_args` is invalid.
        """
        if init_args == 'default':
            init_args = self.DEFAULT_ARGS
        elif init_args in self.DEFAULT_ARGS:
            init_args = [init_args]
        elif init_args is None:
            init_args = []
        elif not isinstance(init_args, list):
            raise TypeError('init_args expected to be a string or list')

        # Passing kwargs as dict in order to allow items to be pop()'d
        # before they're passed to the superclass
        init_operations = self._perform_arg_handler_init(init_args, kwargs)

        super().__init__(**kwargs)
        for op in init_operations:
            op_fn = op[0]
            op_kwargs = op[1]
            op_fn(**op_kwargs)

        # I don't subscribe to the "option flags are for optional arguments,
        # use positionals if they're required".  The flags help me remember
        # which thing I'm specifying, without needing to worry about order.
        #
        # I want to use required=True, even though the Python docs discourage it,
        # and don't want these to be reported as "optional arguments".
        try:
            self._optionals.title = 'options'
        except AttributeError:
            pass

    def add_address_argument(self, default=0, help=None, required=True):
        """
        Add a memory address argument to the ArgumentParser.
        """
        if help is None:
            help = 'Base address of image.'

        if default is not None:
            help += ' Default: 0x{:08x}'.format(default)

        self.add_argument('-a', '--address',
                          metavar='<value>',
                          default=default,
                          action=AddressAction,
                          required=required,
                          help=help)

    def add_arch_argument(self, default='ARM', required=False):
        """
        Add a CPU architecture argument to the ArgumentParser.
        """
        self.add_argument('-A', '--arch',
                          metavar='<architecture>',
                          default=default,
                          required=required,
                          help='CPU architecture. Default: ' + default)

    def add_companion_argument(self, required=False):
        """
        Add an argument to the ArgumentParser that can be used to
        specify a Depthcharge Companion device and its corresponding
        settings.
        """
        help = ('Depthcharge companion device to use and its associated settings.'
                ' See the depthcharge.Companion documentation for supported '
                ' settings.')

        self.add_argument('-C', '--companion',
                          metavar='<device>[:setting=value,...]',
                          default=None,
                          action=CompanionAction,
                          required=required,
                          help=help)

    def add_config_argument(self, required=False, help=None):
        """
        Add the device configuration argument to the ArgumentParser.
        """

        if help is None:
            help = ('Device configuration file to load and update. '
                    'It will be created if it does not exist.')

        self.add_argument('-c', '--config',
                          metavar='<cfg>',
                          required=required,
                          help=help)

    def add_data_argument(self, help=None, required=False):
        """
        Add an option to provide data as a hex string to the ArgumentParser.

        The caller is required to provide help text in order to describe the
        nature of the data users must provide.
        """
        self.add_argument('-d', '--data', metavar='<hex str>', help=help, required=required)

    def add_extra_argument(self, help=None, required=False):
        """
        Add an option to allow scripts to provide "extra" arguments via the
        command line, which translate directly to ``**kwargs`` passed to
        Depthcharge API calls.
        """
        if help is None:
            help = ('Specify extra operation-specific parameters as a key-value '
                    'pair. A value of True is implicit if a value is not '
                    'explicitly provided. Multiple instances of this argument '
                    'are permitted. See the documentation for subclasses of '
                    'depthcharge.Operation for supported keyword arguments.')

        self.add_argument('-X', '--extra',
                          metavar='<key>[=<value>]',
                          action=KeyValListAction,
                          required=required,
                          default={},
                          help=help)

    def add_file_argument(self, help=None, required=False):
        """
        Add a file argument to the ArgumentParser.

        The caller **must** provide the help text in order to specify the
        purpose of this file, and whether it is an input or output file.
        """
        if help is None:
            raise ValueError('Help text must be provided for -f,--file ')

        self.add_argument('-f', '--file', metavar='<path>', help=help, required=required)

    def add_interface_argument(self, required=False):
        """
        Add a serial console interface option the the ArgumentParser.
        """
        self.add_argument('-i', '--iface',
                          metavar='<console dev>[:baudrate]',
                          default='/dev/ttyUSB0:115200',
                          required=required,
                          help='Serial port interface connected to U-Boot console.')

    def add_op_argument(self, required=False):
        """
        Add an argument to allow desired :py:class:`depthcharge.Operation` implementations to be
        requested, by name.
        """
        help = ('Request that one of the specified depthcharge.Operation '
                'implementations be used. Depthcharge will attempt to choose '
                'the best available option if this is not provided.')

        self.add_argument('--op',
                          metavar='<name>[,name,...]',
                          default=None,
                          action=ListAction,
                          required=required,
                          help=help)

    def add_length_argument(self, help=None, required=False):
        """
        Add a length argument to the ArgumentParser.

        Default help text describes a read operation, in bytes.
        """
        if help is None:
            help = 'Number of bytes to read'

        self.add_argument('-l', '--length',
                          default=None,
                          metavar='<n>',
                          action=LengthAction,
                          help=help,
                          required=required)

    def add_monitor_argument(self, required=False):
        """
        Add a serial port monitor argument to the ArgumentParser.
        """
        self.add_argument('-m',  '--monitor',
                          metavar='<type>[:options,...]',
                          default=None,
                          required=required,
                          help='Attach a console monitor. Valid types: file, pipe, colorpipe')

    def add_no_reboot_argument(self, help=None):
        if help is None:
            help = 'Exclude operations that require crashing or rebooting the target.'

        self.add_argument('-R', '--no-reboot',
                          default=False,
                          action='store_true',
                          help=help)

    def add_outfile_argument(self, help=None, required=False):
        """
        Add an output file argument to the ArgumentParser.

        If a script *only* outputs a file, use :py:meth:`add_file_argument()`.

        Otherwise, if a script both reads and writes different files,
        use :py:meth:`add_file_argument()` for the input file and this
        method for the output file.

        The caller is required to provide the *help* argument.
        """
        if help is None:
            raise ValueError('Help text must be provided for -o,--outfile ')

        self.add_argument('-o', '--outfile', metavar='<path>', help=help, required=required)

    def add_prompt_argument(self, required=False):
        """
        Add an option to the ArgumentParser to allow for the expected U-Boot
        prompt to be supplied via the command line.
        """
        help = 'Override expected U-Boot prompt string.'
        self.add_argument('-P', '--prompt',
                          metavar='<prompt str>',
                          default=None,
                          required=required,
                          help=help)

    def add_allow_deploy_argument(self, required=False):
        """
        Add an opt-in option to the ArgumentParser that specifies that the user
        wants to allow payload deployment and execution.
        """
        help_text = ('Allow payloads to be deployed and executed. '
                     'Functionality may be limited if this is not specified.')

        self.add_argument('-A', '--allow-deploy',
                          action='store_true',
                          default=False,
                          required=required,
                          help=help_text)

    def add_skip_deploy_argument(self, required=False):
        """
        Add an option to the ArgumentParser to allow payload deployment to be
        skipped in situations where a prior script or command has already
        done this. (They still want to execute payloads.)
        """
        help_text = ('Skip payload deployment but allow execution. '
                     "assume payloads are already deployed and execute as-needed. "
                     'This has no effect when -A, --allow-deploy is used.')

        self.add_argument('-S', '--skip-deploy',
                          action='store_true',
                          default=False,
                          required=required,
                          help=help_text)

    def add_stratagem_argument(self, help=None, metavar='<file>', required=False):
        """
        Add an option to the ArgumentParser to allow a user to supply a file
        containing a :py:class:`depthcharge.Stratagem` JSON file.

        The caller must provide help text specifying the purpose of the
        stratagem file (e.g. whether its being produced or is an input).
        """
        if help is None:
            raise ValueError('Help text must be provided for -s,--stratagem')

        self.add_argument('-s', '--stratagem', metavar=metavar, help=help, required=required)
