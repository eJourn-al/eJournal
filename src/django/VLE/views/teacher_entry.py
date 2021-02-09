"""
teacher_entry.py.

In this file are all the entry api requests.
"""
from django.db.models import Max
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Entry, EntryCategoryLink, Grade, Journal, Node, TeacherEntry, Template
from VLE.serializers import TeacherEntrySerializer
from VLE.utils import entry_utils, grading
from VLE.utils.error_handling import VLEBadRequest


def _update_categories_of_existing_entries(entries, author, new_category_ids, existing_category_ids):
    """
    Keeps the categories of all existing entries synced with those set on the teacher entry.

    Does not touch the category links of entries which already belong to the desired categories

    Args:
        entries (:model:`VLE.entry`): List of entries associated with a teacher entry which should be updated.
        author (:model:`VLE.author`): Author of the teacher entry edit.
        new_category_ids ([int]): List of category ids which should now belong to the entry.
        existing_category_ids ([int]): List of category ids which currently belong to the entry.
    """
    EntryCategoryLink.objects.filter(entry__in=entries).exclude(category_id__in=new_category_ids).delete()
    new_entry_category_links = []
    for new_category_id in new_category_ids:
        new_entry_category_links += [
            EntryCategoryLink(entry=entry, category_id=new_category_id, author=author)
            for entry in entries.exclude(categories__pk=new_category_id)
        ]
    EntryCategoryLink.objects.bulk_create(new_entry_category_links)


