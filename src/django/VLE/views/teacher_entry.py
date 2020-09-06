"""
teacher_entry.py.

In this file are all the entry api requests.
"""
from rest_framework import viewsets

import VLE.factory as factory
import VLE.serializers as serialize
import VLE.utils.entry_utils as entry_utils
import VLE.utils.file_handling as file_handling
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Field, FileContext, Journal, Node, TeacherEntry, Template
from VLE.utils import grading, import_utils


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
        title, show_title_in_timeline, assignment_id, template_id, content_dict, journal_ids, grades, publish_grade \
            = utils.required_params(request.data, 'title', 'show_title_in_timeline', 'assignment_id', 'template_id',
                                    'content', 'journal_ids', 'grades', 'publish_grade')

        assignment = Assignment.objects.get(pk=assignment_id)

        request.user.check_permission('can_post_teacher_entries', assignment)

        # Check if all journals that have been selected to add the teacher entry to belong to the current assignment.
        if Journal.objects.filter(assignment=assignment, pk__in=journal_ids).count() != len(journal_ids):
            return response.not_found('Could not find all selected journals.')

        if grades is not None and any([float(grade) < 0 for grade in grades.values()
                                       if (grade is not None and grade != '')]):
            return response.bad_request('All given grades must be greater than or equal to zero.')

        grades = {int(journal_id): float(grade) for journal_id, grade in grades.items()
                  if (grade is not None and grade != '')}
        publish_grade = {int(journal_id): published for journal_id, published in publish_grade.items()}

        # Check if the template is available. Preset-only templates are also available for teacher entries.
        if not assignment.format.template_set.filter(archived=False, pk=template_id).exists():
            return response.not_found('Entry template is not available.')

        template = Template.objects.get(pk=template_id)

        entry_utils.check_fields(template, content_dict)
        teacher_entry = TeacherEntry.objects.create(title=title, show_title_in_timeline=show_title_in_timeline,
                                                    assignment=assignment, template=template, author=request.user,
                                                    last_edited_by=request.user)

        try:
            files_to_establish = []
            for field_id, content in content_dict.items():
                field = Field.objects.get(pk=field_id)
                if content is not None and field.type == field.FILE:
                    content, = utils.required_typed_params(content, (str, 'id'))

                created_content = factory.make_content(teacher_entry, content, field)

                if field.type == field.FILE:
                    if field.required and not content:
                        raise FileContext.DoesNotExist
                    if content:
                        files_to_establish.append(
                            (FileContext.objects.get(pk=int(content)), created_content))

                # Establish all files in the rich text editor
                if field.type == Field.RICH_TEXT:
                    files_to_establish += [
                        (f, created_content) for f in file_handling.get_files_from_rich_text(content)]

        # If anything fails during creation of the teacher entry, delete the teacher entry
        except Exception as e:
            teacher_entry.delete()

            # If it is a file issue, raise with propper response, else respond with the exception that was raised
            if type(e) == FileContext.DoesNotExist:
                return response.bad_request('One of your files was not correctly uploaded, please try again.')
            else:
                raise e

        for (file, created_content) in files_to_establish:
            file_handling.establish_file(request.user, file.access_id, content=created_content,
                                         in_rich_text=created_content.field.type == Field.RICH_TEXT)

        self._copy_new_teacher_entry(teacher_entry, journal_ids, grades, publish_grade, request.user.pk, is_new=True)

        return response.created({
            'teacher_entry': serialize.TeacherEntrySerializer(teacher_entry).data
        })

    def partial_update(self, request, *args, **kwargs):
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
        journal_ids, grades, publish_grade = utils.required_params(request.data, 'journal_ids', 'grades',
                                                                   'publish_grade')
        teacher_entry_id, = utils.required_typed_params(kwargs, (int, 'pk'))

        teacher_entry = TeacherEntry.objects.get(pk=teacher_entry_id)

        request.user.check_permission('can_post_teacher_entries', teacher_entry.assignment)
        request.user.check_permission('can_grade', teacher_entry.assignment)
        request.user.check_permission('can_publish_grades', teacher_entry.assignment)

        # Check if all journals that have been selected to add the teacher entry to belong to the current assignment.
        if Journal.objects.filter(assignment=teacher_entry.assignment, pk__in=journal_ids).count() != len(journal_ids):
            return response.not_found('Could not find all selected journals.')

        if grades is not None and any([float(grade) < 0 for grade in grades.values()
                                       if (grade is not None and grade != '')]):
            return response.bad_request('All given grades must be greater than or equal to zero.')

        grades = {int(journal_id): float(grade) for journal_id, grade in grades.items()
                  if (grade is not None and grade != '')}
        publish_grade = {int(journal_id): published for journal_id, published in publish_grade.items()}

        if any(journal_id in journal_ids and journal_id not in grades for journal_id in teacher_entry.entry_set.all()
                .exclude(grade=None).values_list('node__journal__pk', flat=True)):
            # Entry used to have a grade, but now does not anymore. This is not possible.
            return response.bad_request('It is not possible to remove a grade from an entry.')

        for existing_entry in teacher_entry.entry_set.all():
            journal_id = existing_entry.node.journal.pk
            if journal_id not in journal_ids:
                # Entry and node must be deleted.
                existing_entry.delete()
                grading.task_journal_status_to_LMS.delay(journal_id)
            elif journal_id in grades and grades[journal_id] is not None:
                # Entry grade may need to be updated.
                if not existing_entry.grade or existing_entry.grade.grade != grades[journal_id] or \
                        existing_entry.grade.published != (journal_id in publish_grade and publish_grade[journal_id]):
                    # Current grade differs from previous grade or published. Need to update.
                    factory.make_grade(existing_entry, request.user.pk, grades[journal_id],
                                       journal_id in publish_grade and publish_grade[journal_id])
                    grading.task_journal_status_to_LMS.delay(journal_id)
            if journal_id in journal_ids:
                # No new entry needs to be created for this journal in the next step.
                journal_ids.remove(journal_id)

        self._copy_new_teacher_entry(teacher_entry, journal_ids, grades, publish_grade, request.user.pk)

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

        request.user.check_permission('can_post_teacher_entries', assignment, 'You are not allowed to post or delete '
                                      'teacher entries.')

        # All nodes, entries, content and files are deleted along with the teacher entry itself.
        teacher_entry.delete()

        return response.success(description='Successfully deleted teacher entry.')

    def _copy_new_teacher_entry(self, teacher_entry, journal_ids, grades, publish_grade, author_id, is_new=False):
        """Copies a teacher entry to journals. Only used for creating new entries, not updating existing ones."""
        for journal_id in journal_ids:
            journal = Journal.objects.get(pk=journal_id)
            node = Node.objects.create(
                type=Node.ENTRY,
                journal=journal
            )
            copied_entry = import_utils.copy_entry(teacher_entry, node, teacher_entry=teacher_entry)

            if journal_id in grades and grades[journal_id] is not None:
                factory.make_grade(copied_entry, author_id, grades[journal_id],
                                   journal_id in publish_grade and publish_grade[journal_id])
            for content in teacher_entry.content_set.all():
                import_utils.import_content(content, copied_entry)

            grading.task_journal_status_to_LMS.delay(journal_id)
