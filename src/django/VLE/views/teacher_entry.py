"""
teacher_entry.py.

In this file are all the entry api requests.
"""
from django.db.models import Max
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Entry, Grade, Journal, Node, TeacherEntry, Template
from VLE.serializers import TeacherEntrySerializer
from VLE.utils import entry_utils, grading
from VLE.utils.error_handling import VLEBadRequest


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
        """
        title, show_title_in_timeline, assignment_id, template_id, content_dict, journals = utils.required_params(
            request.data,
            'title',
            'show_title_in_timeline',
            'assignment_id',
            'template_id',
            'content',
            'journals'
        )

        assignment = Assignment.objects.get(pk=assignment_id)
        request.user.check_permission('can_post_teacher_entries', assignment)
        journals = self._check_teacher_entry_content(journals, assignment, is_new=True)

        # Check if the template is available. Preset-only templates are also available for teacher entries.
        if not assignment.format.template_set.filter(archived=False, pk=template_id).exists():
            return response.not_found('Entry template is not available.')
        template = Template.objects.get(pk=template_id)

        entry_utils.check_fields(template, content_dict)

        teacher_entry = TeacherEntry.objects.create(
            title=title,
            show_title_in_timeline=show_title_in_timeline,
            assignment=assignment,
            template=template,
            author=request.user,
            last_edited_by=request.user
        )
        entry_utils.create_entry_content(content_dict, teacher_entry, request.user)
        self._create_new_entries(teacher_entry, journals, request.user)

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
        title, = utils.required_typed_params(request.data, (str, 'title'))

        teacher_entry = TeacherEntry.objects.get(pk=pk)

        request.user.check_permission('can_post_teacher_entries', teacher_entry.assignment)
        request.user.check_permission('can_grade', teacher_entry.assignment)
        request.user.check_permission('can_publish_grades', teacher_entry.assignment)

        if title is None or len(title) == 0:
            return response.bad_request('Title cannot be empty.')

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

        self._create_new_entries(teacher_entry, new_journals, request.user)
        self._update_existing_entries(teacher_entry, existing_journals, request.user)

        if teacher_entry.title != title:
            teacher_entry.title = title
            teacher_entry.save()

        return response.success({
            'teacher_entry': TeacherEntrySerializer(
                TeacherEntrySerializer.setup_eager_loading(
                    TeacherEntry.objects.filter(pk=teacher_entry.pk)
                )[0]
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

    def _create_new_entries(self, teacher_entry, journals_data, author):
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

                if journal_data['published']:
                    journal.grade += journal_data['grade']  # Set the journal grade for bulk update later
                else:
                    journal.unpublished += 1  # Set the journal unpublished count for bulk update later
            else:
                journal.needs_marking += 1  # Set the journal needs_marking count for bulk update later

        Node.objects.bulk_create(nodes)
        grades = Grade.objects.bulk_create(grades)
        # Update the journals @computed fields
        Journal.objects.bulk_update(journals, ['grade', 'unpublished', 'needs_marking'])

        # Set the grade field of the newly created entries to the newly created grades.
        # Last edited is set on creation, even when specified during initialization.
        entries = list(
            Entry.objects.filter(pk__in=[e.pk for e in entries]).annotate(newest_grade_id=Max('grade_set__id')))
        for entry in entries:
            entry.grade_id = entry.newest_grade_id
            entry.last_edited = teacher_entry.last_edited
        Entry.objects.bulk_update(entries, ['grade', 'last_edited'])

        grading.task_bulk_send_journal_status_to_LMS.delay([journal.pk for journal in journals])

    def _update_existing_entries(self, teacher_entry, journals_data, author):
        """
        Updates grades of existing entries.
        Only provided journals of which the grade actually changed (is not None).
        """
        journals_data_dict = {journal['journal_id']: journal for journal in journals_data}
        journal_pks = list(journals_data_dict.keys())
        entries = Entry.objects.filter(teacher_entry=teacher_entry, node__journal__in=journal_pks) \
            .select_related('grade', 'node__journal')
        journal_objs = [entry.node.journal for entry in entries]
        grades = []

        for entry in entries:
            if (
                not entry.grade or
                entry.grade.grade != journals_data_dict[entry.node.journal.pk]['grade'] or
                entry.grade.published != journals_data_dict[entry.node.journal.pk]['published']
            ):
                journal = entry.node.journal

                grade = Grade(
                    author=author,
                    grade=journals_data_dict[entry.node.journal.pk]['grade'],
                    published=journals_data_dict[entry.node.journal.pk]['published'],
                    entry=entry,
                )
                grades.append(grade)

                # Set the journal's @computed fields 'grade' ,'unpublished', and 'needs_marking' for bulk update later.
                if entry.grade:
                    if entry.grade.published:
                        if journals_data_dict[entry.node.journal.pk]['published']:
                            journal.grade = journal.grade - entry.grade.grade + journals_data_dict[journal.pk]['grade']
                        else:
                            journal.grade -= entry.grade.grade
                            journal.unpublished += 1
                    else:
                        if journals_data_dict[entry.node.journal.pk]['published']:
                            journal.unpublished -= 1
                            journal.grade += journals_data_dict[journal.pk]["grade"]
                else:
                    journal.needs_marking -= 1
                    if journals_data_dict[entry.node.journal.pk]['published']:
                        journal.grade += journals_data_dict[entry.node.journal.pk]['grade']
                    else:
                        journal.unpublished += 1

        Grade.objects.bulk_create(grades)
        # Update the earlier in memory set journal computed fields
        Journal.objects.bulk_update(journal_objs, ['grade', 'unpublished', 'needs_marking'])

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
