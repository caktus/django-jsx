from __future__ import unicode_literals
import json

from django.template import Context
from django.template import VariableDoesNotExist
from django.test import TestCase

from django_jsx.templatetags.jsx import serialize_opportunistically


class SerializeOpportunisticallyTest(TestCase):
    def test_no_expressions(self):
        obj = {
            'a': 1,
            'b': 2,
            'c': 3
        }
        result = serialize_opportunistically(obj, [])
        self.assertEqual({}, json.loads(result))

    def test_simple_expressions(self):
        obj = {
            'a': 1,
            'b': 2,
            'c': 3
        }
        result = serialize_opportunistically(obj, ['a', 'b'])
        expect = {
            'a': 1,
            'b': 2,
        }
        self.assertEqual(expect, json.loads(result))

    def test_bad_reference(self):
        # If we refer to something not in the context, we get a meaningful exception
        with self.assertRaises(VariableDoesNotExist) as raise_context:
            serialize_opportunistically({}, ['no.such.variable'])
            exc = raise_context.exc
            self.assertIn("there's no variable no.such.variable", str(exc))

    def test_nested_expressions(self):
        obj = {
            'a': {
                'd': 4,
                'f': {
                    'g': 'Hello'
                }
            },
            'b': 2,
            'c': {
                'e': 5
            }
        }
        result = serialize_opportunistically(Context(obj), ['a.d', 'b', 'c.e', 'a.f', 'a.f.g'])
        expect = {
            'a': {

                'd': 4,
                'f': {
                    'g': 'Hello'
                }
            },
            'b': 2,
            'c': {
                'e': 5
            },
        }
        self.assertEqual(expect, json.loads(result))

    def test_with_callable(self):
        def call1():
            return "called 1"

        def call2():
            return "called 2"

        obj = {
            'call1': call1,
            'a': {
                'b': call2,
                'c': call1,
            }
        }
        result = serialize_opportunistically(obj, ['call1', 'a.b'])
        expect = {
            'call1': 'called 1',
            'a': {
                'b': 'called 2'
            }
        }
        self.assertEqual(expect, json.loads(result))
