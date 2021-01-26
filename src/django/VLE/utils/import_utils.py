"""
Model import helper functionality
"""

from django.core.files.base import ContentFile

from VLE.models import Category, Comment, Entry, Field, FileContext, Grade, JournalImportRequest, Node
from VLE.utils.error_handling import VLEProgrammingError
from VLE.utils.file_handling import copy_and_replace_rt_files


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
        elif source_comment.files.filter(pk=old_fc.pk).exists():
            comment.files.add(new_fc)
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

    files = FileContext.objects.filter(
        content=source_content_pk,
        is_temp=False,
    ).unused_file_field_files('exclude').unused_rich_text_field_files('exclude').select_related(
        'content__entry__node__journal',
        'content__entry__node__journal__assignment',
    )

    for old_fc in files:
        new_fc = FileContext.objects.create(
            file=ContentFile(old_fc.file.file.read(), name=old_fc.file_name),
            file_name=old_fc.file_name,
            author=old_fc.author,
            is_temp=False,
            content=content,
            journal=content.entry.node.journal,
            assignment=content.entry.node.journal.assignment,
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


def import_template(template, assignment, user, archived=None):
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
        field.description = copy_and_replace_rt_files(field.description, user, assignment=assignment)
        field.save()

    return template


def bulk_import_assignment_categories(source_assignment, target_assignment, author):
    """
    Bulk creates categories for the target assignment with the same concrete fields as those found in the source
    assignment.

    Does not link the newly created categories to matching templates

    Returns a zip of ordered: (source, target) categories.
    """
    source_categories = source_assignment.categories.all()

    new_categories = []
    for category in source_categories:
        category.pk = None
        category.assignment = target_assignment
        category.author = author
        new_categories.append(category)
    Category.objects.bulk_create(new_categories)

    # RT Categories require their respective 'category' attribute to be set, which is why we first have to create
    # the new cateogires before we can copy and replace the RT files.
    categories_with_copied_rt_description = []
    for category in target_assignment.categories.all():
        category.description = copy_and_replace_rt_files(category.description, author, category=category)
        categories_with_copied_rt_description.append(category)
    Category.objects.bulk_update(categories_with_copied_rt_description, ['description'])

    # Use the fact that names are unique at the DB level to map between old and new categories
    source_categories = source_assignment.categories.order_by('name')
    target_categories = target_assignment.categories.order_by('name')

    return zip(source_categories, target_categories)


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


def copy_preset_node_attached_files(preset, attached_files, user, assignment):
    """
    Args:
        preset (:model:`VLE.PresetNode`): Newly copied preset node, still requiring a copy of all attached files.
        attached_files (QuerySet of :model:`VLE.FileContext`): Attached files which need to be attached to the preset
        assignment (:model:`VLE.Assignment`): Assignment copy target
    """
    new_fcs = [
        FileContext.objects.create(
            file=ContentFile(old_fc.file.file.read(), name=old_fc.file_name),
            file_name=old_fc.file_name,
            author=user,
            is_temp=False,
            in_rich_text=False,
            assignment=assignment,
            category=None,
            content=None,
            comment=None,
            journal=None,
        )
        for old_fc in attached_files
    ]
    preset.attached_files.set(new_fcs)
