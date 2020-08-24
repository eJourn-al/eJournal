'''
Model import helper functionality
'''

import os

from django.core.files.base import ContentFile

from VLE.models import (Assignment, AssignmentParticipation, Comment, Content, Course, Entry, Field, FileContext,
                        Journal, JournalImportRequest, Node, PresetNode, Template)
from VLE.utils.error_handling import VLEProgrammingError


def import_entry(entry, journal, copy_grade):
    '''
    Creates a new entry object attached to the given journal.

    Any nested content (node, comments, contents, and associated files) are copied.
    Nested templates are copied and added to the journal assignment format as archived (along with any fields).
    A new grade object is created, as the start of a fresh grading history for the entry.

    Args:
        entry (:model:`VLE.entry`): Entry to copy.
        journal (:model:`VLE.journal`): Journal which the entry should be copied into.
        copy_grade (bool): Flag indicating whether the entry grade should be copied, if not grade is set to None.

    Returns:
        The copied entry.
    '''
    # TODO JIR: A new grade object is created, as the start of a fresh grading history for the entry.

    # TODO JIR: Create differentiating labels indicating the entry was imported (update docstring once decided)

    copied_entry = copy_entry(
        entry,
        grade=None,
        # QUESTION JIR: Double check if this correct, needs submission not often used
        vle_coupling=Entry.NEEDS_GRADE_PASSBACK if copy_grade else Entry.NEEDS_SUBMISSION
    )

    # Copied entry niet kunnen editen
    # Als geen grade, moet de docent dan normaal "Need grading" krijgen

    # Alle cijfers op 0 zetten
    # Alle cijfers op None zetten (docent kan andere cijfers geven)
    # ALle cijfers overnemen, sommige cijfers kunnen nog steeds None (als dat zo in source). Voor deze entries,
    # mogen deze een nieuw cijfer krijgen? geedit worden?
    # TODO JIR: Create grade object with grade 0, if not copy grade
    # use old factory to immediately set the entry fk factory.make_grade

    # TODO JIR: If a link to presetnode exists can this be maintained? node.preset.format.assignment will diff
    copy_node(entry.node, copied_entry, journal)

    for comment in Comment.objects.filter(entry=entry, published=True):
        import_comment(comment, copied_entry)

    for content in Content.objects.filter(entry=entry):
        import_content(content, copied_entry)

    return copied_entry


def import_comment(comment, entry):
    '''
    Creates a new comment object attached to the target entry.

    Unpublished comments are not imported.

    The source comment is edited in place, any in memory references will be altered. The source comment in db remains
    untouched.

    Args:
        comment (:model:`VLE.comment`): Comment to import.
        entry (:model:`VLE.entry`): Entry to attach content to.
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
            comment=comment,
            journal=comment.entry.node.journal,
            in_rich_text=old_fc.in_rich_text
        )

        if old_fc.in_rich_text:
            comment.text = comment.text.replace(
                old_fc.download_url(access_id=old_fc.access_id), new_fc.download_url(access_id=new_fc.access_id))
        elif source_comment.files.filter(pk=old_fc.pk).exists():
            comment.files.add(new_fc)
        else:
            raise VLEProgrammingError('Unknown file context {} encountered during comment import.'.format(old_fc.pk))

    comment.save()

    return comment


def import_content(content, entry):
    '''
    Creates a new content instance attached to the target entry.

    The source content is edited in place, any in memory references will be altered. The source content in db remains
    untouched.

    Args:
        content (:model:`VLE.content`): Content to import.
        entry (:model:`VLE.entry`): Entry to attach content to.
    '''
    source_content_pk = content.pk
    content.pk = None
    content.entry = entry
    content.save()

    for old_fc in FileContext.objects.filter(content=source_content_pk, is_temp=False):
        new_fc = FileContext.objects.create(
            file=ContentFile(old_fc.file.file.read(), name=old_fc.file_name),
            file_name=old_fc.file_name,
            author=old_fc.author,
            is_temp=False,
            content=content,
            journal=content.entry.node.journal,
            in_rich_text=old_fc.in_rich_text
        )

        if old_fc.in_rich_text:
            content.data = content.data.replace(
                old_fc.download_url(access_id=old_fc.access_id), new_fc.download_url(access_id=new_fc.access_id))
        else:
            if content.data != str(old_fc.pk):
                raise VLEProgrammingError(
                    'Invalid content {} fc {} combo encountered during content import'.format(content.pk, old_fc.pk))
            content.data = str(new_fc.pk)

    content.save()

    return content


def import_template(template, assignment, archived=None):
    '''
    Copies the given template and adds it to the given assignment's format
    '''
    source_template_id = template.pk
    template.pk = None
    template.format = assignment.format
    template.archived = template.archived if archived is None else archived
    template.save()

    for field in Field.objects.filter(template=source_template_id):
        field.pk = None
        field.template = template
        field.save()

    return template


def copy_entry(entry, grade=None, vle_coupling=None):
    '''
    Create a copy of an entry instance
    '''
    return Entry.objects.create(
        template=entry.template,
        grade=grade,
        author=entry.author,
        last_edited_by=entry.last_edited_by,
        vle_coupling=vle_coupling if vle_coupling else entry.vle_coupling
    )


def copy_node(node, entry, journal):
    '''
    Create a copy of a node instance

    Since a node has a one to one relation with an entry, a new entry is expected.

    Args:
        node (:model:`VLE.node`): Node to copy.
        entry (:model:`VLE.entry`): Entry to attach the node to.
        journal (:model:`VLE.journal`): Journal to attach the node to.
    '''
    return Node.objects.create(
        type=node.type,
        entry=entry,
        journal=journal,
        preset=node.preset
    )
