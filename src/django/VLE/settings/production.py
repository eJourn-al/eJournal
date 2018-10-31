"""
Django settings for VLE project.

Generated by 'django-admin startproject' using Django 2.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import json

import VLE.settings.email as email_config
from VLE.settings.base import *

# SECURITY WARNING: KEEP secret
SECRET_KEY = '{{SECRET_KEY}}'

EMAIL_USE_TLS = True
EMAIL_HOST = '{{SMTP_HOST}}'
EMAIL_HOST_USER = '{{SMTP_LOGIN_MAIL}}'
EMAIL_HOST_PASSWORD = '{{SMTP_LOGIN_PASSWORD}}'
EMAIL_PORT = '{{SMTP_PORT}}'

# SECURITY WARNING: KEEP secret
LTI_SECRET = '{{LTI_SECRET}}'
LTI_KEY = '{{LTI_KEY}}'
LTI_ROLE_CONFIG_PATH = BASE_DIR + '/../lti/role_config.json'

with open(LTI_ROLE_CONFIG_PATH) as role_config:
    ROLES = json.load(role_config)
    LTI_ROLES = dict((ROLES[k], k) for k in ROLES)

BASELINK = '{{BASELINK}}'
if BASELINK[-1] == '/':
    BASELINK = BASELINK[:-1]

CORS_ORIGIN_ALLOW_ALL = True

FILE_UPLOAD_PERMISSIONS = 0o644
USER_MAX_FILE_SIZE_BYTES = '{{USER_MAX_FILE_SIZE_BYTES}}'
USER_MAX_TOTAL_STORAGE_BYTES = '{{USER_MAX_TOTAL_STORAGE_BYTES}}'
USER_MAX_EMAIL_ATTACHMENT_BYTES = '{{USER_MAX_EMAIL_ATTACHMENT_BYTES}}'

MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware'] + MIDDLEWARE
ALLOWED_HOSTS = ['*']

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.{{DATABASE_TYPE}}',
        'NAME': '{{DATABASE_NAME}}',
        'USER': '{{DATABASE_USER}}',
        'PASSWORD': '{{DATABASE_PASSWORD}}',
        'HOST': '{{DATABASE_HOST}}',
        'PORT': '{{DATABASE_PORT}}',
    }
}
