# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
"""
Provides the StratagemMemoryWriter class
"""

from .writer import MemoryWriter
from ..operation import OperationNotSupported
from ..stratagem import Stratagem, StratagemRequired


class StratagemMemoryWriter(MemoryWriter):
    """
    StratagemMemoryWriter is a base class for
    :py:class:`~depthcharge.memory.MemoryWriter` implementations that cannot
    write memory directly, but rather through a side-effect or roundabout
    approach described by a :py:class:`depthcharge.Stratagem`.
    """

    # Size of data written by each stratagem entry, in bytes
    _output_size = 4

    def _describe_op(self, addr, data):
        """
        Return a string (suitable for logging) that describes the write
        operation that would be performed with the provided arguments.
        """
        stratagem = data
        desc = '({:s}) Writing {:d} bytes @ 0x{:08x}'
        total_len = len(stratagem) * self._output_size
        return desc.format(self.name, total_len, addr)

    def _write(self, _addr, _data, **kwargs):
        raise OperationNotSupported(self, '_write() not used by StratagemMemoryWriter')

    def _write_stratagem(self, wr_addr: int, stratagem, progress):
        raise NotImplementedError

    def write(self, addr: int, data: bytes = None, **kwargs):
        """
        Execute the :py:class:`~depthcharge.Stratagem` specified in a *stratagem* keyword
        argument in order to write a desired payload to a target memory location (*addr*).

        Because a :py:class:`~.StratagemMemoryWriter` cannot write data directly, the *data* argument
        is unused and should be left as ``None``.

        For this type of :py:class:`~depthcharge.memory.MemoryWriter`, the
        :py:meth:`write_from_file()` method is often more intuitive to use.

        **Example:**

        .. code-block:: python

            my_stratagem_writer.write(0x8400_0000, data=None, strategm=my_stratagem)

        """
        try:
            stratagem = kwargs['stratagem']
        except KeyError:
            raise StratagemRequired(self.name)

        if data is not None and len(data) != 0:
            msg = self.name + ' uses Stratagem. Ignoring {:d} bytes of provided data'
            self.log.warning(msg.format(len(data)))

        stratagem_op_name = stratagem.operation_name
        if stratagem_op_name != self.name:
            error = 'Stratagem is for {:s}, but {:s} is being used'
            raise ValueError(error.format(stratagem_op_name, self.name))

        desc = self._describe_op(addr, stratagem)
        show = kwargs.get('show_progress', True)
        progress = self._ctx.create_progress_indicator(self, stratagem.total_operations, desc, show=show)

        try:
            self._write_stratagem(addr, stratagem, progress)
        finally:
            self._ctx.close_progress_indicator(progress)

    def write_from_file(self, addr: int, filename: str, **kwargs):
        """
        Load a :py:class:`~depthcharge.Stratagem` file and use it to write to the
        target memory locations specified by *addr*.

        **Example:**

        .. code-block:: python

            my_stratagem_writer.write_from_file(0x8400_0000, 'my_stratagem.json')

        """
        stratagem = Stratagem.from_json_file(filename)
        self.write(addr, None, stratagem=stratagem)
