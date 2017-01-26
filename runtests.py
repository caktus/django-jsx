#!/usr/bin/env python
# https://docs.djangoproject.com/en/1.10/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    test_modules = sys.argv[1:] if len(sys.argv) > 1 else ["tests"]
    failures = test_runner.run_tests(test_modules)
    sys.exit(bool(failures))