class TeacherEntryView(viewsets.ViewSet):
    """Entry view.

    This class creates the following api paths:
    POST /teacher_entries/ -- create a new entry
    PATCH /teacher_entries/<pk> -- partially update a teacher entry
    DELETE /teacher_entries/<pk> -- delete a teacher entry and its occurences in journals
    """

    def create(self, request):
        """Create a new teacher entry.

        Deletes remaining temporary user files if successful.

        Arguments:
        request -- the request that was sent with
            title -- title of the teacher entry
            show_title_in_timeline -- whether to include the title in the timeline (show to students as well)
            assignment_id -- the assignment id to which the entry belongs
            template_id -- the template id to create the entry with
            content -- the list of {tag, data} tuples to bind data to a template field.
            journal_ids -- the journal ids of all journals to which the entry should be added
            grades -- dict of grades with journal id as keys
            publish_grade -- dict of grade publish state with journal id as keys
            category_ids -- list of category ids that should be linked to the entries
        """
        title, show_title_in_timeline, assignment_id, template_id, content_dict, journals = utils.required_params(
            request.data,
            'title',
            'show_title_in_timeline',
            'assignment_id',
            'template_id',
            'content',
            'journals',
        )
        category_ids, = utils.required_typed_params(request.data, (int, 'category_ids'))

        assignment = Assignment.objects.get(pk=assignment_id)
        request.user.check_permission('can_post_teacher_entries', assignment)
        journals = self._check_teacher_entry_content(journals, assignment, is_new=True)

        # Check if the template is available. Preset-only templates are also available for teacher entries.
        if not assignment.format.template_set.filter(archived=False, pk=template_id).exists():
            return response.not_found('Entry template is not available.')
        template = Template.objects.get(pk=template_id)

        entry_utils.check_fields(template, content_dict)
        category_ids = Entry.validate_categories(category_ids, assignment)

        teacher_entry = TeacherEntry.objects.create(
            title=title,
            show_title_in_timeline=show_title_in_timeline,
            assignment=assignment,
            template=template,
            author=request.user,
            last_edited_by=request.user
        )
        teacher_entry.set_categories(category_ids, request.user)

        entry_utils.create_entry_content(content_dict, teacher_entry, request.user)
        self._create_new_entries(teacher_entry, journals, category_ids, request.user)

        return response.created({
            'teacher_entry': TeacherEntrySerializer(
                TeacherEntrySerializer.setup_eager_loading(
                    TeacherEntry.objects.filter(pk=teacher_entry.pk)
                ).get(),
                context={'user': request.user},
            ).data
        })

    def partial_update(self, request, pk, *args, **kwargs):
        """Update an existing teacher entry.

        Arguments:
        pk -- the teacher entry to update
        request -- the request that was sent with
            journal_ids -- the journal ids of all journals which the entry should be part of
            grades -- dict of grades with journal id as keys
            publish_grade -- dict of grade publish state with journal id as keys

        All arguments should include the old state (e.g. omitting a journal id from the list will remove the entry from
        that journal).
        """
        journals, = utils.required_params(request.data, 'journals')
        title, category_ids = utils.required_typed_params(request.data, (str, 'title'), (int, 'category_ids'))

        teacher_entry = TeacherEntry.objects.select_related('assignment').get(pk=pk)

        request.user.check_permission('can_post_teacher_entries', teacher_entry.assignment)
        request.user.check_permission('can_grade', teacher_entry.assignment)
        request.user.check_permission('can_publish_grades', teacher_entry.assignment)

        if title is None or len(title) == 0:
            return response.bad_request('Title cannot be empty.')

        category_ids = Entry.validate_categories(category_ids, teacher_entry.assignment)
        existing_category_ids = set(teacher_entry.categories.values_list('pk', flat=True))

        journals = self._check_teacher_entry_content(journals, teacher_entry.assignment, teacher_entry=teacher_entry)

        entries = Entry.objects.filter(teacher_entry=teacher_entry)
        deleted_entries = entries.exclude(node__journal__pk__in=map(lambda j: j['journal_id'], journals))
        deleted_entry_journal_ids = list(deleted_entries.values_list('node__journal__pk', flat=True))
        existing_journal_ids = list(entries.values_list('node__journal__pk', flat=True))
        deleted_entries.delete()

        grading.task_bulk_send_journal_status_to_LMS.delay(deleted_entry_journal_ids)

        new_journals, existing_journals = [], []
        for journal in journals:
            # New entry needs to be created for this journal
            if journal['journal_id'] not in existing_journal_ids:
                new_journals.append(journal)
            # Entry grade may need to be updated.
            elif journal['grade'] is not None:
                existing_journals.append(journal)

        self._create_new_entries(teacher_entry, new_journals, category_ids, request.user)
        self._update_existing_entries(
            teacher_entry=teacher_entry,
            journals_data=existing_journals,
            new_category_ids=category_ids,
            existing_category_ids=existing_category_ids,
            author=request.user,
        )

        if teacher_entry.title != title:
            teacher_entry.title = title
            teacher_entry.save()
        if category_ids != existing_category_ids:
            teacher_entry.set_categories(category_ids, request.user)

        return response.success({
            'teacher_entry': TeacherEntrySerializer(
                TeacherEntrySerializer.setup_eager_loading(
                    TeacherEntry.objects.filter(pk=teacher_entry.pk)
                ).get()
            ).data
        })

    def destroy(self, request, *args, **kwargs):
        """Delete a teacher entry and all instances of it.

        Arguments:
        pk -- the teacher entry to delete
        """
        pk, = utils.required_typed_params(kwargs, (int, 'pk'))

        teacher_entry = TeacherEntry.objects.get(pk=pk)
        assignment = teacher_entry.assignment

        request.user.check_permission(
            'can_post_teacher_entries', assignment, 'You are not allowed to post or delete teacher entries.')

        # All nodes, entries, content and files are deleted along with the teacher entry itself.
        teacher_entry.delete()

        return response.success(description='Successfully deleted teacher entry.')

    def _create_new_entries(self, teacher_entry, journals_data, category_ids, author):
        """Copies a teacher entry to journals."""
        journals = Journal.objects.filter(pk__in=map(lambda j: j['journal_id'], journals_data)).order_by('pk')

        entries = [
            Entry(
                template=teacher_entry.template,
                author=author,
                last_edited_by=teacher_entry.last_edited_by,
                teacher_entry=teacher_entry,
                vle_coupling=Entry.NEEDS_GRADE_PASSBACK,
            )
            for _ in range(len(journals))
        ]
        entries = Entry.objects.bulk_create(entries)

        entry_category_links = [
            EntryCategoryLink(entry=entry, category_id=category_id, author=author)
            for category_id in category_ids
            for entry in entries
        ]
        EntryCategoryLink.objects.bulk_create(entry_category_links)

        nodes, grades = [], []
        journals = list(journals)
        for journal, journal_data, entry in zip(journals, journals_data, entries):
            nodes.append(Node(
                type=Node.ENTRY,
                journal=journal,
                entry=entry,
            ))

            if journal_data['grade'] is not None:
                grade = Grade(
                    author=author,
                    grade=journal_data['grade'],
                    published=journal_data['published'],
                    entry=entry,
                )
                grades.append(grade)

        Node.objects.bulk_create(nodes, new_node_notifications=False)
        grades = Grade.objects.bulk_create(grades)

        # Set the grade field of the newly created entries to the newly created grades.
        # Last edited is set on creation, even when specified during initialization.
        entries = list(
            Entry.objects.filter(pk__in=[e.pk for e in entries]).annotate(newest_grade_id=Max('grade_set__id')))
        for entry in entries:
            entry.grade_id = entry.newest_grade_id
            entry.last_edited = teacher_entry.last_edited
        Entry.objects.bulk_update(entries, ['grade', 'last_edited'])

        grading.task_bulk_send_journal_status_to_LMS.delay([journal.pk for journal in journals])

    def _update_existing_entries(self, teacher_entry, journals_data, new_category_ids, existing_category_ids, author):
        """
        Updates grades of existing entries.
        Only provided journals of which the grade actually changed (is not None).
        """
        journals_data_dict = {journal['journal_id']: journal for journal in journals_data}
        journal_pks = list(journals_data_dict.keys())
        entries = Entry.objects.filter(teacher_entry=teacher_entry, node__journal__in=journal_pks) \
            .select_related('grade', 'node__journal')

        grades = []
        for entry in entries:
            if (
                not entry.grade or
                entry.grade.grade != journals_data_dict[entry.node.journal.pk]['grade'] or
                entry.grade.published != journals_data_dict[entry.node.journal.pk]['published']
            ):
                grade = Grade(
                    author=author,
                    grade=journals_data_dict[entry.node.journal.pk]['grade'],
                    published=journals_data_dict[entry.node.journal.pk]['published'],
                    entry=entry,
                )
                grades.append(grade)
        Grade.objects.bulk_create(grades)

        _update_categories_of_existing_entries(entries, author, new_category_ids, existing_category_ids)

        # Set the grade field of the updated entries to the newly created grades.
        entries = list(
            Entry.objects.filter(teacher_entry=teacher_entry, node__journal__in=journal_pks)
            .annotate(newest_grade_id=Max('grade_set__id'))
        )
        for entry in entries:
            entry.grade_id = entry.newest_grade_id
        Entry.objects.bulk_update(entries, ['grade'])

        grading.task_bulk_send_journal_status_to_LMS.delay(journal_pks)

    def _check_teacher_entry_content(self, journals, assignment, is_new=False, teacher_entry=None):
        """Check if all journals that have been selected also have valid content.

        Return a list of valid journals if nothing """
        valid_journals = []
        valid_journal_ids = set(Journal.objects.filter(assignment=assignment).values_list('pk', flat=True))
        for journal in journals:
            journal_id, grade, published = utils.optional_typed_params(
                journal, (int, 'journal_id'), (float, 'grade'), (bool, 'published'))
            if journal_id not in valid_journal_ids:
                raise VLEBadRequest('Journal does not exist in assignment.')
            if grade is not None and grade < 0:
                raise VLEBadRequest('All grades must be either empty or at least 0.')
            if not is_new and grade is None and Entry.objects.filter(
                    grade__isnull=False, node__journal__pk=journal_id, teacher_entry=teacher_entry).exists():
                raise VLEBadRequest('It is not possible to remove a grade from an entry.')

            valid_journals.append({
                'journal_id': journal_id,
                'grade': grade,
                'published': published or False
            })
        valid_journals.sort(key=lambda journal_data: journal_data['journal_id'])
        return valid_journals
