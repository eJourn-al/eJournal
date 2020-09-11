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
from datetime import timedelta

import pytz
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=None if 'TRAVIS' in os.environ else os.environ['SENTRY_DSN'],
    integrations=[DjangoIntegration(), CeleryIntegration()]
)

MiB = 2**20
USER_MAX_FILE_SIZE_BYTES = 10 * MiB
USER_MAX_TOTAL_STORAGE_BYTES = 100 * MiB
USER_MAX_EMAIL_ATTACHMENT_BYTES = USER_MAX_FILE_SIZE_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = USER_MAX_FILE_SIZE_BYTES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINK = os.environ['BASELINK']
API_URL = os.environ['API_URL']
LTI_LAUNCH_URL = API_URL + '/lti/launch/'
LTI_LOGIN_URL = API_URL + '/lti/login/'

STATIC_URL = '/static/'
DEFAULT_PROFILE_PICTURE = '/unknown-profile.png'
# NOTE: Public media directory (not used as such, should probably be renamed.)
MEDIA_URL = 'media/'

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']


# Email settings
EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
ANYMAIL = {
    'MAILGUN_API_KEY': os.environ['MAILGUN_API_KEY'],
    'MAILGUN_API_URL': 'https://api.eu.mailgun.net/v3',
    'MAILGUN_SENDER_DOMAIN': os.environ['MAILGUN_SENDER_DOMAIN'],
}
EMAIL_SENDER_DOMAIN = ANYMAIL['MAILGUN_SENDER_DOMAIN']


# LTI settings
LTI_SECRET = os.environ['LTI_SECRET']
LTI_KEY = os.environ['LTI_KEY']
ROLES = OrderedDict({'Teacher': 'instructor', 'TA': 'teachingassistant', 'Student': 'learner'})
LTI_ROLES = OrderedDict({'instructor': 'Teacher', 'teachingassistant': 'TA', 'learner': 'Student'})
LTI_TEST_STUDENT_FULL_NAME = 'Test student'


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
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
TZ_INFO = pytz.timezone(TIME_ZONE)
USE_I18N = True
USE_L10N = True
USE_TZ = False

DEFAULT_LMS_PROFILE_PICTURE = os.environ['DEFAULT_LMS_PROFILE_PICTURE']
