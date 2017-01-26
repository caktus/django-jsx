from __future__ import unicode_literals

import hashlib
import io
import os
import sys
import tempfile

from django.core.management import call_command
from django.test import TestCase

from django_jsx.management.commands.compilejsx import compile_templates, END_JS, START_JS


class CompileJSXTest(TestCase):
    """
    Tests for the compilejsx management command, which looks at all the
    template files and emits a jsx_registry.jsx file with information about
    the JSX blocks in the templates, and some JavaScript code to make use of the
    information.
    """
    @classmethod
    def setUpClass(cls):
        cls.files_to_delete = []

    @classmethod
    def tearDownClass(cls):
        for fn in cls.files_to_delete:
            try:
                os.remove(fn)
            except Exception as e:
                print(e)
        delattr(cls, 'files_to_delete')

    @classmethod
    def make_testfile(cls):
        """Returns name of the test file"""
        (filehandle, filename) = tempfile.mkstemp()
        os.close(filehandle)
        cls.files_to_delete.append(filename)
        return filename

    def test_invoking_for_stdout(self):
        # Default output is to stdout
        out = io.StringIO()
        orig_out = sys.stdout
        try:
            sys.stdout = out
            call_command('compilejsx')
            self.assertIn(START_JS, out.getvalue())
        finally:
            sys.stdout = orig_out

    def test_invoking_to_output_file(self):
        # --output sends output to named file
        filename = type(self).make_testfile()
        call_command('compilejsx', output=filename)
        output = open(filename, "rb").read().decode('utf-8')
        self.assertIn(START_JS, output)

    def try_it(self, test_content, expected_result, raw=False):
        # Make template file containing a jsx block whose body is `test_content`, run
        # compilejsx, and make sure the output is `expected_result`.  Or if `raw` is true,
        # then `test_content` is the entire content of the test file to compile.
        filename = type(self).make_testfile()
        expected_result = expected_result.replace('{filename}', filename)
        if raw:
            test_text = test_content
        else:
            test_text = "{% jsx %}" + test_content + "{% endjsx %}"
        with open(filename, "w") as f:
            f.write(test_text)

        # "Compile" it
        output = io.StringIO()
        compile_templates([filename], output)

        # Strip boilerplate to simplify checking
        start = len(START_JS) + 1
        end = 0 - (len(END_JS) + 1)
        result = output.getvalue()[start:end - 1]

        self.maxDiff = None
        self.assertEqual(expected_result, result)

    def test_empty_template(self):
        # If template is empty, output is just the boilerplate.
        # Make empty file
        filename = type(self).make_testfile()
        with open(filename, "w"):
            pass
        # "Compile" it
        output = io.StringIO()
        compile_templates([filename], output)

        # Check boilerplate
        self.assertTrue(output.getvalue().startswith(START_JS + "\n"))
        self.assertTrue(output.getvalue().endswith(END_JS + "\n"))

        # Strip boilerplate to simplify checking what's not boilerplate
        start = len(START_JS) + 1
        end = 0 - (len(END_JS) + 1)
        result = output.getvalue()[start:end - 1]
        self.assertEqual('', result)

    def test_template_with_empty_jsx_block(self):
        # If the block is empty, the output is pretty minimal

        test_content = ''
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
return ();
}''' % sha1
        self.try_it(test_content, expected)

    def test_template_with_minimal_component(self):
        # If the block just has a minimal React component, the output includes
        # a jsx_registry entry for it.
        test_content = '<NeatThing/>'
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'NeatThing')) var {NeatThing} = COMPONENTS;
return (%s);
}''' % (sha1, test_content)
        self.try_it(test_content, expected)

    def test_template_with_component_with_static_property(self):
        # Static properties don't change the output
        test_content = '<NiftyFeature foo="bar"/>'
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'NiftyFeature')) var {NiftyFeature} = COMPONENTS;
return (%s);
}''' % (sha1, test_content)
        self.try_it(test_content, expected)

    def test_template_with_component_with_variable_property(self):
        # Variable properties don't change the output
        test_content = '<WonderBar foo="{{ ctx.bar }}"/>'
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'WonderBar')) var {WonderBar} = COMPONENTS;
return (%s);
}''' % (sha1, test_content)
        self.try_it(test_content, expected)

    def test_template_with_component_with_expression_property(self):
        # Expressions in properties don't change the output
        test_content = '<Component foo="{{ ctx.bar ? 3 : ctx.zip }}"/>'
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'Component')) var {Component} = COMPONENTS;
return (%s);
}''' % (sha1, test_content)
        self.try_it(test_content, expected)

    def test_template_with_component_with_deep_variable(self):
        # Variable properties don't change the output
        test_content = '<Component foo="{{ ctx.foo.bar.baz }}"/>'
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'Component')) var {Component} = COMPONENTS;
return (%s);
}''' % (sha1, test_content)
        self.try_it(test_content, expected)

    def test_template_with_nested_html(self):
        # Each tag level contributes to the output. compilejsx doesn't know or care
        # which tags are React components.
        test_content = '''<div id="search-mnt" className="search-section-mnt">
        <MobileModalSectionSearch
            section="attraction"
            sectionLabel="Attractions"
            currentLocation={ctx.location ? ctx.location.full_name : null}
            mapLink={ctx.map_link}
            useDistance={ctx.location && ctx.location.kind === 'city'}
            subCat={ctx.type_slug || ""}
        />
    </div>'''
        sha1 = hashlib.sha1(test_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'MobileModalSectionSearch')) var {MobileModalSectionSearch} = COMPONENTS;
if (Object.hasOwnProperty.call(COMPONENTS, 'div')) var {div} = COMPONENTS;
return (%s);
}''' % (sha1, test_content)  # noqa (long line hard to avoid here)
        self.try_it(test_content, expected)

    def test_duplicate_blocks_with_different_contexts(self):
        # compilejsx comes up with the same jsx_registry entry repeatedly if there are multiple
        # blocks with the same content but with different contexts.  But this is okay, as
        # the rendered template will have a tag for each occurrence of the block, each
        # with its own unique context, and the JavaScript will render a component for
        # each one using that context.
        block_content = '<Component prop={ctx.foo}/>'
        test_content = '''{% load jsx %}
        {% with foo=1 %}
            {% jsx %}BLOCK_CONTENT{% endjsx %}
        {% endwith %}
        {% with foo=2 %}
            {% jsx %}BLOCK_CONTENT{% endjsx %}
        {% endwith %}
        '''.replace("BLOCK_CONTENT", block_content)
        sha1 = hashlib.sha1(block_content.encode('utf-8')).hexdigest()
        expected = '''/* {filename} */
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'Component')) var {Component} = COMPONENTS;
return (%s);
}
jsx_registry["%s"] = (COMPONENTS, ctx) => {
if (Object.hasOwnProperty.call(COMPONENTS, 'Component')) var {Component} = COMPONENTS;
return (%s);
}''' % (sha1, block_content, sha1, block_content)
        self.try_it(test_content, expected, raw=True)
