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
    elif instance.course is not None:
        return '{}/coursefiles/{}/{}'.format(instance.author.id, instance.course.id, filename)
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


def establish_file(author, identifier, course=None, assignment=None, journal=None, content=None, comment=None,
                   in_rich_text=False):
    """establish files, after this they won't be removed."""
    if str(identifier).isdigit():
        file_context = VLE.models.FileContext.objects.get(pk=identifier)
    else:
        file_context = VLE.models.FileContext.objects.get(access_id=identifier)

    if file_context.author != author:
        raise VLE.utils.error_handling.VLEPermissionError('You are not allowed to update files of other users')
    if not file_context.is_temp:
        raise VLE.utils.error_handling.VLEBadRequest('You are not allowed to update established files')

    if comment:
        journal = comment.entry.node.journal
    if content:
        journal = content.entry.node.journal
    if journal:
        assignment = journal.assignment
    if assignment:
        if not course:
            course = assignment.get_active_course(author)

    file_context.comment = comment
    file_context.content = content
    file_context.journal = journal
    file_context.assignment = assignment
    file_context.course = course
    file_context.is_temp = False
    file_context.in_rich_text = in_rich_text

    # Move the file on filesystem to a permanent location
    initial_path = file_context.file.path
    file_context.file.name = get_file_path(file_context, file_context.file_name)
    new_folder = os.path.join(settings.MEDIA_ROOT, get_file_path(file_context, ''))

    new_path = os.path.join(settings.MEDIA_ROOT, file_context.file.name)

    # Prevent potential name clash on filesystem
    while os.path.exists(str(new_path)):
        p = pathlib.Path(new_path)
        random_file_name = '{}-{}{}'.format(p.stem, uuid.uuid4(), p.suffix)
        file_context.file.name = str(pathlib.Path(file_context.file.name).with_name(random_file_name))
        new_path = p.with_name(random_file_name)

    os.makedirs(new_folder, exist_ok=True)
    os.rename(initial_path, str(new_path))

    file_context.save()

    if content and not in_rich_text:
        content.data = str(file_context.pk)
        content.save()

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


def establish_rich_text(author, rich_text, course=None, assignment=None, journal=None, comment=None, content=None):
    for file in get_temp_files_from_rich_text(rich_text):
        establish_file(author, file.access_id, course, assignment, journal, content, comment, in_rich_text=True)


def remove_unused_user_files(user):
    """Deletes floating user files."""
    # Remove temp files
    VLE.models.FileContext.objects.filter(author=user, is_temp=True).delete()

    # Remove overwritten files
    for file in VLE.models.FileContext.objects.filter(author=user, content__isnull=False):
        if file.content.field.type == VLE.models.Field.FILE:  # Check if file is replaced
            if str(file.pk) != file.content.data:
                file.delete()
        # Remove rich_text files
        elif file.content.field.type == VLE.models.Field.RICH_TEXT:  # Check if url is not in field anymore
            if not file.content.data or str(file.access_id) not in file.content.data:
                file.delete()
    for file in VLE.models.FileContext.objects.filter(author=user, comment__isnull=False):
        # Check if url is not in comment anymore
        if not file.comment_files.filter(pk=file.comment.pk).exists() and \
           (not file.comment.text or str(file.access_id) not in file.comment.text):
            file.delete()
    for file in VLE.models.FileContext.objects.filter(
       author=user, journal__isnull=False, comment__isnull=True, content__isnull=True):
        # Check if url is not the journal image anymore
        if not file.journal.image or str(file.access_id) not in file.journal.image:
            file.delete()
    for file in VLE.models.FileContext.objects.filter(
       author=user, course__isnull=True, assignment__isnull=True, journal__isnull=True):
        # Check if url is not the profile picture
        if not file.author.profile_picture or str(file.access_id) not in file.author.profile_picture:
            file.delete()
    for file in VLE.models.FileContext.objects.filter(author=user, assignment__isnull=False, journal__isnull=True):
        # Check if url is not in assignment anymore
        if not file.assignment.description or str(file.access_id) not in file.assignment.description:
            found = False
            for field in VLE.models.Field.objects.filter(template__format__assignment=file.assignment):
                if field.description and str(file.access_id) in field.description:  # Nor is it in a field
                    found = True
                    break
            if not found:
                for node in VLE.models.PresetNode.objects.filter(format__assignment=file.assignment):
                    if node.description and str(file.access_id) in node.description:  # Nor is it in a field
                        found = True
                        break
            if not found:  # Only then delete the file
                file.delete()
