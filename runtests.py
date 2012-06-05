#!/usr/bin/env python
import os
import sys

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'autocompleter_test.db', 
                'USER': '',
                'PASSWORD': '',
                'HOST': '',
                'PORT': '',
            }
        },
        SITE_ID=1,
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django_nose',
            'autocompleter_test_project',
            'autocompleter',
        ],
        AUTOCOMPLETER_REDIS_CONNECTION = {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
        },
        TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    )

from django_nose import NoseTestSuiteRunner
from django.test.simple import DjangoTestSuiteRunner

def runtests(*test_labels):
    if not test_labels:
        test_labels = ['autocompleter_test_project']
    ac_dir = os.path.join(os.path.dirname(__file__), 'autocompleter')
    sys.path.insert(0, ac_dir)
    tr = NoseTestSuiteRunner(verbosity=2, interactive=True)
    failures = tr.run_tests(test_labels)
    sys.exit(failures)

if __name__ == '__main__':
    runtests(*sys.argv[1:])