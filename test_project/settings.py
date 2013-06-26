DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'autocompleter_test.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

SITE_ID = 1

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django_nose',
    'test_app',
    'autocompleter',
]

AUTOCOMPLETER_REDIS_CONNECTION = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = [
    '--verbosity=2',
    '--nocapture',
    #'--with-coverage',
    #'--cover-package=autocompleter'
]

SECRET_KEY = 'asdvdfbdgbrf076'
