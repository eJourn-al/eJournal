
import test.factory as factory
from copy import deepcopy
from datetime import datetime, timedelta
from test.utils import api
from test.utils.generic_utils import _model_instance_to_dict, equal_models, zip_equal
from test.utils.performance import QueryContext
from unittest import mock

from django.db import transaction
from django.test import TestCase
from django.test.utils import override_settings

from VLE.models import Comment, Entry, EntryCategoryLink, Field, FileContext, Grade, Journal, Node, TeacherEntry
from VLE.serializers import EntrySerializer, TeacherEntrySerializer
from VLE.utils.error_handling import VLEPermissionError


class TeacherEntryAPITest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment(format__templates=[])
        self.category = factory.Category(assignment=self.assignment)
        self.category2 = factory.Category(assignment=self.assignment)
        self.journal1 = factory.Journal(assignment=self.assignment)
        self.student1 = self.journal1.authors.first().user
        self.journal2 = factory.Journal(assignment=self.assignment)
        self.teacher = self.assignment.author
        self.format = self.assignment.format
        self.template = factory.TextTemplate(format=self.format, preset_only=False)

        self.valid_create_params = factory.TeacherEntryCreationParams(
            assignment=self.assignment, template=self.template, journals=[self.journal1])

    def test_create_teacher_entry_params_factory(self):
        assignment = self.assignment
        journal = self.journal1
        teacher = assignment.author
        params = factory.TeacherEntryCreationParams(assignment=assignment)

        te_id = api.create(self, 'teacher_entries', params=params, user=teacher)['teacher_entry']['id']
        te = TeacherEntry.objects.get(pk=te_id)
        entry = Entry.objects.filter(teacher_entry_id=te_id, node__journal=journal).latest('pk')
        assert entry.grade.grade == 1, 'If no grade is specific as kwarg, default to 1'
        assert entry.grade.published, 'If published is not specific as kwarg, default to false'
        assert not te.categories.exists(), 'If no categories are specific as kwarg, default to None'
        assert not entry.categories.exists(), 'If no categories are specific as kwarg, default to None'

        params = factory.TeacherEntryCreationParams(
            assignment=assignment, grade=0, published=False, categories=[self.category])
        te_id = api.create(self, 'teacher_entries', params=params, user=teacher)['teacher_entry']['id']
        te = TeacherEntry.objects.get(pk=te_id)
        entry = Entry.objects.filter(teacher_entry_id=te_id, node__journal=journal).latest('pk')
        assert entry.grade.grade == 0, 'Kwarg grade is used'
        assert not entry.grade.published, 'Kwarg published is used'
        assert Entry.objects.filter(teacher_entry=te).first().categories.filter(pk=self.category.pk).exists(), \
            'Category kwarg is used for the generated entries'
        assert te.categories.filter(pk=self.category.pk).exists(), 'Category kwarg is used for the TE itself'

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_create_graded_teacher_entry(self):
        graded_create_params = deepcopy(self.valid_create_params)

        for publish_state in [False, True]:
            for journal in graded_create_params['journals']:
                journal['published'] = publish_state
            self.journal1 = Journal.objects.get(pk=self.journal1.pk)
            before_grade = self.journal1.grade

            # Check valid entry creation
            resp = api.create(self, 'teacher_entries', params=graded_create_params,
                              user=self.teacher)['teacher_entry']
            resp2 = api.create(self, 'teacher_entries', params=graded_create_params,
                               user=self.teacher)['teacher_entry']

            assert resp['id'] != resp2['id'], 'Multiple creations should lead to different ids'

            journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1)
            journal1_entry2 = Entry.objects.filter(teacher_entry__pk=resp2['id'], node__journal=self.journal1)
            assert journal1_entry.exists(), 'Teacher entry should be added to student journal'
            assert journal1_entry2.exists(), 'Teacher entry should be added to student journal'
            journal1_entry = journal1_entry.first()
            journal1_entry2 = journal1_entry2.first()
            self.journal1 = Journal.objects.get(pk=self.journal1.pk)
            if publish_state:
                assert before_grade + journal1_entry.grade.grade + journal1_entry2.grade.grade == \
                    self.journal1.grade
            else:
                assert before_grade == self.journal1.grade

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

    def test_create_invalid_teacher_entry(self):
        invalid_template_params = deepcopy(self.valid_create_params)
        invalid_template_params['template_id'] = 0

        # Teacher entry cannot be added to journal which is not part of assignment.
        api.create(self, 'teacher_entries', params=invalid_template_params, user=self.teacher, status=404)

        invalid_journal_params = deepcopy(self.valid_create_params)
        invalid_journal_params['journals'].append({'journal_id': factory.Journal().id})

        # Teacher entry cannot be added to journal which is not part of assignment.
        api.create(self, 'teacher_entries', params=invalid_journal_params, user=self.teacher, status=400)

        negative_grade_params = deepcopy(self.valid_create_params)
        negative_grade_params['journals'][-1]['grade'] = -1

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

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_create_ungraded_teacher_entry(self):
        template_all = factory.TemplateAllTypes(format=self.format, preset_only=False)
        ungraded_create_params = factory.TeacherEntryCreationParams(
            assignment=self.assignment, template=template_all, grade=None)
        resp = api.create(self, 'teacher_entries', params=ungraded_create_params, user=self.teacher)['teacher_entry']

        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal__authors__user=self.student1)
        assert journal1_entry.exists(), \
            'Teacher entry should be added to student journal'
        assert not journal1_entry.first().content_set.exists()

        # Student should be able to edit ungraded teacher entry.
        self.student1.check_can_edit(journal1_entry.first())

        params = {
            'pk': journal1_entry.first().pk,
            'content': ungraded_create_params['content'].copy()
        }
        api.update(self, 'entries', params=params.copy(), user=self.student1)
        assert journal1_entry.first().content_set.exists()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_update_teacher_entry(self):
        resp = api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)['teacher_entry']
        updated_entry_journal1 = Entry.objects.filter(
            teacher_entry__pk=resp['id'], node__journal=self.journal1).latest('pk')
        node = Node.objects.filter(entry=updated_entry_journal1).first()

        valid_update_params = {
            'pk': resp['id'],
            'title': resp['title'],
            'category_ids': [],
            'journals': [{
                'journal_id': self.journal1.id,
                'grade': 2
            }, {
                'journal_id': self.journal2.id
            }]
        }

        no_title = deepcopy(self.valid_create_params)
        no_title['pk'] = resp['id']
        no_title.pop('title')
        api.update(self, 'teacher_entries', params=no_title, user=self.teacher, status=400)
        no_title['title'] = ""
        api.update(self, 'teacher_entries', params=no_title, user=self.teacher, status=400)
        no_title['title'] = None
        api.update(self, 'teacher_entries', params=no_title, user=self.teacher, status=400)

        no_title['title'] = 0
        update_resp = api.update(self, 'teacher_entries', params=no_title, user=self.teacher, status=200)
        assert update_resp['teacher_entry']['title'] == '0', 'Title is succesfully updated with a falsey value'

        # Update grade for journal1, create entry to journal2 without grade.
        pre_update_grade_entry_journal1 = updated_entry_journal1.grade
        api.update(self, 'teacher_entries', params=valid_update_params, user=self.teacher)
        updated_entry_journal1.refresh_from_db()
        updated_entry_grade = updated_entry_journal1.grade_set.latest('pk')

        assert pre_update_grade_entry_journal1 != updated_entry_grade, 'A new grade is created for the updated entry'
        assert updated_entry_journal1.grade == updated_entry_grade, \
            'The new grade is correctly set in the entry field "grade"'
        assert updated_entry_grade.grade == 2, 'The grade is of the correct number of points'

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
        valid_update_params['journals'].pop(0)
        api.update(self, 'teacher_entries', params=valid_update_params, user=self.teacher)

        assert not Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).exists(), \
            'Journal 1 has been removed from the list of journal ids: entry should be deleted.'
        assert not Node.objects.filter(pk=node.id).exists(), \
            'Journal 1 has been removed from the list of journal ids: node should be deleted.'

        # Users without permission are not allowed to update teacher entries.
        api.update(self, 'teacher_entries', params=valid_update_params, user=self.student1, status=403)

        invalid_journal_params = deepcopy(valid_update_params)
        invalid_journal_params['journals'].append({
            'journal_id': factory.Journal().id
        })

        # Teacher entry cannot be added to journal which is not part of assignment.
        api.update(self, 'teacher_entries', params=invalid_journal_params, user=self.teacher, status=400)

        negative_grade_params = deepcopy(valid_update_params)
        negative_grade_params['journals'][-1]['grade'] = -1

        # Teacher entry cannot have grade lower than 0.
        api.update(self, 'teacher_entries', params=negative_grade_params, user=self.teacher, status=400)

        remove_grade_params = deepcopy(valid_update_params)
        remove_grade_params['journals'][-1]['grade'] = 2
        api.update(self, 'teacher_entries', params=remove_grade_params, user=self.teacher)
        remove_grade_params['journals'][-1]['grade'] = None

        # It shall not be possible to completely remove a grade for an existing entry.
        api.update(self, 'teacher_entries', params=remove_grade_params, user=self.teacher, status=400)

    def test_teacher_entry_categories(self):
        valid_create_params = factory.TeacherEntryCreationParams(
            assignment=self.assignment, template=self.template, journals=[self.journal1], categories=[self.category])

        resp = api.create(self, 'teacher_entries', params=valid_create_params, user=self.teacher)['teacher_entry']
        with mock.patch('VLE.models.Entry.validate_categories') as validate_categories_mock:
            api.create(self, 'teacher_entries', params=valid_create_params, user=self.teacher)
            validate_categories_mock.assert_called_with(valid_create_params['category_ids'], self.assignment)
        te = TeacherEntry.objects.get(pk=resp['id'])
        entry = Entry.objects.get(teacher_entry_id=te.pk, node__journal=self.journal1)

        assert set(te.categories.values_list('pk', flat=True)) == set(valid_create_params['category_ids'])
        assert set(entry.categories.values_list('pk', flat=True)) == set(valid_create_params['category_ids'])

        valid_update_params = deepcopy(valid_create_params)
        valid_update_params['pk'] = resp['id']

        remove_categories = deepcopy(valid_update_params)
        remove_categories['category_ids'] = []
        assert te.categories.exists()
        assert entry.categories.exists()
        api.update(self, 'teacher_entries', params=remove_categories, user=self.teacher)
        assert not te.categories.exists(), 'Categories are removed from the teacher entry itself'
        assert not entry.categories.exists(), 'Categories are removed from the entry generated by the teacher entry'

        add_categories = deepcopy(valid_update_params)
        add_categories['category_ids'] = [self.category.pk, self.category2.pk]
        api.update(self, 'teacher_entries', params=add_categories, user=self.teacher)
        # Teacher entries are correctly added (including setting the author)
        assert EntryCategoryLink.objects.filter(category=self.category, entry=te, author=self.teacher).exists()
        assert EntryCategoryLink.objects.filter(category=self.category2, entry=te, author=self.teacher).exists()
        assert EntryCategoryLink.objects.filter(category=self.category, entry=entry, author=self.teacher).exists()
        assert EntryCategoryLink.objects.filter(category=self.category2, entry=entry, author=self.teacher).exists()

        # Updating the categories of a TE should sync the categories of all associated entries.
        two_categories = deepcopy(valid_update_params)
        two_categories['category_ids'] = [self.category.pk, self.category2.pk]

        # Remove category from an entry create by the teacher entry (manual edit by teacher)
        EntryCategoryLink.objects.filter(category=self.category, entry=entry, author=self.teacher).delete()
        pre_category2_link = EntryCategoryLink.objects.get(category=self.category2, entry=entry)
        api.update(self, 'teacher_entries', params=two_categories, user=self.teacher)
        assert EntryCategoryLink.objects.filter(category=self.category, entry=entry, author=self.teacher).exists(), \
            'The manual category edit is corrected by saving the teacher entry'
        post_category2_link = EntryCategoryLink.objects.get(category=self.category2, entry=entry)
        assert pre_category2_link.creation_date == post_category2_link.creation_date, 'Existing links are untouched'
        assert pre_category2_link.update_date == post_category2_link.update_date, 'Existing links are untouched'

        # Teacher removes `category` from the teacher entry itself
        category3 = factory.Category(assignment=self.assignment)
        entry.add_category(category=category3, author=self.teacher)
        api.update(self, 'teacher_entries', params=two_categories, user=self.teacher)
        assert not EntryCategoryLink.objects.filter(category=category3, entry=entry).exists(), \
            'The manual category edit is corrected by saving the teacher entry.'

        # Update also validates the provided category ids
        with mock.patch('VLE.models.Entry.validate_categories') as validate_categories_mock:
            api.update(self, 'teacher_entries', params=two_categories, user=self.teacher)
            validate_categories_mock.assert_called_with(two_categories['category_ids'], self.assignment)

    def test_teacher_entry_outside_assignment_unlock_lock(self):
        # Check if teacher can already create teacher entry when assignment is not yet unlocked
        self.assignment.unlock_date = datetime.today() + timedelta(1)
        self.assignment.save()
        api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)

        # Check if teacher can still create teacher entry when assignment is locked
        self.assignment.unlock_date = None
        self.assignment.due_date = datetime.today() - timedelta(1)
        self.assignment.lock_date = datetime.today() - timedelta(1)
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
            assert check_fields_mock.called

    def test_teacher_entry_title(self):
        create_params = deepcopy(self.valid_create_params)

        create_params['show_title_in_timeline'] = True
        resp = api.create(self, 'teacher_entries', params=create_params, user=self.teacher)['teacher_entry']
        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).first()
        serializer = EntrySerializer(journal1_entry)

        assert serializer.data['title'] == create_params['title'], 'Title should be shown in timeline'

        create_params['show_title_in_timeline'] = False
        resp = api.create(self, 'teacher_entries', params=create_params, user=self.teacher)['teacher_entry']
        journal1_entry = Entry.objects.filter(teacher_entry__pk=resp['id'], node__journal=self.journal1).first()
        serializer = EntrySerializer(journal1_entry)

        assert serializer.data['title'] != create_params['title'], 'Title should not be shown in timeline'

        for title in ['', None]:
            params = deepcopy(self.valid_create_params)
            params['title'] = title
            api.create(self, 'teacher_entries', params=params, user=self.teacher, status=400)

        params = deepcopy(self.valid_create_params)
        falsey_but_string_title = '0'
        params['title'] = falsey_but_string_title
        resp = api.create(self, 'teacher_entries', params=params, user=self.teacher)['teacher_entry']
        assert resp['title'] == falsey_but_string_title, 'Falsey title value is no issue'

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_get_teacher_entries(self):
        resp = api.create(self, 'teacher_entries', params=self.valid_create_params, user=self.teacher)['teacher_entry']
        te = TeacherEntry.objects.get(pk=resp['id'])

        # Students cannot retrieve teacher entries for an assignment.
        api.get(self, 'assignments/teacher_entries', params={'pk': self.assignment.pk}, user=self.student1, status=403)

        # Teacher can retrieve all grades and content of teacher entry.
        teacher_entries = api.get(self, 'assignments/teacher_entries', params={'pk': self.assignment.pk},
                                  user=self.teacher)['teacher_entries']
        teacher_entry = next(teacher_entry for teacher_entry in teacher_entries if teacher_entry['id'] == resp['id'])
        assert 'title' in teacher_entry and teacher_entry['title'] == te.title, \
            'Teacher entry title should be serialized'
        assert 'template' in teacher_entry and teacher_entry['template']['id'] == self.template.id, \
            'Teacher entry template should be serialized'
        assert 'content' in teacher_entry and isinstance(teacher_entry['content'], dict), \
            'Teacher entry content dictionary should be serialized'
        assert 'journals' in teacher_entry and \
            self.journal1.id in map(lambda j: j['journal_id'], teacher_entry['journals']), \
            'Journals which a teacher entry is part of should be serialized'
        assert 1 in map(lambda j: j['grade'], teacher_entry['journals']), \
            'Entry grades for all entries that belong to a teacher entry should be serialized'
        assert any(map(lambda j: j['published'], teacher_entry['journals'])), \
            'Published state for all entry grades for entries that belong to a teacher entry should be serialized'

    def test_delete_teacher_entry(self):
        journal3 = factory.Journal(assignment=self.assignment, entries__n=0)
        journal4 = factory.Journal(assignment=self.assignment, entries__n=0)

        create_params = deepcopy(self.valid_create_params)
        create_params['journals'] = [{
            'journal_id': journal3.id
        }, {
            'journal_id': journal4.id,
            'grade': 1,
            'published': True
        }]

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

    def test_teacher_entry_serializer(self):
        assignment = factory.Assignment()
        factory.Journal(assignment=assignment, entries__n=0)
        teacher = assignment.author
        params = factory.TeacherEntryCreationParams(assignment=assignment, grade=1, published=True)
        te_id = api.create(self, 'teacher_entries', params=params, user=teacher)['teacher_entry']['id']

        with QueryContext() as context_pre:
            TeacherEntrySerializer(
                TeacherEntrySerializer.setup_eager_loading(TeacherEntry.objects.filter(pk=te_id)).get()
            ).data

        factory.Journal(assignment=assignment, entries__n=0)
        params = factory.TeacherEntryCreationParams(assignment=assignment, grade=1, published=True)
        te_id = api.create(self, 'teacher_entries', params=params, user=teacher)['teacher_entry']['id']

        with QueryContext() as context_post:
            TeacherEntrySerializer(
                TeacherEntrySerializer.setup_eager_loading(TeacherEntry.objects.filter(pk=te_id)).get()
            ).data
        assert len(context_pre) == len(context_post) and len(context_pre) <= 8

    def test_teacher_entry_crash_recovery(self):
        # Setup some earlier DB context
        course = factory.Course(author__preferences__can_post_teacher_entries=True)
        teacher = course.author
        assignment = factory.Assignment(courses=[course], format__templates=[])
        factory.TemplateAllTypes(format=assignment.format)
        for _ in range(3):
            journal = factory.Journal(assignment=assignment)
        entry = Entry.objects.get(node__journal=journal)
        factory.Grade(entry=entry, author=teacher)
        factory.TeacherComment(entry=entry, n_att_files=1, n_rt_files=1, author=teacher, published=True)

        def all_to_dict(model):
            return [_model_instance_to_dict(i) for i in model.objects.all()]

        pre_crash_nodes = all_to_dict(Node)
        pre_crash_entries = all_to_dict(Entry)
        pre_crash_grades = all_to_dict(Grade)
        pre_crash_comments = all_to_dict(Comment)
        pre_crash_fcs = list(FileContext.objects.values_list('pk', flat=True))

        data = factory.TeacherEntryCreationParams(assignment=assignment)
        temp_files = list(FileContext.objects.filter(author=teacher, is_temp=True).values_list('pk', flat=True))

        def check_db_state_after_exception(self, raise_exception_for):
            with mock.patch(raise_exception_for, side_effect=Exception()):
                self.assertRaises(
                    Exception, api.create, self, 'teacher_entries', params=data, user=teacher)

            # Check if DB state is unchanged after a crash
            assert all([equal_models(pre, post) for pre, post in zip_equal(pre_crash_nodes, all_to_dict(Node))])
            assert all([equal_models(pre, post) for pre, post in zip_equal(pre_crash_entries, all_to_dict(Entry))])
            assert all([equal_models(pre, post) for pre, post in zip_equal(pre_crash_grades, all_to_dict(Grade))])
            assert all([equal_models(pre, post) for pre, post in zip_equal(pre_crash_comments, all_to_dict(Comment))])
            assert list(FileContext.objects.exclude(pk__in=temp_files).values_list('pk', flat=True)) == pre_crash_fcs
            assert list(FileContext.objects.filter(author=teacher, is_temp=True).values_list('pk', flat=True)) \
                == temp_files, \
                'Teacher can reuse earlier uploaded temporary files, despite a crash occurring'

        check_db_state_after_exception(self, 'VLE.views.teacher_entry.TeacherEntryView._create_new_entries')
        check_db_state_after_exception(self, 'VLE.views.teacher_entry.TeacherEntryView._update_existing_entries')
        check_db_state_after_exception(self, 'VLE.views.teacher_entry.TeacherEntryView._check_teacher_entry_content')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.copy_node')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.copy_entry')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.import_comment')
        check_db_state_after_exception(self, 'VLE.utils.import_utils.import_content')
        check_db_state_after_exception(self, 'VLE.factory.make_content')
        check_db_state_after_exception(self, 'VLE.utils.file_handling.get_files_from_rich_text')
        check_db_state_after_exception(self, 'VLE.utils.file_handling.establish_file')
        check_db_state_after_exception(self, 'VLE.factory.make_grade')
        check_db_state_after_exception(self, 'VLE.utils.grading.task_journal_status_to_LMS')
