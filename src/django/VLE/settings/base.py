"""
Django settings for VLE project.

Generated by 'django-admin startproject' using Django 2.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import os
from collections import OrderedDict
from dataclasses import dataclass
from datetime import timedelta

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    # Setting DSN to an empty value or None will disable the SDK
    dsn=os.environ.get('SENTRY_DSN', None),
    integrations=[DjangoIntegration(), CeleryIntegration()],
    release=os.environ['RELEASE_VERSION']
)

MiB = 2**20
USER_MAX_FILE_SIZE_BYTES = 10 * MiB
USER_MAX_TOTAL_STORAGE_BYTES = 100 * MiB
USER_MAX_EMAIL_ATTACHMENT_BYTES = USER_MAX_FILE_SIZE_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = USER_MAX_FILE_SIZE_BYTES

# Format follow by our frontend date and datetime pickers
ALLOWED_DATE_FORMAT = '%Y-%m-%d'
ALLOWED_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINK = os.environ['BASELINK']
API_URL = os.environ['API_URL']
CODE_VERSION = os.environ['CODE_VERSION']

STATIC_URL = '/static/'
DEFAULT_PROFILE_PICTURE = '/unknown-profile.png'
# NOTE: Public media directory (not used as such, should probably be renamed.)
MEDIA_URL = 'media/'

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

EXPLICITLY_WITHOUT_CONTEXT = -1

# Email settings
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
ANYMAIL = {
    'MAILGUN_API_KEY': os.environ['MAILGUN_API_KEY'],
    'MAILGUN_API_URL': 'https://api.eu.mailgun.net/v3',
    'MAILGUN_SENDER_DOMAIN': os.environ['MAILGUN_SENDER_DOMAIN'],
}
EMAIL_SENDER_DOMAIN = ANYMAIL['MAILGUN_SENDER_DOMAIN']


@dataclass
class EmailToSender:
    label: str

    @property
    def email(self) -> str:
        return f'{self.label}@{EMAIL_SENDER_DOMAIN}'

    @property
    def sender(self) -> str:
        name = self.email.split('@')[0].capitalize()
        return f'eJournal | {name}<{self.email}>'


class Emails:
    support = EmailToSender('support')
    noreply = EmailToSender('noreply')
    contact = EmailToSender('contact')

EMAILS = Emails()


# LTI settings
LTI_SECRET = os.environ['LTI_SECRET']
LTI_KEY = os.environ['LTI_KEY']
ROLES = OrderedDict({
    'Teacher': [
        'instructor',
        'administrator',
        'urn:lti:role:ims/lis/instructor',
        'urn:lti:role:ims/lis/contentdeveloper',
        'urn:lti:role:ims/lis/administrator',
    ],
    'TA': [
        'teachingassistant',
        'urn:lti:role:ims/lis/mentor',
        'urn:lti:role:ims/lis/teachingassistant',
    ],
    'Student': [
        'learner',
        'urn:lti:role:ims/lis/learner',
    ]
})
LTI_ROLES = OrderedDict({
    'instructor': 'Teacher',
    'administrator': 'Teacher',
    'urn:lti:role:ims/lis/instructor': 'Teacher',
    'urn:lti:role:ims/lis/contentdeveloper': 'Teacher',
    'urn:lti:role:ims/lis/administrator': 'Teacher',
    'urn:lti:role:ims/lis/mentor': 'TA',
    'urn:lti:role:ims/lis/teachingassistant': 'TA',
    'urn:lti:role:ims/lis/learner': 'Student',
    'learner': 'Student',
})
# Names we have encountered used for test students
LTI_TEST_STUDENT_FULL_NAMES = {'Test student'}

# Celery settings
CELERY_BROKER_URL = os.environ['BROKER_URL']
CELERY_RESULT_BACKEND = 'django-db://{}:{}@{}:{}/{}'.format(
    os.environ['DATABASE_USER'],
    os.environ['DATABASE_PASSWORD'],
    os.environ['DATABASE_HOST'],
    os.environ['DATABASE_PORT'],
    os.environ['DATABASE_NAME']
)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
DJANGO_CELERY_BEAT_TZ_AWARE = False


# Webserver settings
WEBSERVER_TIMEOUT = 60


# Read for webserver, r + w for django
FILE_UPLOAD_PERMISSIONS = 0o644

GROUP_API = 'https://api.datanose.nl/Groups/{}'

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'VLE.apps.VLEConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'anymail',
    'rest_framework',
    'corsheaders',
    'django_celery_results',
    'django_celery_beat',
    'computedfields',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'VLE.utils.authentication.SentryContextAwareJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'VLE.utils.throttle.GDPRThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'gdpr': '3/day',
    },
}

AUTH_USER_MODEL = "VLE.User"

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=2),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'id',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'VLE.utils.error_handling.ErrorMiddleware',
    'csp.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'VLE.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (os.path.join(BASE_DIR, 'templates/email_templates/'),),
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

WSGI_APPLICATION = 'VLE.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'CET'
USE_I18N = True
USE_L10N = True
USE_TZ = False

DEFAULT_LMS_PROFILE_PICTURE = os.environ['DEFAULT_LMS_PROFILE_PICTURE']
