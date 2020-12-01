# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Provides Report class for aggregating and exporting a collection of
identified security risks.
"""

import csv
import html
import os
import sys

from datetime import datetime
from operator import attrgetter
from textwrap import dedent, indent

from . import SecurityRisk


class Report:
    """
    A set of of :py:class:`SecurityRisk` objects that can be exported to multiple formats.
    This class can be used to aggregate results from custom "checkers" and tools.

    The number of results currently within the :py:class:`Report` can be determined via
    ``len(report_instance)``.
    """
    def __init__(self):
        """
        Create an empty report.
        """
        self._risks = set()

        # For generator/iterator
        self._i = 0
        self._ordered = None

    def __len__(self):
        return len(self._risks)


    def add(self, risk) -> bool:
        """
        Record a new security risk. This argument should be either a :py:class:`SecurityRisk`
        object or a dictionary that can be passed to the :py:class:`SecurityRisk` constructor.

        Each added :py:class:`SecurityRisk` must have a unique *identifier* in order to be
        treated as a unique result. If a :py:class:`SecurityRisk` with a given identifier is already
        in the report, no change will be made. The previously added item will remain in place.

        This methods returns ``True`` if the :py:class:`SecurityRisk` was newly added.
        ``False`` is returned when *risk* is a duplicate of an already-recorded item.
        """
        if isinstance(risk, SecurityRisk):
            pass
        elif isinstance(risk, dict):
            risk = SecurityRisk(**risk)
        else:
            raise TypeError('Risk argument must be SecurityRisk or dict')

        before = len(self._risks)
        self._risks.add(risk)
        after = len(self._risks)

        return after > before

    def security_risks(self, high_impact_first=True):
        """
        This is a generator that provides each of the :py:class:`SecurityRisk`
        objects contained in the :py:class:`Report`.

        The default value of ``high_impact_first=True`` ensures that the :py:class:`SecurityRisk`
        objects are ordered highest-to-lowest impact.

        Bear in mind, however, that "risk" and "impact" are just generalizations -- ultimately
        the target device's threat model and surrounding context actually define these. *(Use your
        brain, don't just rely upon automated tools like this one.)*

        It is also possible to iterate over the report in a highest-impact-first order as follows:

        .. code:

            for risk in report:
                print(risk.to_json(indent=4) + os.linesep)
        """
        risks = sorted(self._risks, key=attrgetter('impact'), reverse=high_impact_first)
        for risk in risks:
            yield risk

    def __next__(self):
        if self._ordered is None:
            self._i = 0

            # TODO: Sort by identifier after impact
            self._ordered = sorted(self._risks, key=attrgetter('impact'), reverse=True)

        if self._i < len(self._ordered):
            ret = self._ordered[self._i]
            self._i += 1
            return ret

        raise StopIteration()

    def __iter__(self):
        self._i = 0
        self._ordered = None
        return self

    def merge(self, *others):
        """
        Merge :py:class:`SecurityRisk` items from one or more :py:class:`Report` instances
        (*others*) into this report.

        Items having the same :py:class:`SecurityRisk.identifer` value will **not** be
        duplicated. Only new items from ``other`` will be added. (i.e. it's a set union)

        The `|=` operator has the same effect.

        .. code-block:: python

            report |= other

        """
        for other in others:
            self._risks.update(other._risks)

    def __ior__(self, other):
        self._risks.update(other._risks)
        return self

    def _column_write_wrapper(self, filename: str, write_header: bool, filetype: str, columns=None, **kwargs):
        """
        Wrapper for column-based formats
        """

        # Order of risks
        high_impact_first = kwargs.pop('high_impact_first', True)

        if filename is not None and filename != '-':
            outfile = open(filename, 'w')
        else:
            outfile = sys.stdout

        try:
            if filetype == 'html':
                writer = _HtmlWriter(outfile, **kwargs)
            elif filetype == 'csv':
                # Allow this to be overridden, otherwise us OS-appropriate line ending
                if 'lineterminator' not in kwargs:
                    kwargs['lineterminator'] = os.linesep

                writer = csv.writer(outfile, **kwargs)
            else:
                raise ValueError('Invalid filetype parameter: ' + filetype)

            self._write_risks(writer, write_header, columns, high_impact_first)

        finally:
            if outfile is not sys.stdout:
                outfile.close()

    def _write_risks(self, writer, write_headings=True, columns=None, high_first=True):
        if columns is None:
            columns = ('Identifier', 'Impact', 'Source', 'Summary')
        elif not isinstance(columns, (list, tuple)):
            raise TypeError('`columns` argument must be a list, tuple, or None')

        try:
            writer.begin(write_headings)
        except AttributeError:
            pass  # Expected for csv.writer

        if write_headings:
            writer.writerow(columns)

        for risk in self.security_risks(high_impact_first=high_first):
            row = []
            for col in columns:
                col = col.lower()
                if col == 'identifier':
                    row.append(risk.identifier)
                elif col == 'impact':
                    s = risk.impact_str
                    if isinstance(writer, _HtmlWriter):
                        s = s.replace('+', ', ')
                    row.append(s)
                elif col == 'summary':
                    row.append(risk.summary)
                elif col == 'source':
                    row.append(risk.source)
                elif col == 'description':
                    row.append(risk.description)
                elif col == 'recommendation':
                    row.append(risk.recommendation)
                else:
                    raise ValueError('Invalid column name: ' + col)

            writer.writerow(row)

        try:
            writer.finalize()
        except AttributeError:
            pass  # Expected for csv.writer

    def save_csv(self, filename: str, write_header=True, columns=None, **kwargs):
        """
        Write checker results to a CSV file with the name specified by *filename*.

        If *filename* is ``None`` or ``'-'``, the CSV is written to *stdout*.

        A header row will be written unless *write_header* is set to ``False``.

        The *columns* argument controls the order and presence of columns in
        the produced CSV. This should be provided as a tuple of strings.
        Below are the supported names. Those followed by an asterisk are
        **note** included by default when ``columns=None``

        * Identifier
        * Impact
        * Source
        * Summary
        * Description (\*)
        * Recommendation (\*)

        Any additional keyword arguments are passed to :py:meth:`csv.writer()`.
        """
        self._column_write_wrapper(filename, write_header, 'csv', columns, **kwargs)

    def save_html(self, filename: str, write_header=True, columns=None, **kwargs):
        """
        Write checker results to a simple HTML file with the name specified by *filename*.

        If *filename* is ``None`` or ``'-'``, the output is written to *stdout*.

        A header row will be written unless *write_header* is set to ``False``.

        The *columns* argument controls the order and presence of columns in
        the produced HTML table. This should be provided as a tuple of strings.
        Below are the supported names. Those followed by an asterisk are
        **note** included by default when ``columns=None``

        * Identifier
        * Impact
        * Source
        * Summary
        * Description (*)
        * Recommendation (*)

        Additional keyword arguments are ignored, but not used at this time.
        This API reserves keyword arguments named with a single underscore prefix
        (e.g. ``_foo='bar'``) for internal use.

        """
        self._column_write_wrapper(filename, write_header, 'html', columns, **kwargs)

    def save_markdown(self, filename, **kwargs):  # pylint: disable=unused-argument
        """
        Writer checker results to a Markdown file with the name specified by *filename*.

        Additional keyword arguments are ignored, but not used at this time.
        This API reserves keyword arguments named with a single underscore prefix
        (e.g. ``_foo='bar'``) for internal use.
        """

        with open(filename, 'w') as outfile:
            def _write_header(s, level=2):
                outfile.write('#' * level + ' ' + s + 2 * os.linesep)

            def _write_body(s):
                outfile.write(s)

                if not s.endswith(2 * os.linesep):
                    outfile.write(2 * os.linesep)

            for risk in self.security_risks():
                _write_header(risk.identifier + ': ' + risk.summary, 1)
                _write_header('Impact')
                _write_body(risk.impact.describe())
                _write_header('Source')
                _write_body(risk.source)
                _write_header('Description')
                _write_body(risk.description)
                _write_header('Recommendation')
                _write_body(risk.recommendation)
                outfile.write(os.linesep)


class _HtmlWriter:  # pylint: disable=missing-function-docstring
    """
    Internal class to write results to a simple HTML table.
    """

    def __init__(self, outfile, **kwargs):
        self.outfile = outfile
        self.in_header = False
        self.table_only = kwargs.get('table_only', False)
        self.tindent = 0 if self.table_only else 4

        timestamp_str = kwargs.get('timestamp', '')

        if timestamp_str == '':
            timestamp_str = str(datetime.now())

        if timestamp_str is not None:
            timestamp_str = ' - ' + timestamp_str
        else:
            timestamp_str = ''

        self.timestamp = timestamp_str

    def begin(self, in_header):
        self.in_header = in_header

        if not self.table_only:
            self.outfile.write(dedent("""\
                <html>
                  <head>
                    <title>Depthcharge results{:s}</title>
                  </head>
                  <body>
                """.format(self.timestamp)))

        self.outfile.write(' ' * self.tindent + '<table>' + os.linesep)
        if self.in_header:
            self.outfile.write(' ' * self.tindent + '  <thead>' + os.linesep)
        else:
            self.outfile.write(' ' * self.tindent + '  <tbody>' + os.linesep)

    def writerow(self, columns):
        ind = 4 if self.table_only else 6

        self.outfile.write(' ' * ind + '<tr>' + os.linesep)
        for col in columns:
            col = col.replace('\n', '<br/>')

            if self.in_header:
                self.outfile.write(' ' * (ind + 2) + '<th>' + os.linesep)
                self.outfile.write(' ' * (ind + 4) + html.escape(col) + os.linesep)
                self.outfile.write(' ' * (ind + 2) + '</th>' + os.linesep)
            else:
                self.outfile.write(' ' * (ind + 2) + '<td>' + os.linesep)
                self.outfile.write(' ' * (ind + 4) + html.escape(col) + os.linesep)
                self.outfile.write(' ' * (ind + 2)  + '</td>' + os.linesep)
        self.outfile.write(' ' * ind + '</tr>' + os.linesep)

        if self.in_header:
            self.outfile.write(indent(dedent("""\
                </thead>
                <tbody>
            """), ' ' * (2 if self.table_only else 4)))

        self.in_header = False

    def finalize(self):
        if self.table_only:
            self.outfile.write(
                dedent("""\
                      </tbody>
                    </table>
                """))
        else:
            self.outfile.write(
                dedent("""\
                        </tbody>
                      </table>
                    </html>
                """))
