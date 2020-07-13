# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring, missing-class-docstring

"""
Unit tests for depthcharge.Stratagem
"""

from copy import copy
from unittest import TestCase

from depthcharge import Stratagem


class DummyStratagemOp:
    _stratagem = None
    _spec = None

    @classmethod
    def get_stratagem_spec(cls):
        return cls._spec


class TestStratagem(TestCase):

    def test_constructor(self):
        with self.subTest('Valid usage'):
            DummyStratagemOp._spec = {'foo': int, 'bar': bool, 'baz': str}
            _ = Stratagem(DummyStratagemOp)

    def test_entries(self):
        expected = []

        DummyStratagemOp._spec = {'foo': int, 'bar': bool, 'baz': str}
        s = Stratagem(DummyStratagemOp)
        self.assertEqual(len(s), 0)

        with self.subTest('Successful append via dict'):
            d = {'foo': 7, 'bar': True, 'baz': 'Test1'}
            expected.append(d)
            s.append(d)
            self.assertEqual(len(s), 1)

        with self.subTest('Successful append via kwargs'):
            s.append(foo=42, bar=False, baz='Test2')
            expected.append({'foo': 42, 'bar': False, 'baz': 'Test2'})
            self.assertEqual(len(s), 2)

        with self.subTest('Successful append via hybrid'):
            # The kwargs are overrides
            d = {'foo': -1, 'bar': False, 'baz': 'Replaced'}

            s.append(d, foo=1337, baz='Test3')
            self.assertEqual(len(s), 3)

            d['foo'] = 1337
            d['baz'] = 'Test3'
            expected.append(copy(d))

            # Confirm that touching d doesn't change the Stratagem's copy.
            d['foo'] = None
            d['bar'] = None
            d['baz'] = None

        with self.subTest('Verify entries'):
            i = 0
            for e in s.entries():
                self.assertEqual(e, expected[i])
                self.assertEqual(s[i], expected[i])
                i += 1

        with self.subTest('Key not present in spec'):
            with self.assertRaises(KeyError):
                s.append(foo=999, bar=False, baz='Test4', extraneous=1)

        with self.subTest('Invalid type test'):
            # Valid cast
            s.append(foo=999, bar=1, baz='Test5')

            with self.assertRaises(ValueError):
                s.append(foo='one', bar=True, baz='Test5')

    def test_str(self):
        DummyStratagemOp._spec = {'foo': int, 'bar': bool, 'baz': str}
        s = Stratagem(DummyStratagemOp)
        s.append(foo=7, bar=False, baz='Test!')

        str_val = str(s)
        self.assertEqual(type(str_val), str)
