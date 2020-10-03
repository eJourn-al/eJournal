"""
File handling related utilites.
"""
import json
import os
import pathlib
import re
import shutil
import uuid

from django.conf import settings

import VLE.models
import VLE.utils.error_handling


def get_path(instance, filename):
    """Upload user files into their respective directories. Following MEDIA_ROOT/uID/aID/<file>

    Uploaded files not part of an entry yet, and are treated as temporary untill linked to an entry."""
    return str(instance.author.id) + '/' + str(instance.assignment.id) + '/' + filename


def get_file_path(instance, filename):
    """Upload user files into their respective directories. Following MEDIA_ROOT/uID/<category>/?[id/]<filename>"""
    if instance.is_temp:
        return('{}/tempfiles/{}'.format(instance.author.id, filename))
    elif instance.journal is not None:
        return '{}/journalfiles/{}/{}'.format(instance.author.id, instance.journal.id, filename)
    elif instance.assignment is not None:
        return '{}/assignmentfiles/{}/{}'.format(instance.author.id, instance.assignment.id, filename)
    else:
        return '{}/userfiles/{}'.format(instance.author.id, filename)


def get_feedback_file_path(instance, filename):
    """Upload user feedback file into their respective directory. Following MEDIA_ROOT/uID/feedback/<file>

    An uploaded feedback file is temporary, and removed when the feedback mail is processed by celery."""
    return '{}/feedback/{}'.format(instance.id, filename)


def compress_all_user_data(user, extra_data_dict=None, archive_extension='zip'):
    """Compresses all user files found in MEDIA_ROOT/uid into a single archiveself.

    If an extra data dictionary is provided, this is json dumped and included in the archive as
    information.json.
    The archive is stored in MEDIA_ROOT/{username}_data_archive.{archive_extension}.
    Please note that this archive is overwritten if it already exists."""
    user_file_dir_path = os.path.join(settings.MEDIA_ROOT, str(user.id))
    archive_name = user.username + '_data_archive'
    archive_ouput_base_name = os.path.join(settings.MEDIA_ROOT, archive_name)
    archive_ouput_path = archive_ouput_base_name + '.' + archive_extension

    if extra_data_dict:
        extra_data_dump_name = 'information.json'
        extra_data_dump_path = os.path.join(user_file_dir_path, extra_data_dump_name)
        os.makedirs(os.path.dirname(extra_data_dump_path), exist_ok=True)
        with open(extra_data_dump_path, 'w') as file:
            file.write(json.dumps(extra_data_dict))

    shutil.make_archive(archive_ouput_base_name, archive_extension, user_file_dir_path)

    return archive_ouput_path, '{}.{}'.format(archive_name, archive_extension)


def _set_file_context(fc, assignment=None, journal=None, content=None, comment=None, in_rich_text=False):
    if comment:
        journal = comment.entry.node.journal
    if content:
        if type(content.entry).__name__ == 'TeacherEntry':
            assignment = content.entry.assignment
        else:
            journal = content.entry.node.journal
    if journal:
        assignment = journal.assignment

    fc.comment = comment
    fc.content = content
    fc.journal = journal
    fc.assignment = assignment
    fc.is_temp = False
    fc.in_rich_text = in_rich_text

    if content and not in_rich_text:
        content.data = str(fc.pk)
        content.save()


def _move_newly_established_file_context_to_permanent_location(fc):
    """
    Once a file is no longer temporary and its context is set, it can be moved to a permanent location according
    `get_file_path`.
    """
    initial_path = fc.file.path
    fc.file.name = get_file_path(fc, fc.file_name)
    new_folder = os.path.join(settings.MEDIA_ROOT, get_file_path(fc, ''))

    new_path = os.path.join(settings.MEDIA_ROOT, fc.file.name)

    # Prevent potential name clash on filesystem
    while os.path.exists(str(new_path)):
        p = pathlib.Path(new_path)
        random_file_name = '{}-{}{}'.format(p.stem, uuid.uuid4(), p.suffix)
        fc.file.name = str(pathlib.Path(fc.file.name).with_name(random_file_name))
        new_path = p.with_name(random_file_name)

    os.makedirs(new_folder, exist_ok=True)
    os.rename(initial_path, str(new_path))


def establish_file(author, identifier, assignment=None, journal=None, content=None, comment=None, in_rich_text=False):
    """Sets the context of a temporary file, and moves it to a permanent location."""
    if str(identifier).isdigit():
        file_context = VLE.models.FileContext.objects.get(pk=identifier)
    else:
        file_context = VLE.models.FileContext.objects.get(access_id=identifier)

    if file_context.author != author:
        raise VLE.utils.error_handling.VLEPermissionError('You are not allowed to update files of other users')
    if not file_context.is_temp:
        raise VLE.utils.error_handling.VLEBadRequest('You are not allowed to update established files')

    _set_file_context(file_context, assignment, journal, content, comment, in_rich_text)
    _move_newly_established_file_context_to_permanent_location(file_context)

    file_context.save()

    return file_context


def get_access_ids_from_rich_text(rich_text):
    re_access_ids = re.compile(r'\/files\/[0-9]+\?access_id=([a-zA-Z0-9]+)')
    return re.findall(re_access_ids, rich_text)


def get_files_from_rich_text(rich_text):
    if rich_text is None or len(rich_text) < 128:
        return VLE.models.FileContext.objects.none()
    return VLE.models.FileContext.objects.filter(access_id__in=get_access_ids_from_rich_text(rich_text))


def get_temp_files_from_rich_text(rich_text):
    return get_files_from_rich_text(rich_text).filter(is_temp=True)


def establish_rich_text(author, rich_text, assignment=None, journal=None, comment=None, content=None):
    for file in get_temp_files_from_rich_text(rich_text):
        establish_file(author, file.access_id, assignment, journal, content, comment, in_rich_text=True)
