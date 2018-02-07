from __future__ import print_function, unicode_literals

import os
import re
import hashlib

from django.apps import apps
import django.template
from django.template.backends.django import DjangoTemplates
from django.core.management.base import BaseCommand

# Regex matching all JSX blocks in a template
R_JSX = re.compile(r'\{% *jsx *%\}(.*?)\{% *endjsx *%\}', re.DOTALL)

# Regex to spot the beginning of an HTML element in JSX text
R_COMPONENT = re.compile(r'<(\w+)')

START_JS = """
import React from 'react';
import ReactDOM from 'react-dom';
var jsx_registry = {};
"""

# <script type="script/django-jsx" ...>

END_JS = """
function renderAllDjangoJSX(COMPONENTS) {
    Array.prototype.forEach.call(
        // Find all "django-jsx" scripts which are hooks to render and inject react components
        document.querySelectorAll('script[type^=script][type$=django-jsx]'),
        function(el) {

            // Extract serialized context data for rendering the component and get the component
            // from our database
            let ctx = JSON.parse(el.dataset.ctx)
            let component = jsx_registry[el.dataset.sha1](COMPONENTS, ctx)

            // Actually render and place the component into the pgae:
            // 1) Create a placeholder to render the component into
            // 2) Render the component into the placeholder
            // 3) Replace the placeholder with the actual component
            // 4) Remove the <script> hook to clean up

            el.insertAdjacentHTML("afterend", "<span></span>")

            ReactDOM.render(component, el.nextSibling)

            //el.parentNode.replaceChild(el.nextSibling.children[0], el.nextSibling)
            //el.parentNode.removeChild(el)
        }
    )
}

jsx_registry.renderAllDjangoJSX = renderAllDjangoJSX;
export default jsx_registry;
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

        compile_templates(list_template_files(), output)

        if output is not None:
            output.close()


def list_template_files():
    """
    Return list of template files everywhere Django looks for them.
    """
    engines = django.template.engines

    template_dirs = []
    # 'engines' is not a dictionary, it just behaves like one in some ways
    for engine_name in engines:
        engine = engines[engine_name]
        if isinstance(engine, DjangoTemplates):
            # We only handle Django templates
            template_dirs.extend(engine.template_dirs)

    template_list = []
    for each in template_dirs:
        for dir, dirnames, filenames in os.walk(each):
            for filename in filenames:
                template_list.append(os.path.join(dir, filename))

    for appname, app in apps.app_configs.items():
        app_dir = os.path.dirname(app.module.__file__)
        for dir, dirnames, filenames in os.walk(os.path.join(app_dir, "templates")):
            for filename in filenames:
                template_list.append(os.path.join(dir, filename))

    return template_list


def compile_templates(template_list, output=None):
    """
    Write a jsx_registry.js file to output (or stdout if output is None),
    containing boilerplate at top and bottom, and a jsx_registry entry for
    each jsx block found in any of the template files listed in `template_list`.
    :param template_list: A list of template filenames.
    :param output: A file-like object to write to, or None.
    :return: nothing
    """
    print(START_JS, file=output)
    for template in template_list:
        first = True
        try:
            content = open(template).read()
        except (IOError, UnicodeDecodeError):
            pass
        else:
            jsx_blocks = re.findall(R_JSX, content)
            for jsx in jsx_blocks:
                if first:
                    # Add comment indicating the template that these blocks came from.
                    # Can help with debugging.
                    first = False
                    print('/* %s */' % template, file=output)
                hash = hashlib.sha1(jsx.encode('utf-8')).hexdigest()

                jsx = jsx.strip()
                components = set(re.findall(R_COMPONENT, jsx))
                component_statements = []
                # Sort for repeatable output, making for easier debugging and testing
                for component in sorted(components):
                    component_statements.append(
                        "if (Object.hasOwnProperty.call(COMPONENTS, '%(component)s')) "
                        "var {%(component)s} = COMPONENTS;\n" % locals())
                component_statements.append('return (%(jsx)s);' % locals())
                component_statements = ''.join(component_statements)

                print('jsx_registry["%(hash)s"] = '
                      '(COMPONENTS, ctx) => {\n%(component_statements)s\n}' % locals(), file=output)
    print(END_JS, file=output)
