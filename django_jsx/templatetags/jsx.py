import re
import json
from hashlib import sha1

from django import template
from django.utils.html import escape
from django.template.base import TOKEN_VAR, TOKEN_BLOCK

R_CTXEXPR = re.compile(r'\.*ctx\.([A-Za-z][\d\w\.]*)')

register = template.Library()

def serialize_opportunistically(obj, expressions):
    expressions = [
        expression.split('.')
        for expression in expressions
    ]
    return json.dumps(pack_opportunistically(obj, [], expressions))

def pack_opportunistically(obj, path, expressions):
    if isinstance(obj, (tuple, list)):
        return [
            pack_opportunistically(item, path + [str(i)], expressions)
            for i, item in enumerate(obj)
        ]
    elif isinstance(obj, template.Context):
        return pack_opportunistically(obj.flatten(), path, expressions)
    elif isinstance(obj, dict):
        return dict(
            (k, pack_opportunistically(obj[k], path + [k], expressions))
            for k in obj
        )
    elif isinstance(obj, (float, int, basestring)):
        return obj
    else:
        # Is this a thing we need for an expected expression?
        packed = {}
        for expression_path in expressions:
            if path == expression_path[:len(path)]:
                # This is part of an expected expression, so keep walking
                # for the next part of the expression
                try:
                    next_step = expression_path[len(path)]
                except IndexError:
                    # done stepping through expression path
                    continue
                else:
                    # Look for an item or attribute by the next step
                    try:
                        next_obj = obj[next_step]
                    except (KeyError, TypeError, IndexError):
                        try:
                            next_obj = getattr(obj, next_step)
                        except AttributeError:
                            next_obj = None
                    if callable(next_obj):
                        next_obj = next_obj()
                    packed[next_step] = pack_opportunistically(next_obj, path + [next_step], expressions)
        return packed or None

@register.tag
def jsx(parser, token):
    text = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == 'endjsx':
            break
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
        return '<script type="script/django-jsx" data-sha1="%s" data-ctx="%s" data-expressions="%s"></script>' % (sha1(self.jsx).hexdigest(), escape(ctx), expressions)
