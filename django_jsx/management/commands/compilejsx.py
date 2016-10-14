from __future__ import print_function

import os
import re
import hashlib

from django.conf import settings
from django.template.loaders.app_directories import get_app_template_dirs
from django.core.management.base import BaseCommand, CommandError

R_JSX = re.compile(r'\{% *jsx *%\}(.*?)\{% *endjsx *%\}', re.DOTALL)
R_COMPONENT = re.compile(r'<(\w+)')
R_CTXVAR = re.compile(r'({)([A-Za-z]\w?)(\.?)', re.DOTALL)

SETUP_JS = """
function renderAllDjangoJSX(COMPONENTS) {
    Array.prototype.forEach.call(
        document.querySelectorAll('script[type^=script][type$=django-jsx]'), function(el) {
            let ctx = JSON.parse(el.dataset.ctx)
            let component = jsx_registry[el.dataset.sha1](COMPONENTS, ctx)
            ReactDOM.render(component, el)
            el.replaceWith(el.children[0])
        }
    )
}
"""

class Command(BaseCommand):
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '-o'
            '--output',
            action='store',
            dest='output',
        )

    def handle(self, *args, **kwargs):
        output = None
        if kwargs['output']:
            output = open(kwargs['output'], 'w')

        template_dir_list = []
        for each in get_app_template_dirs('templates'):
            template_dir_list.append(each)

        template_list = []
        for each in (template_dir_list + settings.TEMPLATES[0]['DIRS']):
            for dir, dirnames, filenames in os.walk(each):
                for filename in filenames:
                    template_list.append(os.path.join(dir, filename))

        print("import React from 'react';", file=output)
        print("import ReactDOM from 'react-dom';", file=output)
        print("var jsx_registry = {};", file=output)
        for template in template_list:
            try:
                content = open(template).read()
            except IOError:
                pass
            else:
                jsx_blocks = re.findall(R_JSX, content)
                for jsx in jsx_blocks:
                    hash = hashlib.sha1(jsx).hexdigest()
                    jsx = jsx.strip()
                    jsx = re.sub(R_CTXVAR, r'\1__CTX__.\2\3', jsx)
                    components = set(re.findall(R_COMPONENT, jsx))
                    component_statements = []
                    for component in components:
                        component_statements.append("if (Object.hasOwnProperty.call(__COMPONENTS__, '%(component)s'))\n  var {%(component)s} = __COMPONENTS__;\n" % locals())
                    component_statements = ''.join(component_statements)

                    print('jsx_registry["%(hash)s"] = (__COMPONENTS__, __CTX__) => { %(component_statements)s; return (%(jsx)s); }' % locals(), file=output)
        print(SETUP_JS, file=output)
        print("jsx_registry.renderAllDjangoJSX = renderAllDjangoJSX;", file=output)
        print("export default jsx_registry;", file=output)
