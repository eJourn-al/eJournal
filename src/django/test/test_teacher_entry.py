import test.factory as factory
from copy import deepcopy
from datetime import date, timedelta
from test.utils import api
from unittest import mock

from django.db import transaction
from django.test import TestCase

from VLE.models import Comment, Entry, Field, FileContext, Grade, Node, TeacherEntry
from VLE.serializers import EntrySerializer
from VLE.utils.error_handling import VLEPermissionError


class TeacherEntryAPITest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment(format__templates=[])
        self.journal1 = factory.Journal(assignment=self.assignment)
        self.student1 = self.journal1.authors.first().user
        self.journal2 = factory.Journal(assignment=self.assignment)
        self.teacher = self.assignment.author
        self.format = self.assignment.format
        self.template = factory.TextTemplate(format=self.format)

        self.valid_create_params = {
            'title': 'Teacher initated entry title',
            'show_title_in_timeline': True,
            'assignment_id': self.assignment.id,
            'template_id': self.template.id,
            'journal_ids': [self.journal1.id],
            'content': {},
            'grades': {
                self.journal1.id: 1,
            },
            'publish_grade': {
                self.journal1.id: True,
            },
        }
        fields = self.template.field_set.all()
        self.valid_create_params['content'] = {str(field.id): 'test data' for field in fields}

    def test_create_graded_teacher_entry(self):
        graded_create_params = deepcopy(self.valid_create_params)

        for publish_state in [False, True]:
            graded_create_params['publish_grade']: {
                self.journal1.id: publish_state,
            }

            # Check valid entry creation
            resp = api.create(self, 'teacher_entries', params=graded_create_params,
                              user=self.teacher)['teacher_entry']
            resp2 = api.create(self, 'teacher_entries', params=graded_create_params,
                               user=self.teacher)['teacher_entry']

            assert resp['id'] != resp2['id'], 'Multiple creations should lead to different ids'

            journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1)
            assert journal1_entry.exists(), 'Teacher entry should be added to student journal'

            journal1_entry = journal1_entry.first()
            assert journal1_entry.id != resp['id'], 'Student entry should not be same as teacher entry'
            assert journal1_entry.author == self.teacher, \
                'Teacher should be author of teacher entry in student journal'

            # Graded entry cannot be edited, like usual.
            self.assertRaises(
                VLEPermissionError,
                self.student1.check_can_edit,
                journal1_entry,
            )

            # Users without permission are not allowed to create (graded) teacher entries.
            api.create(self, 'teacher_entries', params=graded_create_params, user=self.student1, status=403)

    def test_create_teacher_entry_params_factory(self):
        assignment = factory.Assignment(author__preferences__can_post_teacher_entries=True)
        factory.Journal(assignment=assignment)
        teacher = assignment.author
        params = factory.TeacherEntryCreationParams(assignment=assignment)

        api.create(self, 'teacher_entries', params=params, user=teacher)

    def test_create_invalid_teacher_entry(self):
        invalid_template_params = deepcopy(self.valid_create_params)
        invalid_template_params['template_id'] = 0

        # Teacher entry cannot be added to journal which is not part of assignment.
        api.create(self, 'teacher_entries', params=invalid_template_params, user=self.teacher, status=404)

        invalid_journal_params = deepcopy(self.valid_create_params)
        invalid_journal_params['journal_ids'].append(factory.Journal().id)

        # Teacher entry cannot be added to journal which is not part of assignment.
        api.create(self, 'teacher_entries', params=invalid_journal_params, user=self.teacher, status=404)

        negative_grade_params = deepcopy(self.valid_create_params)
        negative_grade_params['grades'][self.journal2.id] = -1

        # Teacher entry cannot have grade lower than 0.
        api.create(self, 'teacher_entries', params=negative_grade_params, user=self.teacher, status=400)

    def test_catch_exceptions_teacher_entry(self):
        # File establishment errors should be caught and not leave dangling teacher entries.
        file_template_params = deepcopy(self.valid_create_params)
        file_template = factory.FilesTemplate(format=self.format)
        file_template_params['template_id'] = file_template.id
        fields = list(file_template.field_set.all())
        fields[0].required = True
        fields[0].save()
        file_template_params['content'] = {str(fields[0].id): None}

        teacher_entry_count = TeacherEntry.objects.count()

        # Content is None.
        api.create(self, 'teacher_entries', params=file_template_params, user=self.teacher, status=400)

        assert teacher_entry_count == TeacherEntry.objects.count(), 'Failed request should not leave teacher entry'

        file_template_params['content'] = {str(fields[0].id): {'id': 0}}

        # File content ID is invalid.
        api.create(self, 'teacher_entries', params=file_template_params, user=self.teacher, status=404)

        assert teacher_entry_count == TeacherEntry.objects.count(), 'Failed request should not leave teacher entry'

        with mock.patch('VLE.utils.file_handling.get_files_from_rich_text', side_effect=Exception()):
            # Errors in rich text content should not leave dangling teacher entries.
            rich_text_params = deepcopy(self.valid_create_params)
            rich_text_template = factory.MentorgesprekTemplate(format=self.format)
            rich_text_params['template_id'] = rich_text_template.id
            fields = rich_text_template.field_set.all()
            rich_text_params['content'] = {str(field.id): 'test data' for field in fields}

            with transaction.atomic():
                with self.assertRaises(Exception):
                    api.create(self, 'teacher_entries', params=rich_text_params, user=self.teacher)

            assert teacher_entry_count == TeacherEntry.objects.count(), 'Failed request should not leave teacher entry'

    def test_create_ungraded_teacher_entry(self):
        ungraded_create_params = deepcopy(self.valid_create_params)
        ungraded_create_params['grades'] = {}
        ungraded_create_params['publish_grade'] = {}

        resp = api.create(self, 'teacher_entries', params=ungraded_create_params, user=self.teacher)['teacher_entry']

        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal__authors__user=self.student1)
        assert journal1_entry.exists(), \
            'Teacher entry should be added to student journal'

        # Student should be able to edit ungraded teacher entry.
        self.student1.check_can_edit(journal1_entry.first())

    def test_update_teacher_entry(self):
        resp = api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)['teacher_entry']
        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).first()
        node = Node.objects.filter(entry=journal1_entry).first()

        valid_update_params = {
            'pk': resp['id'],
            'journal_ids': [self.journal1.id, self.journal2.id],
            'grades': {
                self.journal1.id: 2,
            },
            'publish_grade': {},
        }

        # Upgrade grade for journal1, add entry to journal2 without grade.
        api.update(self, 'teacher_entries', params=valid_update_params, user=self.teacher)

        assert Entry.objects.filter(teacher_entry__pk=resp['id'], grade=None, node__journal=self.journal2).exists(), \
            'Journal 2 has been added to list of journal ids: entry should be added.'

        node_count_before = Node.objects.count()
        entry_count_before = Entry.objects.count()
        grade_count_before = Grade.objects.count()

        # Perform same update: nothing should change.
        api.update(self, 'teacher_entries', params=valid_update_params, user=self.teacher)

        assert node_count_before == Node.objects.count(), 'No new nodes created'
        assert entry_count_before == Entry.objects.count(), 'No new entries created'
        assert grade_count_before == Grade.objects.count(), 'No new grades created'

        # Remove journal 1 from journal ids.
        valid_update_params['journal_ids'].pop(0)

        api.update(self, 'teacher_entries', params=valid_update_params, user=self.teacher)

        assert not Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).exists(), \
            'Journal 1 has been removed from the list of journal ids: entry should be deleted.'
        assert not Node.objects.filter(pk=node.id).exists(), \
            'Journal 1 has been removed from the list of journal ids: node should be deleted.'

        # Users without permission are not allowed to update teacher entries.
        api.update(self, 'teacher_entries', params=valid_update_params, user=self.student1, status=403)

        invalid_journal_params = deepcopy(valid_update_params)
        invalid_journal_params['journal_ids'].append(factory.Journal().id)

        # Teacher entry cannot be added to journal which is not part of assignment.
        api.update(self, 'teacher_entries', params=invalid_journal_params, user=self.teacher, status=404)

        negative_grade_params = deepcopy(valid_update_params)
        negative_grade_params['grades'][self.journal2.id] = -1

        # Teacher entry cannot have grade lower than 0.
        api.update(self, 'teacher_entries', params=negative_grade_params, user=self.teacher, status=400)

        remove_grade_params = deepcopy(valid_update_params)
        remove_grade_params['grades'] = {self.journal2.id: 5}
        api.update(self, 'teacher_entries', params=remove_grade_params, user=self.teacher)
        remove_grade_params['grades'] = {}

        # It shall not be possible to completely remove a grade for an existing entry.
        api.update(self, 'teacher_entries', params=remove_grade_params, user=self.teacher, status=400)

    def test_teacher_entry_outside_assignment_unlock_lock(self):
        # Check if teacher can already create teacher entry when assignment is not yet unlocked
        self.assignment.unlock_date = date.today() + timedelta(1)
        self.assignment.save()
        api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)

        # Check if teacher can still create teacher entry when assignment is locked
        self.assignment.unlock_date = None
        self.assignment.lock_date = date.today() - timedelta(1)
        self.assignment.save()
        api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)

    def test_required_for_teacher_entry(self):
        # Check if required field is required also for teacher entries.
        factory.Field(template=self.template, required=True)
        api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher, status=400)

    def test_preset_only_template_teacher_entry(self):
        # Check if preset only templates are available for teacher entries.
        preset_only_template = factory.TextTemplate(format=self.format, preset_only=True)
        preset_only_create_params = deepcopy(self.valid_create_params)
        preset_only_create_params['template_id'] = preset_only_template.id
        fields = Field.objects.filter(template=preset_only_template).all()
        preset_only_create_params['content'] = {field.id: 'test data' for field in fields}

        api.create(self, 'teacher_entries', params=preset_only_create_params, user=self.teacher)

    def test_valid_content_teacher_entry(self):
        with mock.patch('VLE.utils.entry_utils.check_fields') as check_fields_mock:
            # Ensure teacher entries are validated the same as regular entries.
            api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)
            check_fields_mock.assert_called_with(self.template, self.valid_create_params['content'])

    def test_teacher_entry_title(self):
        create_params = deepcopy(self.valid_create_params)

        create_params['show_title_in_timeline'] = True
        resp = api.create(self, 'teacher_entries', params=create_params, user=self.teacher)['teacher_entry']
        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).first()
        serializer = EntrySerializer(journal1_entry)

        assert serializer.data['title'] == 'Teacher initated entry title', 'Title should be shown in timeline'

        create_params['show_title_in_timeline'] = False
        resp = api.create(self, 'teacher_entries', params=create_params, user=self.teacher)['teacher_entry']
        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).first()
        serializer = EntrySerializer(journal1_entry)

        assert serializer.data['title'] != 'Teacher initated entry title', 'Title should not be shown in timeline'

    def test_get_teacher_entries(self):
        resp = api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)['teacher_entry']

        # Students cannot retrieve teacher entries for an assignment.
        api.get(self, 'assignments/teacher_entries', params={'pk': self.assignment.pk}, user=self.student1, status=403)

        # Teacher can retrieve all grades and content of teacher entry.
        teacher_entries = api.get(self, 'assignments/teacher_entries', params={'pk': self.assignment.pk},
                                  user=self.teacher)['teacher_entries']
        teacher_entry = next(teacher_entry for teacher_entry in teacher_entries if teacher_entry['id'] == resp['id'])

        assert 'title' in teacher_entry and teacher_entry['title'] == 'Teacher initated entry title', \
            'Teacher entry title should be serialized'
        assert 'template' in teacher_entry and teacher_entry['template']['id'] == self.template.id, \
            'Teacher entry template should be serialized'
        assert 'content' in teacher_entry and isinstance(teacher_entry['content'], dict), \
            'Teacher entry content dictionary should be serialized'
        assert 'journal_ids' in teacher_entry and self.journal1.id in teacher_entry['journal_ids'], \
            'Journals which a teacher entry is part of should be serialized'
        assert 'grades' in teacher_entry and teacher_entry['grades'][str(self.journal1.id)] == 1, \
            'Entry grades for all entries that belong to a teacher entry should be serialized'
        assert 'grade_published' in teacher_entry and teacher_entry['grade_published'][str(self.journal1.id)], \
            'Published state for all entry grades for entries that belong to a teacher entry should be serialized'

    def test_delete_teacher_entry(self):
        journal3 = factory.Journal(assignment=self.assignment, entries__n=0)
        journal4 = factory.Journal(assignment=self.assignment, entries__n=0)

        create_params = deepcopy(self.valid_create_params)
        create_params['journal_ids'] = [journal3.id, journal4.id]
        create_params['grades'] = {
            journal4.id: 1,
        }
        create_params['publish_grade'] = {
            journal4.id: True,
        }

        node_count_before = Node.objects.count()
        entry_count_before = Entry.objects.count()

        resp = api.create(self, 'teacher_entries', params=create_params, user=self.teacher)['teacher_entry']
        entries = Entry.objects.filter(teacher_entry__pk=resp['id']).all()
        nodes = Node.objects.filter(entry__in=entries).all()

        assert Entry.objects.count() == entry_count_before + 3 and len(entries) == 2, \
            'Two journal entries have been added for the teacher entry, teacher entry itself is also an Entry but ' \
            'without journal'
        assert Node.objects.count() == node_count_before + 2 and len(nodes) == 2, \
            'Two nodes have been added for the teacher entry'

        api.delete(self, 'teacher_entries', params={'pk': resp['id']}, user=self.teacher)

        for entry in entries:
            assert not Entry.objects.filter(pk=entry.id).exists(), \
                'Journal entries corresponding to teacher entry should have been removed'
        for node in nodes:
            assert not Node.objects.filter(pk=node.id).exists(), \
                'Journal nodes corresponding to teacher entry should have been removed'

        assert not TeacherEntry.objects.filter(pk=resp['id']).exists()

        assert Entry.objects.count() == entry_count_before, 'Deleting teacher entry restores original entry count'
        assert Node.objects.count() == node_count_before, 'Deleting teacher entry restores original node count'

        resp = api.create(self, 'teacher_entries', params=create_params, user=self.teacher)['teacher_entry']
        # Student (who does not have permission can_post_teacher_entries) cannot delete teacher entries.
        api.delete(self, 'teacher_entries', params={'pk': resp['id']}, user=journal3.authors.first().user, status=403)
        # They can, however, still delete an ungraded teacher entry in their own journal.
        api.delete(self, 'entries', params={
            'pk': Entry.objects.get(teacher_entry__pk=resp['id'], node__journal=journal3).id
        }, user=journal3.authors.first().user)

    def test_teacher_entry_crash_recovery(self):
        # Setup some earlier DB context
        course = factory.Course(author__preferences__can_post_teacher_entries=True)
        teacher = course.author
        assignment = factory.Assignment(courses=[course], format__templates=[])
        factory.TemplateAllTypes(format=assignment.format)
        for _ in range(3):
            journal = factory.Journal(assignment=assignment)
        entry = Entry.objects.get(node__journal=journal)
        factory.TeacherComment(entry=entry, n_att_files=1, n_rt_files=1, author=teacher, published=True)

        pre_crash_nodes = list(Node.objects.values_list('pk', flat=True))
        pre_crash_entries = list(Entry.objects.values_list('pk', flat=True))
        pre_crash_fcs = list(FileContext.objects.values_list('pk', flat=True))
        pre_crash_comments = list(Comment.objects.values_list('pk', flat=True))

        # QUESTION: This action will generate a RT and FILE field temp FC, how should these temp files be handled?
        data = factory.TeacherEntryCreationParams(assignment=assignment)

        def check_db_state_after_exception(self, raise_exception_for):
            with mock.patch(raise_exception_for, side_effect=Exception()):
                self.assertRaises(
                    Exception, api.create, self, 'teacher_entries', params=data, user=teacher)

            # Check if DB state is unchanged after a crash
            assert list(Node.objects.values_list('pk', flat=True)) == pre_crash_nodes
            assert list(Entry.objects.values_list('pk', flat=True)) == pre_crash_entries
            assert list(FileContext.objects.values_list('pk', flat=True)) == pre_crash_fcs
            assert list(Comment.objects.values_list('pk', flat=True)) == pre_crash_comments

        check_db_state_after_exception(self, 'VLE.views.teacher_entry._copy_new_teacher_entry')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.copy_node')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.copy_entry')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.import_comment')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.import_content')
        check_db_state_after_exception(self, 'VLE.factory.make_content')
        check_db_state_after_exception(self, 'VLE.utils.file_handling.get_files_from_rich_text')
        check_db_state_after_exception(self, 'VLE.utils.file_handling.establish_file')
        check_db_state_after_exception(self, 'VLE.factory.make_grade')
        check_db_state_after_exception(self, 'VLE.utils.grading.task_journal_status_to_LMS')
