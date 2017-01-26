"""Tests for finding all the template files"""
from __future__ import unicode_literals
import os.path

from django.test import TestCase
from django.test import override_settings

from django_jsx.management.commands.compilejsx import list_template_files


class TemplateFindingTest(TestCase):
    @override_settings(
        INSTALLED_APPS=['tests'],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
            },
        ])
    def test_finding_templates_with_test_app(self):
        # If 'tests' is the only installed app, we find its templates
        this_dir = os.path.dirname(__file__)
        result = list_template_files()
        expected = [
            os.path.join(this_dir, "templates", filename)
            for filename in
            [
                "test_file_B.html",
                "test_file_A.txt",
                "test_dir_C/test_file_D.zip",
            ]
        ]
        self.assertEqual(set(expected), set(result))

    @override_settings(
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
            },
        ],
        INSTALLED_APPS=[])
    def test_finding_templates_without_test_app(self):
        # If there are no installed apps, we don't find any templates
        result = list_template_files()
        expected = []
        self.assertEqual(set(expected), set(result))

    @override_settings(
        INSTALLED_APPS=['tests'],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [os.path.join(os.path.dirname(__file__), "more_templates")],
                'APP_DIRS': True,
            },
        ])
    def test_finding_templates_in_additional_dirs(self):
        # If the user configured additional dirs to find templates in, we spot them
        result = list_template_files()
        this_dir = os.path.dirname(__file__)
        self.assertEqual(
            set(result),
            {
                os.path.join(this_dir, "templates", filename)
                for filename in
                [
                    "test_file_B.html",
                    "test_file_A.txt",
                    "test_dir_C/test_file_D.zip",
                ]
            } | {
                os.path.join(this_dir, "more_templates", "another_template.html")
            }
        )

    @override_settings(
        INSTALLED_APPS=['test'],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [os.path.join(os.path.dirname(__file__), "more_templates")],
                'APP_DIRS': False,
            },
        ])
    def test_finding_templates_with_app_dirs_false(self):
        this_dir = os.path.dirname(__file__)
        result = list_template_files()
        expected = [os.path.join(this_dir, "more_templates", "another_template.html")]
        self.assertEqual(set(expected), set(result))
