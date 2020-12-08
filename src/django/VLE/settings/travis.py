"""
Django settings for VLE project.

Generated by 'django-admin startproject' using Django 2.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""
import os

from VLE.settings.base import *

ENVIRONMENT = 'CI_CD'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEDIA_ROOT = os.path.join(BASE_DIR, MEDIA_URL)
STATIC_ROOT = os.path.join(BASE_DIR, STATIC_URL)
BACKUP_DIR = os.path.join(BASE_DIR, 'backup/')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
LOG_DIR = os.path.join(BASE_DIR, 'logs/')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

CORS_ORIGIN_ALLOW_ALL = True
CSP_DEFAULT_SRC = ("'self'", "'unsafe-inline'")

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware'
] + MIDDLEWARE
ALLOWED_HOSTS = ['*']

# If this is True, all tasks will be executed locally by blocking until the task returns.
# TODO implement a testing environment, which does use background workers moving closer to production.
CELERY_TASK_ALWAYS_EAGER = True if 'CI_CD' in os.environ else False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_USER'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': os.environ['DATABASE_HOST'],
        'PORT': os.environ['DATABASE_PORT'],
        'TEST': {
            'NAME': 'test_ejournal'
        }
    }
}

DEBUG = True
