# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Depthcharge Monitor functionality can be used to observe data written to and
read from the console interface. This can be helpful when debugging or simply
as a means to better understand how Depthcharge is performing requested
operations.

The monitor is shown in the following animation, in the bottom terminal.
Observed that the commands used by the ``depthcharge-inspect`` and
``depthcharge-readmem`` (using :py:class:`~depthcharge.memory.ItestMemoryReader`)
can be observed.

.. image:: ../../images/monitor.gif
    :align: center
"""

import os
import stat
import subprocess

from . import log


class Monitor:
    """
    The :py:class:`.Monitor` class implements a no-op base implementation
    that simply discards all data.
    """
    def __init__(self):
        self._f = None
        self._prev_write = None

    _default_depthcharge_pipe = '/tmp/depthcharge-monitor.pipe'
    _default_depthcharge_file = '/tmp/depthcharge-monitor.txt'

    _impls = {}

    @classmethod
    def register(cls, name: str, impl_class):
        """
        Register a :py:class:`Monitor` implementation to be returned by
        :py:meth:`Monitor.create()`. This the Monitor functionality to be
        extended at run-time.
        """
        if not issubclass(impl_class, Monitor):
            raise ValueError('Implementation must be a subclass of depthcharge.Montior')

        cls._impls[name.lower()] = impl_class

    @classmethod
    def create(cls, spec: str):
        """
        Create and return a monitor from a "specification" string structured as follows:

        ``<type>[:arg1,...]``


        Below are the supported types and arguments.

        +--------------------------------------------------+----------------------------------------------------+
        |   Monitor Type                                   |  Argument(s)                                       |
        +--------------------------------------------------+----------------------------------------------------+
        | :py:class:`'file' <.FileMonitor>`                | Filename to write logged console data to.          |
        +--------------------------------------------------+----------------------------------------------------+
        | :py:class:`'pipe' <.NamedPipeMonitor>`           | Named pipe (FIFO) to write logged console data to. |
        +--------------------------------------------------+----------------------------------------------------+
        | :py:class:`'colorpipe' <.ColorNamedPipeMonitor>` | Named pipe (FIFO) to write logged console data to. |
        +--------------------------------------------------+----------------------------------------------------+
        | :py:class:`'term' <.TerminalMonitor>`            | None.                                              |
        +--------------------------------------------------+----------------------------------------------------+

        """
        if spec is None or len(spec) == 0:
            return Monitor()

        fields = spec.split(':', maxsplit=1)

        name = fields[0].lower()
        try:
            args = fields[1].split(',')
        except IndexError:
            args = []

        try:
            impl = cls._impls[name]
            return impl(*args)
        except KeyError:
            raise ValueError('Invalid Monitor name: ' + name)

    def read(self, data):
        """
        Insert data *read from the target* (i.e. U-Boot output) into the monitor.
        """
        if self._prev_write and data.startswith(self._prev_write):
            data = data[len(self._prev_write):].lstrip()
            self._prev_write = None

        self.write(data)

    def write(self, data):
        """
        Insert data *written to the target* (i.e. Depthcharge output) into the monitor.
        """
        self._prev_write = data.strip()
        if self._f is not None:
            for b in data:
                if b in range(0x20, 0x7f) or b in (0x09, 0xa, 0xd):
                    self._f.write(bytes([b]))
                else:
                    s = '<{:02x}>'.format(b)
                    self._f.write(bytes(s, 'ascii'))
            self._f.flush()

    def close(self):
        """
        Close the monitor and its underlying resources.
        """
        if self._f is not None:
            self._f.close()


class FileMonitor(Monitor):
    """
    A :py:class:`.Monitor` subclass that logs console data to a file.
    """

    def __init__(self, path=Monitor._default_depthcharge_file):
        super().__init__()
        self._f = open(path, 'wb')


class NamedPipeMonitor(Monitor):
    """
    A :py:class:`.Monitor` subclass that logs console data to a named pipe.
    """
    def __init__(self, path=Monitor._default_depthcharge_pipe):
        super().__init__()

        msg = ('Writing console output to {:s}. '
               + os.linesep
               + '    Waiting until this is open...')

        log.info(msg.format(path))
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

        os.mkfifo(path, mode=0o600)
        self._f = open(path, 'wb')

        if not stat.S_ISFIFO(os.fstat(self._f.fileno()).st_mode):
            raise IOError("Path '{:s}' does not refer to a FIFO".format(path))


class ColorNamedPipeMonitor(NamedPipeMonitor):
    """
    A :py:class:`.Monitor` subclass that logs console data to a named pipe and styleizes
    output using VT-100 escape sequences, as described below.

    +-----------------------------+---------------------------------------------------------------+
    | Styling                     | Applied to...                                                 |
    +=============================+===============================================================+
    | None                        | U-Boot output containing printable characters                 |
    +-----------------------------+---------------------------------------------------------------+
    | Hex-encoded, magenta        | U-Boot output containing non-printable characters             |
    +-----------------------------+---------------------------------------------------------------+
    | Green                       | Depthcharge output containing printable characters            |
    +-----------------------------+---------------------------------------------------------------+
    | Hex-encoded, cyan           | Depthcharge output containing non-printable characters        |
    +-----------------------------+---------------------------------------------------------------+

    """
    UBOOT_OUT_NONPRINTABLE = 35  # Magenta
    UBOOT_IN_PRINTABLE     = 32  # Green
    UBOOT_IN_NONPRINTABLE  = 36  # Cyan

    def read(self, data):

        if self._prev_write and data.startswith(self._prev_write):
            data = data[len(self._prev_write):].lstrip()
            self._prev_write = None

        for b in data:
            if b in range(0x20, 0x7f) or b in (0x9, 0xa, 0xd):
                self._f.write(bytes([b]))
            else:
                s = '\033[{:d};1m{:02x}\033[0m'.format(self.UBOOT_OUT_NONPRINTABLE, b)
                self._f.write(bytes(s, 'ascii'))

        self._f.flush()

    def write(self, data):
        self._prev_write = data.strip()
        for b in data:
            if b in range(0x20, 0x7f) or b == 0xa or b == 0xd:
                s = '\033[{:d}m{:c}\033[0m'.format(self.UBOOT_IN_PRINTABLE, b)
            else:
                s = '\033[{:d}m{:02x}\033[0m'.format(self.UBOOT_IN_NONPRINTABLE, b)

            self._f.write(bytes(s, 'ascii'))
        self._f.flush()


class TerminalMonitor(ColorNamedPipeMonitor):
    """
    This :py:class:`.ColorNamedPipeMonitor` opens a terminal and displays the stylized data read
    from the underlying named pipe (using */usr/bin/cat*).

    The following terminals are supported. One will be automatically selected.

        * /usr/bin/terminator
        * /usr/bin/xfce4-terminator
        * /usr/bin/gnome-terminator
        * /usr/bin/xterm

    """

    # I have some lingering heebie jeebies over using shutil.which() and then effectively just
    # implementing an RCE here to support this. This is probably too conservative, but we'll see
    # how feedback comes back after some more dogfooding.
    _TERMINALS = (
        '/usr/bin/terminator',
        '/usr/bin/xfce4-terminal',
        '/usr/bin/gnome-terminal',
        '/usr/bin/xterm',
    )

    def __init__(self):
        selected_term = None

        for term in self._TERMINALS:
            if os.path.isfile(term):
                selected_term = term
                break

        if selected_term is None:
            raise NotImplementedError("TerminalMonitor's allow list doesn't support your terminal")

        args = [
            selected_term, '-T', 'Depthcharge Monitor',
            '-e',
            '/usr/bin/sleep 0.25;'
            "/usr/bin/cat '" + Monitor._default_depthcharge_pipe + "'; "
            'read -P "\nDepthcharge operation complete. Press Enter to exit."'
        ]
        self._pid = subprocess.Popen(args)
        super().__init__(Monitor._default_depthcharge_pipe)


# Register default monitors
Monitor.register('file', FileMonitor)
Monitor.register('pipe', NamedPipeMonitor)
Monitor.register('colorpipe',  ColorNamedPipeMonitor)
Monitor.register('term', TerminalMonitor)
