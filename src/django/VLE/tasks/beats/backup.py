from __future__ import absolute_import, unicode_literals

import gzip
import os
import shutil
import time

from celery import shared_task
from sh import pg_dump

from django.conf import settings


@shared_task
def backup_postgres():
    """Backsup the postgres database.
    -h host, -U user, -w no-password (taken from the environment).

    Streaming output to be zipped on the go, keeping memory use minimal.
    """
    output_path = '{}/postgres_backup_{}.gz'.format(settings.BACKUP_DIR, int(time.time()))

    with gzip.open(output_path, 'wb') as f:
        pg_dump(
            '-h',
            os.environ['DATABASE_HOST'],
            '-U',
            os.environ['DATABASE_USER'],
            os.environ['DATABASE_NAME'],
            '-w',
            _env={'PGPASSWORD': os.environ['DATABASE_PASSWORD']},
            _out=f
        )

    return "Backup of postgress db: {} success.".format(os.environ['DATABASE_NAME'])


# TODO Figure out if this creates acceptable memory overhead
@shared_task
def backup_media():
    """Backsup the media folder."""
    output_base_path = '{}/media_backup_{}'.format(settings.BACKUP_DIR, int(time.time()))

    name = shutil.make_archive(output_base_path, 'tar', settings.MEDIA_ROOT)

    return "Backup of media dir: {} success.".format(name)
