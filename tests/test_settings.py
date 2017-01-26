# SETTINGS file for running tests on this pluggable application

# https://docs.djangoproject.com/en/1.10/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications

SECRET_KEY = 'fake-key'
INSTALLED_APPS = [
    "tests",
    "django_jsx",
]

# We need a database configuration or Django complains, but we're not
# actually using the database. An in-memory Sqlite database should
# be very light-weight and not leave anything behind after testing.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}


# COPIED from project template in Django 1.10
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
