"""
Model import helper functionality
"""

from django.core.files.base import ContentFile

from VLE.models import Comment, Entry, Field, FileContext, Grade, JournalImportRequest, Node
from VLE.utils.error_handling import VLEProgrammingError


def _copy_grade_based_on_jir_action(entry, grade, author, action=JournalImportRequest.APPROVED_WITH_GRADES_ZEROED):
    """
    Create a new grade instance with a fresh history. Could be ungraded, zeroed or none based on the action.

    If the Entry's grade was unpublished, it is not copied and set to None.

    Args:
        entry (:model:`VLE.entry`): Entry the copied grade should be attached to.
        author (:model:`VLE.user`): Author of the new grade
        action (str): Choice of (:model:`VLE.JournalImportRequest`).APPROVED_STATES
    """
    if action not in JournalImportRequest.APPROVED_STATES:
        raise VLEProgrammingError('Copy grade request based on unrecognized action.')

    if action == JournalImportRequest.APPROVED_INC_GRADES:
        if grade is None or not grade.published:
            return None
        points = grade.grade
    if action == JournalImportRequest.APPROVED_EXC_GRADES:
        return None
    if action == JournalImportRequest.APPROVED_WITH_GRADES_ZEROED:
        points = 0

    return Grade.objects.create(
        entry=entry,
        grade=points,
        published=True,
        author=author,
    )


def _select_vle_coupling_based_on_jir_action(action, entry):
    """
    Args:
        action (str): Choice of (:model:`VLE.JournalImportRequest`).APPROVED_STATES
        entry (:model:`VLE.entry`): The original entry.
    """
    if action not in JournalImportRequest.APPROVED_STATES:
        raise VLEProgrammingError('Copy grade request based on unrecognized action.')

    if action == JournalImportRequest.APPROVED_INC_GRADES:
        if entry.grade is None:
            return Entry.NEEDS_SUBMISSION
        return Entry.NEEDS_GRADE_PASSBACK
    if action == JournalImportRequest.APPROVED_EXC_GRADES:
        return Entry.NEEDS_SUBMISSION
    if action == JournalImportRequest.APPROVED_WITH_GRADES_ZEROED:
        return Entry.NEEDS_GRADE_PASSBACK


def import_entry(entry, journal, jir=None, grade_author=None,
                 grade_action=JournalImportRequest.APPROVED_WITH_GRADES_ZEROED):
    """
    Creates a new entry object attached to the given journal.

    Any nested content (node, comments, contents, and associated files) are copied.
    Nested templates are copied and added to the journal assignment format as archived (along with any fields).
    A new grade object is created, as the start of a fresh grading history for the entry.

    Args:
        - entry (:model:`VLE.entry`): Entry to copy.
        - journal (:model:`VLE.journal`): Journal which the entry should be copied into.
        - grade_action: Action selection from (:model:`VLE.JournalImportRequest`), determines how the new entry's
          grade should be set.
        - jir (:model:`VLE.JournalImportRequest`): JIR instance triggering the import action.

    Returns:
        The copied entry.
    """
    if jir is None and grade_author is None:
        raise VLEProgrammingError('A grade author needs to be specified either via a JIR or directly.')

    grade_author = grade_author if grade_author else jir.processor
    grade_action = jir.state if jir else grade_action

    copied_node = copy_node(entry.node, journal)
    copied_entry = copy_entry(
        entry,
        node=copied_node,
        vle_coupling=_select_vle_coupling_based_on_jir_action(grade_action, entry),
        jir=jir
    )
    grade = _copy_grade_based_on_jir_action(copied_entry, entry.grade, grade_author, grade_action)
    if grade:
        copied_entry.save()

    for comment in entry.comment_set.filter(published=True):
        import_comment(comment, copied_entry)

    for content in entry.content_set.all():
        import_content(content, copied_entry)

    return copied_entry


def import_comment(comment, entry):
    """
    Creates a new comment object attached to the target entry.

    Unpublished comments are not imported.

    The source comment is edited in place, any in memory references will be altered. The source comment in db remains
    untouched.

    Args:
        comment (:model:`VLE.comment`): Comment to import.
        entry (:model:`VLE.entry`): Entry to attach content to.
    """
    if not comment.published:
        raise VLEProgrammingError('Unpublished comments should not be imported.')

    last_edited = comment.last_edited
    source_comment_pk = comment.pk
    comment.pk = None
    comment.entry = entry
    comment.save()
    comment.last_edited = last_edited
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
        elif source_comment.attached_files.filter(pk=old_fc.pk).exists():
            comment.attached_files.add(new_fc)
        else:
            raise VLEProgrammingError('Unknown file context {} encountered during comment import.'.format(old_fc.pk))

    comment.save()

    return comment


def import_content(content, entry):
    """
    Creates a new content instance attached to the target entry.

    The source content is edited in place, any in memory references will be altered. The source content in db remains
    untouched.

    Args:
        content (:model:`VLE.content`): Content to import.
        entry (:model:`VLE.entry`): Entry to attach content to.
    """
    source_content_pk = content.pk
    content.pk = None
    content.entry = entry
    content.save()

    files = FileContext.objects.filter(content=source_content_pk, is_temp=False)
    for old_fc in files:
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
    if files.exists():
        content.save()

    return content


def import_template(template, assignment, archived=None):
    """
    Copies the given template and adds it to the given assignment's format
    """
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


def copy_entry(old_entry, node=None, grade=None, vle_coupling=None, teacher_entry=None, jir=None):
    """
    Create a copy of an entry instance

    Does not copy the associated template into the journal's assignment format
    """
    last_edited = old_entry.last_edited
    entry = Entry.objects.create(
        node=node,
        template=old_entry.template,
        author=old_entry.author,
        last_edited_by=old_entry.last_edited_by,
        teacher_entry=teacher_entry,
        vle_coupling=vle_coupling if vle_coupling else old_entry.vle_coupling,
        jir=jir
    )

    if node:
        node.entry = entry
        node.save()
    # Last edited is set on creation, even when specified during initialization.
    entry.last_edited = last_edited
    entry.save()

    return entry


def copy_node(node, journal, entry=None):
    """
    Create a copy of a node instance

    Since a node has a one to one relation with an entry, a new entry is expected.

    Args:
        node (:model:`VLE.node`): Node to copy.
        entry (:model:`VLE.entry`): Entry to attach the node to.
        journal (:model:`VLE.journal`): Journal to attach the node to.
    """
    return Node.objects.create(
        type=node.type,
        entry=entry,
        journal=journal,
        preset=node.preset
    )
