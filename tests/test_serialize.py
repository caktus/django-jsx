from __future__ import unicode_literals
import json

from django.template import Context
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

    def test_missing_variable(self):
        """
        In Django templates, if a variable is not defined in the context, then
        Django sets that variable to the special value ``string_if_invalid``
        which is normally the empty string, but is customizable in Django
        settings TEMPLATES['OPTIONS']['string_if_invalid']. Django doesn't
        raise a user-visible error, so we should do the same thing in
        django_jsx.
        """
        result = serialize_opportunistically(Context(), ['no.such.variable'])
        expect = {
            'no': {
                'such': {
                    'variable': ''
                }
            }
        }
        self.assertEqual(expect, json.loads(result))

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

    def test_top_level_object_doesnt_clobber_nested_expressions(self):
        # create an object with some attributes
        class Location(dict):
            full_name = 'New York'
        location = Location()

        # the order of expressions is important here
        expressions = [
            'location.full_name',  # set up the nested dict
            'location',            # this should not clobber the nested dict
        ]
        obj = {'location': location}
        result = serialize_opportunistically(Context(obj), expressions)
        expect = {
            'location': {
                'full_name': 'New York',
            }
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
