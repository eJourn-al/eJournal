"""
teacher_entry.py.

In this file are all the entry api requests.
"""
from rest_framework import viewsets

import VLE.serializers as serialize
import VLE.utils.entry_utils as entry_utils
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Entry, Grade, Journal, Node, TeacherEntry, Template
from VLE.utils import grading
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
        title, show_title_in_timeline, assignment_id, template_id, content_dict, journals = \
            utils.required_params(
                request.data, 'title', 'show_title_in_timeline', 'assignment_id', 'template_id', 'content', 'journals')
        assignment = Assignment.objects.get(pk=assignment_id)

        request.user.check_permission('can_post_teacher_entries', assignment)

        journals = self._check_teacher_entry_content(journals, assignment, is_new=True)

        # Check if the template is available. Preset-only templates are also available for teacher entries.
        if not assignment.format.template_set.filter(archived=False, pk=template_id).exists():
            return response.not_found('Entry template is not available.')

        template = Template.objects.get(pk=template_id)

        entry_utils.check_fields(template, content_dict)
        teacher_entry = TeacherEntry.objects.create(title=title, show_title_in_timeline=show_title_in_timeline,
                                                    assignment=assignment, template=template, author=request.user,
                                                    last_edited_by=request.user)
        entry_utils.create_entry_content(content_dict, teacher_entry, request.user)
        self._create_new_entries(teacher_entry, journals, request.user)

        return response.created({
            'teacher_entry': serialize.TeacherEntrySerializer(teacher_entry).data
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

        teacher_entry = TeacherEntry.objects.get(pk=pk)

        request.user.check_permission('can_post_teacher_entries', teacher_entry.assignment)
        request.user.check_permission('can_grade', teacher_entry.assignment)
        request.user.check_permission('can_publish_grades', teacher_entry.assignment)

        journals = self._check_teacher_entry_content(journals, teacher_entry.assignment, teacher_entry=teacher_entry)
        new_journals, existing_journals = [], []

        entries = Entry.objects.filter(teacher_entry=teacher_entry)
        deleted_entries = entries.exclude(node__journal__pk__in=map(lambda j: j['journal_id'], journals))
        deleted_entry_journal_ids = list(deleted_entries.values_list('node__journal__pk', flat=True))
        existing_journal_ids = list(entries.values_list('node__journal__pk', flat=True))
        deleted_entries.delete()
        for journal_id in deleted_entry_journal_ids:
            # Entry and node must be deleted.
            grading.task_journal_status_to_LMS.delay(journal_id)

        for journal in journals:
            if journal['journal_id'] not in existing_journal_ids:
                # New entry needs to be created for this journal
                new_journals.append(journal)
            elif journal['grade'] is not None:
                # Entry grade may need to be updated.
                existing_journals.append(journal)
        self._create_new_entries(teacher_entry, new_journals, request.user)
        self._update_existing_entries(teacher_entry, existing_journals, request.user)

        return response.success({
            'teacher_entry': serialize.TeacherEntrySerializer(teacher_entry).data
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
        journals = Journal.objects.filter(pk__in=map(lambda j: j['journal_id'], journals_data))
        entries, nodes, grades = [], [], []
        for journal, journal_data in zip(journals, journals_data):
            entries.append(Entry(
                template=teacher_entry.template,
                author=author,
                last_edited_by=teacher_entry.last_edited_by,
                teacher_entry=teacher_entry,
                vle_coupling=Entry.NEEDS_GRADE_PASSBACK,
            ))
        Entry.objects.bulk_create(entries)
        for journal, journal_data, entry in zip(journals, journals_data, entries):
            nodes.append(Node(
                type=Node.ENTRY,
                journal=journal,
                entry=entry,
            ))
            if journal_data['grade'] is not None:
                grades.append(Grade(
                    author=author,
                    grade=journal_data['grade'],
                    published=journal_data['published'],
                    entry=entry,
                ))
        Node.objects.bulk_create(nodes)
        Grade.objects.bulk_create(grades)
        entries = Entry.objects.filter(pk__in=[e.pk for e in entries])
        # Last edited is set on creation, even when specified during initialization.
        entries.update(last_edited=teacher_entry.last_edited)

        # Send new grades back to LMS
        for grade in grades:
            grade.entry.grade = grade
            grade.entry.save()
            grading.task_journal_status_to_LMS.delay(grade.entry.node.journal.pk)

    def _update_existing_entries(self, teacher_entry, journals_data, author):
        """Updates grades of existing entries. Only when grade is actually changed."""
        journals_data_dict = {
            journal['journal_id']: journal
            for journal in journals_data
        }
        grades = []
        for entry in Entry.objects.filter(teacher_entry=teacher_entry, node__journal__in=journals_data_dict.keys()):
            if not entry.grade or \
               entry.grade.grade != journals_data_dict[entry.node.journal.pk]['grade'] or \
               entry.grade.published != journals_data_dict[entry.node.journal.pk]['published']:
                grades.append(Grade(
                    author=author,
                    grade=journals_data_dict[entry.node.journal.pk]['grade'],
                    published=journals_data_dict[entry.node.journal.pk]['published'],
                    entry=entry,
                ))
        Grade.objects.bulk_create(grades)
        # Send new grades back to LMS
        for grade in grades:
            grade.entry.grade = grade
            grade.entry.save()
            grading.task_journal_status_to_LMS.delay(grade.entry.node.journal.pk)

    def _check_teacher_entry_content(self, journals, assignment, is_new=False, teacher_entry=None):
        """Check if all journals that have been selected also have valid content.

        Return a list of valid journals if nothing """
        valid_journals = []
        valid_journal_ids = list(Journal.objects.filter(assignment=assignment).values_list('pk', flat=True))
        for journal in journals:
            journal_id, grade, published = utils.optional_typed_params(
                journal, (int, 'journal_id'), (float, 'grade'), (bool, 'published'))
            if journal_id not in valid_journal_ids:
                raise VLEBadRequest('Journal does not exist in assignment')
            if grade and grade < 0:
                raise VLEBadRequest('All grades must be either empty or at least 0.')
            if not is_new and not grade and Entry.objects.filter(
                    grade__isnull=False, node__journal__pk=journal_id, teacher_entry=teacher_entry).exists():
                raise VLEBadRequest('It is not possible to remove a grade from an entry.')

            valid_journals.append({
                'journal_id': journal_id,
                'grade': grade,
                'published': published or False
            })
        return valid_journals
