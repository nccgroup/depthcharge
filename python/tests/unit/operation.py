# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# Relax style and documentation requirements for unit tests.
# pylint: disable=missing-function-docstring,missing-class-docstring,too-few-public-methods
#

"""
Unit tests for depthcharge.Operation
"""

from unittest import TestCase

from depthcharge import Operation, OperationSet
from depthcharge import OperationNotSupported, OperationFailed


class _DummyCtx:
    def __init__(self, companion=True, cmds=None, env=None, payloads=None):
        self.companion = companion

        self._cmds = cmds or []
        self._env = env or []
        self._payloads = payloads or []


class _DummyOperation(Operation):
    def rank(self, **kwargs):
        return 0


class _Dummy2Operation(Operation):
    def rank(self, **kwargs):
        return 0


class _Dummy3Operation(Operation):
    def rank(self, **kwargs):
        return 0


class TestOperation(TestCase):

    def test_constructor(self):
        op = _DummyOperation(_DummyCtx())
        self.assertNotEqual(op, None)

    def test_name(self):
        op = _DummyOperation(_DummyCtx())
        self.assertEqual(op.name, '_DummyOperation')

    def test_companion_req(self):
        _DummyOperation._required['companion'] = True
        op = _DummyOperation(_DummyCtx())
        self.assertNotEqual(op._req, None)

        with self.assertRaises(OperationNotSupported):
            ctx = _DummyCtx(companion=None)
            _DummyOperation._required['companion'] = True
            op = _DummyOperation(ctx)

        _DummyOperation._required['companion'] = False

    def test_command_req(self):
        ctx = _DummyCtx(cmds=['cmd1', 'cmd2', 'cmd3'])
        _DummyOperation._required['commands'] = ['cmd2']
        op = _DummyOperation(ctx)
        self.assertNotEqual(op._req, None)

        _DummyOperation._required['commands'] = ['cmd4']
        with self.assertRaises(OperationNotSupported):
            op = _DummyOperation(ctx)

        _DummyOperation._required['commands'] = []

    def test_envvar_req(self):
        ctx = _DummyCtx(env=['env1', 'env2', 'env3'])
        _DummyOperation._required['variables'] = ['env2']
        op = _DummyOperation(ctx)
        self.assertNotEqual(op._req, None)

        with self.assertRaises(OperationNotSupported):
            _DummyOperation._required['variables'] = ['env2', 'env4']
            op = _DummyOperation(ctx)

        _DummyOperation._required['variables'] = []

    def test_payload_reqs(self):
        ctx = _DummyCtx(payloads=['p1', 'p2', 'p3'])
        _DummyOperation._required['payloads'] = ['p1', 'p2', 'p3']
        _ = _DummyOperation(ctx)

        with self.assertRaises(OperationNotSupported):
            _DummyOperation._required['payloads'] = ['p4']
            _ = _DummyOperation(ctx)

        _DummyOperation._required['payloads'] = []

    def test_host_programs_reqs(self):
        _DummyOperation._required['host_programs'] = ['python3']
        _ = _DummyOperation(_DummyCtx())

        with self.assertRaises(OperationNotSupported):
            _DummyOperation._required['host_programs'] = ['xXx_a_nonexistant_program_xXx']
            _ = _DummyOperation(_DummyCtx())

        _DummyOperation._required['host_programs'] = []


class TestOperationSet(TestCase):

    def test(self):
        s = OperationSet(suffix='Operation')
        s.add(_DummyOperation(_DummyCtx()))
        s.add(_Dummy2Operation(_DummyCtx()))
        s.add(_Dummy3Operation(_DummyCtx()))

        self.assertEqual(len(s), 3)

        # Exercise iterator and name-based access
        for op in s:
            self.assertTrue(isinstance(s[op.name], Operation))

        self.assertTrue(s[0] is s['_DummyOperation'])

        # Suffix-based search
        op = s.find('_Dummy2')
        self.assertTrue(op is s['_Dummy2Operation'])

        op = s.find('_DummyOperation')
        self.assertTrue(op is s['_DummyOperation'])


class TestOperationNotSupported(TestCase):

    def test(self):
        msg = 'Test Operation Not Supported: '
        try:
            raise OperationNotSupported(_DummyOperation, msg + '{:d}', 42)
        except OperationNotSupported as e:
            self.assertEqual(str(e), '_DummyOperation - ' + msg + '42')
            return

        raise RuntimeError


class TestOperationFailed(TestCase):
    def test(self):
        msg = 'Test Operation Failed'
        try:
            raise OperationFailed(msg)
        except OperationFailed as e:
            self.assertEqual(str(e), msg)
            return

        raise RuntimeError
