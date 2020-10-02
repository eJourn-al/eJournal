"""
WSGI config for VLE project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import logging
import os
import sys

from django.core.wsgi import get_wsgi_application

# NOTE: When deploying with mod_wsgi see:
# http://docs.celeryproject.org/projects/django-celery/en/v2.5.3/introduction.html#special-note-for-mod-wsgi-users

logging.basicConfig(stream=sys.stderr)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VLE.settings.production")
path = '{{DIR}}'
if path not in sys.path:
    sys.path.append(path)
application = get_wsgi_application()
