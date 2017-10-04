from __future__ import unicode_literals

import hashlib
import json
import re
from django.template import Context, Engine
from django.template import TemplateSyntaxError
from django.test import TestCase

from django_jsx.templatetags.jsx import set_nested


RESULT_REGEX = re.compile(
    r'<script type="script/django-jsx" data-sha1="(?P<sha1>[0-9a-f]+)" '
    r'data-ctx="(?P<ctx>.*)"></script>')

DEFAULT_CONTEXT = {
    'False': False,
    'True': True,
    'None': None
}

ENGINE = Engine.get_default()


def unescape(s):
    return s.replace('&amp;', '&').replace('&lt;', '<')\
        .replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")


class SetNestedTest(TestCase):
    def test_simple_key(self):
        d = {}
        set_nested(d, 'foo', 3)
        self.assertEqual({'foo': 3}, d)

    def test_one_level(self):
        d = {}
        set_nested(d, 'foo.bar', 3)
        self.assertEqual({'foo': {'bar': 3}}, d)

    def test_two_levels(self):
        d = {}
        set_nested(d, 'foo.bar.baz', 3)
        self.assertEqual({'foo': {'bar': {'baz': 3}}}, d)

    def test_with_existing_stuff(self):
        d = {'one': 1, 'foo': {'baz': 2}}
        set_nested(d, 'foo.bar', 3)
        self.assertEqual({'one': 1, 'foo': {'bar': 3, 'baz': 2}}, d)

    def test_with_existing_object(self):
        """
        If a top level item to be serialized is an object, we shouldn't fail at
        trying to set the lower level item.
        """
        d = {'foo': object()}
        set_nested(d, 'foo.bar', 3)
        self.assertEqual({'foo': {'bar': 3}}, d)

    def test_top_level_item_doesnt_clobber_nested(self):
        # foo.bar has previously been set
        d = {'foo': {'bar': 3}}
        # if we later try to set foo, we shouldn't clobber foo.bar
        set_nested(d, 'foo', object())
        self.assertEqual({'foo': {'bar': 3}}, d)


class JsxTagTest(TestCase):
    def test_loading_tags(self):
        # We can `load` the tag library
        engine = Engine.get_default()
        template_object = engine.from_string("{% load jsx %}")
        result = template_object.render(Context({}))
        self.assertEqual("", result)

    def try_it(self, content, expected_ctx, raw=False, context=None):
        # Assert that if we do a {% jsx %} block with the given content, that we
        # get the standard empty script tag in the output, the data-sha1 attribute
        # has the sha1 digest of the content, and the `data-ctx` is
        # a JSON-encoding of `expected_ctx`.
        # If `raw` is True, use `content` as the entire template content, not just
        # the insides of a jsx block, and just return the result rather than trying
        # to validate it.
        # If `context` is given, use it as the template context.
        if raw:
            template_content = content
        else:
            template_content = "{% load jsx %}{% jsx %}" + content + "{% endjsx %}"
        template_object = ENGINE.from_string(template_content)
        result = template_object.render(Context(context or {}))
        if raw:
            return result
        else:
            m = RESULT_REGEX.match(result)
            self.assertEqual(m.group('sha1'), hashlib.sha1(content.encode('utf-8')).hexdigest())
            ctx = json.loads(unescape(m.group('ctx')))
            self.assertEqual(ctx, expected_ctx)

    def test_empty_tag(self):
        # No content -> no context
        expected_ctx = {}
        self.try_it('', expected_ctx)

    def test_empty_component(self):
        # No references to context -> no context
        content = '<Component/>'
        expected_ctx = {}
        self.try_it(content, expected_ctx)

    def test_component_with_properties_using_context(self):
        # Refer to context -> context we used gets included
        content = '''<Component prop1="foo" prop2={ctx.False} prop3={not ctx.True}/>'''
        expected_ctx = {'False': False, 'True': True}
        self.try_it(content, expected_ctx)

    def test_referring_to_elements_numerically(self):
        content = '''<Component prop2={ctx.list.0}/>'''
        context = {'list': [1, 2, 3]}
        expected_ctx = {'list': {'0': 1}}
        self.try_it(content, expected_ctx, context=context)

    def test_missing_variables(self):
        "If variable is missing, set it to empty string (by default)."
        content = '''<Component prop2={ctx.does.not.exist}/>'''
        context = {}
        expected_ctx = {'does': {'not': {'exist': ''}}}
        self.try_it(content, expected_ctx, context=context)

    def test_missing_variables_with_string_if_invalid_set(self):
        "If variable is missing, use Engine's string_if_invalid value."
        ENGINE.string_if_invalid = 'hey, missing var -> %s'
        content = '''<Component prop2={ctx.does.not.exist}/>'''
        context = {}
        expected_ctx = {'does': {'not': {'exist': 'hey, missing var -> does.not.exist'}}}
        self.try_it(content, expected_ctx, context=context)

    # SHOULD NOT BE ALLOWED - compilejsx will reject
    # def test_two_identical_blocks_with_different_contexts(self):
    #     # If an identical block is repeated with different context values, we
    #     # can't handle it, so it should report an error and force the user to make
    #     # the blocks different.
    #     block_content = '<Component prop={ctx.foo}/>'
    #     test_content = '''{% spaceless %}
    #     {% load jsx %}
    #     {% with foo=1 %}
    #         {% jsx %}BLOCK_CONTENT{% endjsx %}
    #     {% endwith %}
    #     {% with foo=2 %}
    #         {% jsx %}BLOCK_CONTENT{% endjsx %}
    #     {% endwith %}
    #     {% endspaceless %}'''.replace("BLOCK_CONTENT", block_content)
    #     result = self.try_it(test_content, None, raw=True)
    #     sha1 = hashlib.sha1(block_content.encode('utf-8')).hexdigest()
    #     expected_output = (
    #         '<script type="script/django-jsx" data-sha1="SHA1" data-ctx="{"foo": 1}"></script>'
    #         '<script type="script/django-jsx" data-sha1="SHA1" data-ctx="{"foo": 2}"></script>'
    #         .replace('SHA1', sha1))
    #     self.assertEqual(expected_output, unescape(result))

    def test_block_in_loop(self):
        # We can put a block in a loop, and we get an output tag for each loop iteration
        test_content = '''{% spaceless %}
        {% load jsx %}
        {% for i in values %}
            {% jsx %}<Component key={ ctx.i }/>{% endjsx %}
        {% endfor %}
        {% endspaceless %}'''
        result = self.try_it(test_content, None, raw=True, context={'values': [1, 2, 3]})
        sha1 = hashlib.sha1('<Component key={ ctx.i }/>'.encode('utf-8')).hexdigest()
        expected_output = (
            '<script type="script/django-jsx" data-sha1="SHA1" data-ctx="{"i": 1}"></script>'
            '<script type="script/django-jsx" data-sha1="SHA1" data-ctx="{"i": 2}"></script>'
            '<script type="script/django-jsx" data-sha1="SHA1" data-ctx="{"i": 3}"></script>'
            .replace('SHA1', sha1))
        self.assertEqual(expected_output, unescape(result))

    def test_nested_blocks(self):
        # Nested JSX blocks are not allowed
        test_content = '''
        {% load jsx %}
        {% jsx %}
            <Component1>
                {% jsx %}<Component2/>{% endjsx %}
            </Component1>
        {% endjsx %}'''
        with self.assertRaises(TemplateSyntaxError) as raise_context:
            self.try_it(test_content, None, raw=True,)
            exc = raise_context.exc
            self.assertIn('jsx blocks cannot be nested in a template', str(exc))
