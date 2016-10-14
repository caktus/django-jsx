import json
from hashlib import sha1

from django import template
from django.utils.html import escape
from django.template.base import TOKEN_VAR, TOKEN_BLOCK

register = template.Library()

def serialize_opportunistically(obj):
    return json.dumps(pack_opportunistically(obj))

def pack_opportunistically(obj):
    if isinstance(obj, (tuple, list)):
        return [pack_opportunistically(i) for i in obj]
    elif isinstance(obj, (basestring, int, float)):
        return obj
    elif isinstance(obj, template.Context):
        return pack_opportunistically(obj.flatten())
    elif isinstance(obj, dict):
        return dict(
            (k, pack_opportunistically(obj[k]))
            for k in obj
        )
    else:
        return None

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
        ctx = serialize_opportunistically(context)
        return '<script type="script/django-jsx" data-sha1="%s" data-ctx="%s"></script>' % (sha1(self.jsx).hexdigest(), escape(ctx))
