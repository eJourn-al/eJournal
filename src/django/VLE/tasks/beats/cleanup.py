from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

import VLE.models


def remove_temp_files(older_lte=None):
    """Remove temp files older than the REFRESH_TOKEN_LIFETIME"""
    if not older_lte:
        older_lte = timezone.now() - settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

    VLE.models.FileContext.objects.filter(creation_date__lte=older_lte, is_temp=True).delete()


def remove_unused_content_files():
    """Remove overwritten files of RT and FILE context fields"""
    VLE.models.FileContext.objects.unused_file_field_files().delete()
    VLE.models.FileContext.objects.unused_rich_text_field_files().delete()


def remove_unused_comment_files():
    """Removes unused comment files, both no longer attached and no longer referenced in RT"""
    VLE.models.FileContext.objects.filter(
        ~Q(comment__text__contains=F('access_id')),
        comment__isnull=False,
        comment_files__isnull=True,
    ).delete()


def remove_unused_journal_files():
    """Removes unused files associated directly with a journal (cover image)"""
    VLE.models.FileContext.objects.filter(
        ~Q(journal__stored_image__contains=F('access_id')),
        journal__isnull=False,
        comment__isnull=True,
        content__isnull=True,
    ).delete()


def remove_unused_profile_pictures():
    """Removes unused files associated directly with a single user (profile picture)"""
    VLE.models.FileContext.objects.filter(
        ~Q(author__profile_picture__contains=F('access_id')),
        assignment__isnull=True,
        journal__isnull=True,
        comment__isnull=True,
        content__isnull=True,
    ).delete()


def remove_unused_assignment_files():
    """Remove files associated directly with an assignment, e.g. in a field or presetnode description"""
    ass_fcs = VLE.models.FileContext.objects.filter(
        assignment__isnull=False,
        journal__isnull=True,
        comment__isnull=True,
        content__isnull=True,
    )
    fcs_not_in_description = ass_fcs.filter(~Q(assignment__description__contains=F('access_id')))

    for fc in fcs_not_in_description:
        found = VLE.models.Field.objects.filter(
            template__format__assignment=fc.assignment, description__contains=fc.access_id).exists()
        found = found or VLE.models.PresetNode.objects.filter(
            format__assignment=fc.assignment, description__contains=fc.access_id).exists()
        if not found:
            fc.delete()


@shared_task
def remove_unused_files(older_lte=None):
    """Deletes floating user files."""
    remove_temp_files(older_lte=older_lte)
    remove_unused_content_files()
    remove_unused_comment_files()
    remove_unused_journal_files()
    remove_unused_profile_pictures()
    remove_unused_assignment_files()
