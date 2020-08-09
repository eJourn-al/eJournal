'''
Model import helper functionality
'''

from django.core.files.base import ContentFile

from VLE.models import (Assignment, AssignmentParticipation, Content, Course, Entry, Field, FileContext, Journal,
                        JournalImportRequest, Node, PresetNode, Template, Comment)
from VLE.utils.error_handling import VLEProgrammingError


def import_comment(comment, entry):
    '''
    Creates a new comment object attached to the target entry.

    Unpublished comments are not imported.

    The source comment is edited in place, any in memory references will be altered. The source comment in db remains
    untouched.
    '''
    if not comment.published:
        raise VLEProgrammingError('Unpublished comments should not be imported')

    source_comment_pk = comment.pk
    comment.pk = None
    comment.entry = entry
    comment.save()

    source_comment = Comment.objects.get(pk=source_comment_pk)

    for old_fc in FileContext.objects.filter(comment=source_comment, is_temp=False):
        new_fc = FileContext.objects.create(
            file=ContentFile(old_fc.file.file.read(), name=old_fc.file_name),
            file_name=old_fc.file_name,
            author=old_fc.author,
            is_temp=False,
            creation_date=old_fc.creation_date,
            update_date=old_fc.update_date,
            comment=comment,
            journal=old_fc.journal,
            in_rich_text=old_fc.in_rich_text
        )

        if old_fc.in_rich_text:
            comment.text = comment.text.replace(
                old_fc.download_url(access_id=old_fc.access_id), new_fc.download_url(access_id=new_fc.access_id))
        elif source_comment.files.filter(pk=old_fc.pk).exists():
            comment.files.add(new_fc)
        else:
            raise VLEProgrammingError('Unknown file context encountered during comment import.')

    comment.save()

    return comment
