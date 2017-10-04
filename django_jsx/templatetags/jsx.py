import re
import json
from hashlib import sha1
import logging

from django import template
from django.template import TemplateSyntaxError
from django.utils.html import escape
from django.template.base import TOKEN_VAR, TOKEN_BLOCK, Variable, VariableDoesNotExist

# Regex to find references to context that start with "ctx."
# and look like "ctx.foo.bar" or "ctx.3.xyz" etc.
R_CTXEXPR = re.compile(r'\.*ctx\.([A-Za-z][\d\w\.]*)')

logger = logging.getLogger(__name__)
register = template.Library()


def set_nested(dictionary, key, value):
    """
    Key is a string with optional "." in it, e.g. "foo.bar".
    Will set value in the dictionary so that
    dictionary['foo']['bar'] = value
    """
    elts = key.split('.')
    if len(elts) == 1:
        # Simple key, just set the value in the dictionary ...
        if elts[0] not in dictionary:
            # ... but only if the key is not already there.
            dictionary[elts[0]] = value
    else:
        # Dotted key. Need to make sure the item with the first
        # part of the key is a dictionary, then set the value
        # into that dictionary using the key with the first part
        # stripped off.

        if not isinstance(dictionary.get(elts[0], None), dict):
            # Either top level expression is not yet in the dictionary, or it
            # is there, but it is not itself a dictionary. It must be a
            # dictionary so we can put our nested value inside of it, so set
            # it to a dictionary.
            dictionary[elts[0]] = {}
        new_key = '.'.join(elts[1:])
        set_nested(dictionary[elts[0]], new_key, value)


def serialize_opportunistically(context, expressions):
    """
    :param context: A template context
    :param expressions: A list of strings that refer to the context, e.g. "foo.bar" or "baz.1"
    :return: A string containing a JSON dump of a dictionary representing the parts of the
      context that are referred to in the expressions, resolved to their final values.
      In other words, a snapshot of the current context, limited to the listed names.
    """
    ctx = {}
    for expression in expressions:
        try:
            value = Variable(expression).resolve(context)
        except VariableDoesNotExist:
            logger.debug(
                "JSX block refers to ctx.%s, but there's no variable by that name "
                "in the Django template context.", expression)
            if context.template:
                string_if_invalid = context.template.engine.string_if_invalid
            else:
                string_if_invalid = ''
            if '%s' in string_if_invalid:
                value = string_if_invalid % expression
            else:
                value = string_if_invalid
        set_nested(ctx, expression, value)
    ctx = json.dumps(ctx)
    return ctx


@register.tag
def jsx(parser, token):
    """

    `jsx` is a block tag for Django templates.

    The block should contain JSX (magic HTML-ish markup for React).
    It can also contain the usual Django template stuff.  (But it
    can't contain another jsx tag.)

    In the JavaScript in the JSX, you can refer to values from
    the Django template context using the `ctx` variable and
    dot-notation. E.g. to access "field.name" from the template
    context, use "ctx.field.name" in the JavaScript.

    See also the compilejsx management command, which provides the
    JavaScript to use the data that this template tag puts into the
    HTML.

    When rendered, the block will turn into an empty script tag whose
    data attributes will contain:

    data-sha1) The sha1 hex digest of the body of the block. (Used by
    jsx_registry.js to find this script tag.)

    data-ctx) A serialized copy of the contents of the template context
    at the point where this block was, filtered to the bits that are referred
    to in the JSX.
    """

    text = []

    while parser.tokens:
        token = parser.next_token()

        if token.contents == 'endjsx':
            break

        if token.contents == 'jsx':
            raise TemplateSyntaxError("jsx blocks cannot be nested in a template")

        if token.token_type == TOKEN_VAR:
            text.append('{{')
        elif token.token_type == TOKEN_BLOCK:
            text.append('{%')

        text.append(token.contents)

        if token.token_type == TOKEN_VAR:
            text.append('}}')
        elif token.token_type == TOKEN_BLOCK:
            text.append('%}')

    return JsxNode(''.join(text))


class JsxNode(template.Node):
    def __init__(self, jsx):
        self.jsx = jsx

    def render(self, context):
        expressions = re.findall(R_CTXEXPR, self.jsx)
        ctx = serialize_opportunistically(context, expressions)
        return '<script type="script/django-jsx" data-sha1="%s" data-ctx="%s"></script>' % \
               (sha1(self.jsx.encode('utf-8')).hexdigest(), escape(ctx))
