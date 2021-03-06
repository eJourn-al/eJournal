import copy
import json
import os
import test.factory as factory
from copy import deepcopy
from datetime import datetime, timedelta
from test.factory.content import kaltura_what_is_ej_embed_code
from test.utils import api
from test.utils.generic_utils import equal_models
from test.utils.performance import QueryContext, assert_num_queries_less_than
from unittest import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from faker import Faker

import VLE.timeline as timeline
import VLE.utils.entry_utils as entry_utils
from VLE.models import (Assignment, Category, Comment, Content, Course, Entry, Field, FileContext, Format, Grade,
                        Journal, JournalImportRequest, Node, Notification, PresetNode, TeacherEntry, Template,
                        TemplateChain, User)
from VLE.serializers import EntrySerializer, FileSerializer, TemplateSerializer
from VLE.utils.error_handling import VLEBadRequest, VLEMissingRequiredField, VLEPermissionError
from VLE.validators import validate_entry_content

faker = Faker()


class EntryAPITest(TestCase):
    def setUp(self):
        self.admin = factory.Admin()
        self.g_assignment = factory.Assignment(group_assignment=True)
        self.group_journal = factory.GroupJournal(assignment=self.g_assignment)
        self.student = self.group_journal.authors.first().user
        self.journal2 = factory.Journal(assignment=self.g_assignment)
        self.student2 = self.journal2.authors.first().user
        self.teacher = self.g_assignment.author
        self.format = self.g_assignment.format
        self.template = factory.TextTemplate(format=self.format)
        factory.TextTemplate(format=self.format)
        factory.TextTemplate(format=self.format)

        self.valid_create_params = {
            'journal_id': self.group_journal.pk,
            'template_id': self.template.pk,
            'content': {}
        }
        fields = Field.objects.filter(template=self.template)
        self.valid_create_params['content'] = {field.id: 'test data' for field in fields}

        self.entry_serializer_base_query_count = (
            1
            + len(EntrySerializer.prefetch_related)
            + len(TemplateSerializer.prefetch_related)
        )

    def test_entry_factory(self):
        course_c = Course.objects.count()
        a_c = Assignment.objects.count()
        j_c = Journal.objects.count()
        format_c = Format.objects.count()
        t_c = Template.objects.count()
        e_c = Entry.objects.count()
        n_c = Node.objects.count()
        field_c = Field.objects.count()
        cont_c = Content.objects.count()
        grade_c = Grade.objects.count()
        template_c = Template.objects.count()
        category_c = Category.objects.count()

        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment, node__journal__entries__n=0, categories=1)
        assignment.refresh_from_db()

        assert template_c + 1 == Template.objects.count(), \
            'Creating an entry for an assignment without templates creates a single template'
        assert Template.objects.last().pk == entry.template.pk, 'The created template is linked to the entry'
        assert assignment.format.template_set.filter(pk=entry.template.pk).exists(), \
            'The created template is also added to the format of the assignment'
        assert course_c + 1 == Course.objects.count(), 'A single course is created'
        assert a_c + 1 == Assignment.objects.count(), 'A single assignment is created'
        assert j_c + 1 == Journal.objects.count(), 'A single journal is created'
        assert format_c + 1 == Format.objects.count(), 'A single format is created'
        assert t_c + 1 == Template.objects.count(), 'A single template is created'
        assert e_c + 1 == Entry.objects.count(), 'A single entry is created'
        assert n_c + 1 == Node.objects.count(), 'A single node is created'
        assert field_c + 1 == Field.objects.count(), 'A single field is created'
        assert cont_c + 1 == Content.objects.count(), 'Content is created for the entry with a single field'
        assert grade_c == Grade.objects.count(), 'No grade instances are created for the entry (default ungraded)'
        assert category_c + 1 == Category.objects.count(), 'A single category is created'

        journal = entry.node.journal
        assert Content.objects.filter(entry=entry).exists(), 'Content is created for the generated entry'
        assert Content.objects.filter(entry__node__journal=journal).exists(), \
            'Content is attached to the journal of the entry'
        assert Node.objects.filter(type=Node.ENTRY, journal__assignment=assignment, entry=entry).count() == 1, \
            'An entry node is correctly attached and of the correct type'
        assert entry.grade is None, 'Entry is ungraded by default'
        assert entry.title is None, 'Entry has no custom title by default'
        assert entry.categories.first().assignment == assignment

        grade = 7
        grade_c = Grade.objects.count()

        category = factory.Category(assignment=assignment)
        entry = factory.UnlimitedEntry(
            node__journal__assignment=assignment,
            node__journal__entries__n=0,
            grade__grade=grade,
            categories=[category],
            title='Custom',
        )
        assert grade_c + 1 == Grade.objects.count(), 'A single grade instance is created for the grade entry'
        assert entry.grade.grade == grade, 'Deep syntax works for entry grade instance'
        assert entry.categories.first() == category, 'Passing categories directly works'
        assert entry.title == 'Custom', 'We can set the title'

        assignment = factory.Assignment()
        template_c = Template.objects.count()
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment, node__journal__entries__n=0)
        assignment.refresh_from_db()

        assert template_c == Template.objects.count(), \
            'Creating an entry in an assignment with templates does not create any extra'
        assert assignment.format.template_set.filter(pk=entry.template.pk).exists(), \
            'The selected template is chosen from the assignment format'

    def test_entry_factory_user_generation(self):
        journal = factory.Journal()

        users_before = list(User.objects.values_list('pk', flat=True))
        factory.UnlimitedEntry(node__journal=journal)
        assert User.objects.exclude(pk__in=users_before).count() == 0, 'No additional user is created'

        users_before = list(User.objects.values_list('pk', flat=True))
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1)
        assert User.objects.exclude(pk__in=users_before).count() == 0, \
            'No additional user is created, the grade author should default to the assignment author'

    def test_create_entry_params_factory(self):
        fcs_before = list(FileContext.objects.values_list('pk', flat=True))

        course = factory.Course()
        assignment = factory.Assignment(courses=[course], format__templates=[])
        template = factory.TemplateAllTypes(format=assignment.format)
        journal = factory.Journal(assignment=assignment)
        student = journal.authors.first().user

        data = factory.UnlimitedEntryCreationParams(journal=journal)
        assert data['journal_id'] == journal.pk
        assert data['template_id'] == template.pk

        new_temp_fcs = FileContext.objects.filter(is_temp=True).exclude(pk__in=fcs_before)
        assert all([fc.author == student for fc in new_temp_fcs]) and new_temp_fcs.exists()

        api.create(self, 'entries', params=data, user=student)

    def test_bulk_update_entry_grade(self):
        entry = factory.UnlimitedEntry(grade__grade=1)
        entry2 = factory.UnlimitedEntry(grade__grade=1)
        grade = Grade(entry=entry, grade=2, published=True, author=entry.author)
        grade2 = Grade(entry=entry2, grade=2, published=True, author=entry.author)
        Grade.objects.bulk_create([grade, grade2])

        assert entry.grade != grade, 'Bulk creation does not trigger save so the relation is not set'

        # Check if the annotations actually fetch the newest grade
        assert Entry.objects \
            .filter(pk=entry.pk) \
            .annotate(newest_grade_id=Max('grade_set__id')) \
            .filter(newest_grade_id=grade.pk) \
            .exists()
        assert Entry.objects \
            .filter(pk=entry2.pk) \
            .annotate(newest_grade_id=Max('grade_set__id')) \
            .filter(newest_grade_id=grade2.pk) \
            .exists()

        entries = list(Entry.objects.filter(pk__in=[entry.pk, entry2.pk])
                       .annotate(newest_grade_id=Max('grade_set__id'))
                       .order_by('pk'))
        for e in entries:
            if e == entry:
                assert e.newest_grade_id == grade.pk
            if e == entry2:
                assert e.newest_grade_id == grade2.pk
            e.grade_id = e.newest_grade_id

        Entry.objects.bulk_update(entries, ['grade_id'])

        entry.refresh_from_db()
        entry2.refresh_from_db()
        assert entry.grade == grade
        assert entry2.grade == grade2

    def test_only_most_recent_published_entry_grade_contributes_to_journal_grade_total(self):
        entry = factory.UnlimitedEntry(grade__grade=1, grade__published=True)
        entry2 = factory.UnlimitedEntry(grade__grade=3, grade__published=True, node__journal=entry.node.journal)
        journal = entry.node.journal
        journal = Journal.objects.get(pk=journal.pk)  # Journal is created before the entry and grade in the factory
        assert journal.grade == entry.grade.grade + entry2.grade.grade

        factory.Grade(entry=entry, grade=2, published=False)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == entry2.grade.grade, 'Journal grade consists only of published grades'

        factory.Grade(entry=entry, grade=5, published=True)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 5 + entry2.grade.grade

    def test_entry_validation(self):
        # An entry cannot be instantiated without a node
        self.assertRaises(ValidationError, factory.UnlimitedEntry, node=None)

        entry = factory.UnlimitedEntry()
        entry.author = factory.Student()
        # The author of an entry should always be part of the entry's journal authors
        self.assertRaises(ValidationError, entry.save)

    def test_entry_grade(self):
        entry = factory.UnlimitedEntry()
        journal = entry.node.journal

        assert entry.grade is None, 'Entry grade is None by default'

        entry = factory.UnlimitedEntry(grade__grade=2, node__journal=journal)
        assert entry.grade.grade == 2, 'Deep syntax works for an entries grade.'
        assert journal.assignment.author.pk == entry.grade.author.pk, \
            'An entry\'s grade author defaults to the entry\'s assignment\'s teacher'

    def test_preset_entry_factory(self):
        course_c = Course.objects.count()
        a_c = Assignment.objects.count()
        j_c = Journal.objects.count()
        format_c = Format.objects.count()
        t_c = Template.objects.count()
        e_c = Entry.objects.count()
        p_c = PresetNode.objects.count()
        field_c = Field.objects.count()
        cont_c = Content.objects.count()

        assignment = factory.Assignment(format__templates=[{'type': Field.URL}])
        template = assignment.format.template_set.first()
        journal = factory.Journal(assignment=assignment, entries__n=0)
        n_c = Node.objects.filter(journal=journal).count()
        deadline = factory.DeadlinePresetNode(format=assignment.format, forced_template=template)
        entry = factory.PresetEntry(node=journal.node_set.get(preset=deadline))

        assert course_c + 1 == Course.objects.count(), 'A single course is created'
        assert a_c + 1 == Assignment.objects.count(), 'A single course and assignment is created'
        assert format_c + 1 == Format.objects.count(), 'A single format is created'
        assert j_c + 1 == Journal.objects.count(), 'A single journal is created'
        assert t_c + 1 == Template.objects.count(), 'A single template is created'
        assert e_c + 1 == Entry.objects.count(), 'A single entry is created'
        assert n_c + 1 == Node.objects.filter(journal=journal).count(), \
            'One additional node is created by the presetnode'
        assert p_c + 1 == PresetNode.objects.count(), 'A single preset node is created'
        assert field_c + 1 == Field.objects.count(), 'A single field is created'
        assert cont_c + 1 == Content.objects.count(), 'Content is created for the entry with a single field'

        # A single node has been added to the journal
        node = Node.objects.get(journal=journal)
        assert node.pk == entry.node.pk, 'The journal has no additional nodes'
        assert node.is_deadline, 'The entry node is of the correct type'
        assert node.preset.is_deadline, 'The attached preset is of the correct type'
        assert node.preset.forced_template == Template.objects.get(format__assignment=assignment), \
            'The deadline node\'s preset is indeed that of the assignment'
        assert Node.objects.get(type=Node.ENTRYDEADLINE, journal=journal, preset__forced_template=template), \
            'Correct node type is created, attached to the journal, whose PresetNode links to the correct template'

        # Now we create the preset deadline in advance, and attempt to create an entry for it
        # Note that the deadline template is specified, we would expect the entry to also be of that template
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        template = assignment.format.template_set.first()

        journal = factory.Journal(assignment=assignment, entries__n=0)
        deadline_preset_node = factory.DeadlinePresetNode(forced_template=template, format=assignment.format)
        entry = factory.PresetEntry(node=journal.node_set.get(preset=deadline_preset_node))
        journal = entry.node.journal
        assert journal.node_set.count() == 1, 'Only a single node should be added to the journal'
        assert Node.objects.get(
            type=Node.ENTRYDEADLINE, journal=journal, preset__forced_template=template, preset=deadline_preset_node), \
            'Correct node type is created, attached to the journal, whose PresetNode links to the correct template'

        # Again creating a preset deadline in advance, but now we only specify the format
        journal = factory.Journal(assignment=assignment, entries__n=0)
        deadline_preset_node = factory.DeadlinePresetNode(format=assignment.format)
        template = deadline_preset_node.forced_template
        entry = factory.PresetEntry(node=journal.node_set.get(preset=deadline_preset_node))

        assert Node.objects.get(type=Node.ENTRYDEADLINE, journal=journal, preset__forced_template=template), \
            'Correct node type is created, attached to the journal, whose PresetNode links to the correct template'

    def test_add_entry_to_deadline_preset_node(self):
        assignment = factory.Assignment(format__templates=False)
        archived_template = factory.Template(format=assignment.format, add_fields=[{'type': Field.TEXT}], archived=True)
        new_template = factory.Template(
            format=assignment.format, add_fields=[{'type': Field.TEXT}], chain=archived_template.chain)
        deadline = factory.DeadlinePresetNode(format=assignment.format, forced_template=new_template)
        journal = factory.Journal(assignment=assignment, entries__n=0)
        student = journal.author
        deadline_node = journal.node_set.get(preset=deadline)

        with self.assertRaises(VLEBadRequest) as context:
            entry_utils.add_entry_to_deadline_preset_node(deadline_node, archived_template, student)
        assert 'updated the template' in str(context.exception)

        different_chain_template = factory.Template(format=assignment.format, add_fields=[{'type': Field.TEXT}])
        with self.assertRaises(VLEBadRequest) as context:
            entry_utils.add_entry_to_deadline_preset_node(deadline_node, different_chain_template, student)
        assert 'Provided template is not used by the deadline' in str(context.exception)

        deadline_node.type = 'p'
        with self.assertRaises(VLEBadRequest) as context:
            entry_utils.add_entry_to_deadline_preset_node(deadline_node, new_template, student)
        assert 'Provided deadline type does not support entries' in str(context.exception)
        deadline_node.type = 'd'

        lock_date = deadline.lock_date
        deadline.lock_date = datetime.now()
        deadline.save()
        deadline_node.refresh_from_db()
        with self.assertRaises(VLEBadRequest) as context:
            entry_utils.add_entry_to_deadline_preset_node(deadline_node, new_template, student)
        assert 'The lock date for this deadline has passed' in str(context.exception)
        deadline.lock_date = lock_date
        deadline.save()

        entry = factory.PresetEntry(node=deadline_node)
        with self.assertRaises(VLEBadRequest) as context:
            entry_utils.add_entry_to_deadline_preset_node(deadline_node, new_template, student)
        assert 'Deadline already contains an entry' in str(context.exception)
        entry.delete()
        deadline_node.refresh_from_db()

        entry = entry_utils.add_entry_to_deadline_preset_node(deadline_node, new_template, student)
        assert entry.node == deadline_node, 'Entry creation was succesful'

    def test_validate_entry_content(self):
        assignment = factory.Assignment(format__templates=False)
        template = factory.TemplateAllTypes(format=assignment.format)
        journal = factory.Journal(assignment=assignment, entries__n=0)
        entry = factory.UnlimitedEntry(node__journal=journal, template=template)

        # Required field required
        required_field = factory.Field(template=template, required=True)
        self.assertRaises(VLEMissingRequiredField, validate_entry_content, {}, required_field)
        self.assertRaises(VLEMissingRequiredField, validate_entry_content, None, required_field)
        self.assertRaises(VLEMissingRequiredField, validate_entry_content, False, required_field)
        # Optional field
        optional_field = factory.Field(template=template, required=False)
        validate_entry_content({}, optional_field)
        validate_entry_content('', optional_field)
        validate_entry_content(None, optional_field)
        validate_entry_content(False, optional_field)

        # Test Url with allowed schemes
        validate_entry_content(faker.url(schemes=Field.ALLOWED_URL_SCHEMES), factory.UrlField(template=template))
        # Unallowed scheme should raise validation error
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            faker.url(schemes=('illega')),
            factory.UrlField(template=template)
        )

        # Test Video
        valid_youtube_video_url = 'http://www.youtube.com/watch?v=06xKPwQuMfk'
        video_field = factory.VideoField(template=template)
        with mock.patch('VLE.validators.validate_video_data') as validate_video_data_mock:
            validate_entry_content('http://www.youtube.com/watch?v=06xKPwQuMfk', video_field)
            validate_video_data_mock.assert_called_with(video_field, valid_youtube_video_url)

        selection_field = factory.SelectionField(template=template)
        validate_entry_content(json.loads(selection_field.options)[0], selection_field)
        self.assertRaises(ValidationError, validate_entry_content, 'Not in options', selection_field)

        valid_date_content = entry.content_set.get(field__type=Field.DATE)
        validate_entry_content(valid_date_content.data, valid_date_content.field)
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            faker.date(pattern='NOT-Y%-ALLOWED-%m-FORMAT-%d'),
            valid_date_content.field
        )

        valid_datetime_content = entry.content_set.get(field__type=Field.DATETIME)
        validate_entry_content(valid_datetime_content.data, valid_datetime_content.field)
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            faker.date(pattern='NOT-Y%-ALLOWED-%m-FORMAT-%d'),
            valid_datetime_content.field
        )

        valid_file_field_content = entry.content_set.filter(field__type=Field.FILE).first()
        fc = FileContext.objects.get(content=valid_file_field_content)

        correct_data_dict = {'id': fc.pk, 'download_url': valid_file_field_content.data}
        validate_entry_content(correct_data_dict, valid_file_field_content.field)

        incorrect_data_dict = copy.deepcopy(correct_data_dict)
        validate_entry_content(incorrect_data_dict, valid_file_field_content.field)
        incorrect_data_dict['id'] = 'incorrectly_formatted'
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            incorrect_data_dict,
            valid_file_field_content.field
        )

        # FC does not exist
        incorrect_data_dict = copy.deepcopy(correct_data_dict)
        validate_entry_content(incorrect_data_dict, valid_file_field_content.field)
        incorrect_data_dict['id'] = FileContext.objects.count() + 9000
        self.assertRaises(
            FileContext.DoesNotExist,
            validate_entry_content,
            incorrect_data_dict,
            valid_file_field_content.field
        )

        # FC file no longer exists
        os.remove(fc.file.path)
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            correct_data_dict,
            valid_file_field_content.field
        )

        self.assertRaises(
            ValidationError, validate_entry_content, 'some data', factory.NoSubmissionField(template=template))

        valid_rich_text_field_content = entry.content_set.get(field__type=Field.RICH_TEXT)
        fc = FileContext.objects.get(content=valid_rich_text_field_content)

        # Data contains bogus FC's
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            valid_rich_text_field_content.data.replace(
                fc.download_url(access_id=fc.access_id),
                f'{settings.API_URL}/files/{fc.pk}?access_id=123fake',
            ),
            valid_rich_text_field_content.field
        )

        # FC file no longer exists
        os.remove(fc.file.path)
        self.assertRaises(
            ValidationError,
            validate_entry_content,
            valid_rich_text_field_content.data,
            valid_rich_text_field_content.field
        )

    def test_validate_video_data(self):
        assignment = factory.Assignment(format__templates=False)
        template = factory.Template(format=assignment.format)

        valid_youtube_video_url = 'http://www.youtube.com/watch?v=06xKPwQuMfk'
        youtube_video_field = factory.VideoField(template=template, options=f'{Field.YOUTUBE}')
        with mock.patch(
            'VLE.validators.validate_youtube_url_with_video_id') as validate_youtube_video_url_mock, mock.patch(
                'VLE.validators.validate_kaltura_video_embed_code') as validate_kaltura_mock:
            validate_entry_content(valid_youtube_video_url, youtube_video_field)
            validate_youtube_video_url_mock.assert_called_with(valid_youtube_video_url)
            assert not validate_kaltura_mock.called

        valid_kaltura_embed_code = kaltura_what_is_ej_embed_code
        kaltura_video_field = factory.VideoField(template=template, options=f'{Field.KALTURA}')
        with mock.patch(
            'VLE.validators.validate_youtube_url_with_video_id') as validate_youtube_video_url_mock, mock.patch(
                'VLE.validators.validate_kaltura_video_embed_code') as validate_kaltura_mock:
            validate_entry_content(valid_kaltura_embed_code, kaltura_video_field)
            assert not validate_youtube_video_url_mock.called
            validate_kaltura_mock.assert_called_with(valid_kaltura_embed_code)

    def test_assignment_unpublish_with_entries(self):
        assignment = factory.Assignment()

        # It should be no problem to change the published state of a fresh assignment
        assert not assignment.has_entries(), 'Empty assignment should hold no entries'
        assert assignment.can_unpublish(), 'Without entries it should be possible to unpublish the assignment'
        api.update(self, 'assignments', params={'pk': assignment.pk, 'is_published': False}, user=assignment.author)
        api.update(self, 'assignments', params={'pk': assignment.pk, 'is_published': True}, user=assignment.author)

        # Create a journal with non graded entries
        factory.Journal(assignment=assignment, entries__n=1)

        # It should no longer be possible to unpublish as the assignment now holds entries
        assert assignment.has_entries(), 'Assignment should now hold entries'
        assert not assignment.can_unpublish(), 'Assignment should no longer be unpublishable'
        api.update(self, 'assignments', params={'pk': assignment.pk, 'is_published': False},
                   user=assignment.author, status=400)

    def test_create_entry(self):
        # Check valid entry creation
        resp = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        entry = Entry.objects.get(pk=resp['id'])
        self.student.check_can_edit(entry)
        resp2 = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        assert resp['id'] != resp2['id'], 'Multiple creations should lead to different ids'
        assert resp['author'] == self.student.full_name
        assert not resp['is_draft'], 'Entry response should NOT be draft if is_draft is not supplied'
        assert not Entry.objects.get(pk=resp['id']).is_draft, 'Entry should NOT be draft if is_draft is not supplied'

        # Check if students cannot update journals without required parts filled in
        create_params = self.valid_create_params.copy()
        create_params['content'] = {
            list(self.valid_create_params['content'])[1]: 'only optional field filled',
        }
        api.create(self, 'entries', params=create_params, user=self.student, status=400)

        # Check for assignment locked
        self.group_journal.assignment.due_date = datetime.now()
        self.group_journal.assignment.lock_date = datetime.now()
        self.group_journal.assignment.save()
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(node__journal=self.group_journal).first(),
        )
        api.create(self, 'entries', params=create_params, user=self.student, status=403)
        self.group_journal.assignment.lock_date = datetime.today() + timedelta(1)
        self.group_journal.assignment.save()

        # Check if template for other assignment wont work
        create_params = self.valid_create_params.copy()
        alt_journal = factory.Journal()
        template = factory.TextTemplate(format=alt_journal.assignment.format)
        create_params['template_id'] = template.pk
        api.create(self, 'entries', params=create_params, user=self.student, status=403)

        # Entries can no longer be created if the LTI link is outdated (new active uplink)
        assignment_old_lti_id = self.group_journal.assignment.active_lti_id
        self.group_journal.assignment.active_lti_id = 'new_lti_id_1'
        self.group_journal.assignment.save()
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(node__journal=self.group_journal).first(),
        )
        resp = api.create(self, 'entries', params=self.valid_create_params, user=self.student, status=403)
        assert resp['description'] == self.group_journal.outdated_link_warning_msg, \
            'When the active LTI uplink is outdated no more entries can be created.'
        self.group_journal.assignment.active_lti_id = assignment_old_lti_id
        self.group_journal.assignment.save()

        # Cannot set a custom title when the template does not allow it
        payload = deepcopy(self.valid_create_params)
        TemplateChain.objects.filter(template=payload['template_id']).update(allow_custom_title=False)
        title = 'Custom'
        payload['title'] = title
        api.create(self, 'entries', params=payload, user=self.student, status=403)

        # But we can do so if the template does allow for a custom title
        TemplateChain.objects.filter(template=payload['template_id']).update(allow_custom_title=True)
        resp = api.create(self, 'entries', params=payload, user=self.student)['entry']
        assert resp['title'] == title, \
            'It is possible to set a custom entry title if its template allows as such'

        # A custom title can also be set for deadline entries
        payload = deepcopy(payload)
        deadline = factory.DeadlinePresetNode(format=self.g_assignment.format, forced_template=self.template)
        payload['node_id'] = self.group_journal.node_set.get(preset=deadline).pk
        resp = api.create(self, 'entries', params=payload, user=self.student)['entry']
        assert resp['title'] == title, \
            'It is possible to set a custom entry title if its template allows as such, for a deadline entry as well'

        # Check entry categories, fixed categories
        cat = factory.Category(assignment=self.g_assignment, templates=self.template)
        payload = deepcopy(self.valid_create_params)
        payload['category_ids'] = [cat.pk]

        with mock.patch('VLE.models.Entry.validate_categories') as validate_categories_mock:
            resp = api.create(self, 'entries', params=payload, user=self.student)['entry']
            validate_categories_mock.assert_called_with(payload['category_ids'], self.g_assignment, self.template)
        assert resp['categories'][0]['id'] == cat.pk
        assert all(link.author == self.student for link in cat.entrycategorylink_set.filter(entry__pk=resp['id']))

        # Check entry categories, allowing custom categories
        cat2 = factory.Category(assignment=self.g_assignment)
        self.template.chain.allow_custom_categories = True
        self.template.chain.save()
        payload = deepcopy(self.valid_create_params)
        payload['category_ids'] = [cat.pk, cat2.pk]
        resp = api.create(self, 'entries', params=payload, user=self.student)['entry']
        entry = Entry.objects.get(pk=resp['id'])
        assert set(entry.categories.all()) == set([cat, cat2]), (
            'Entry is succesfully created, including categories which are not all default for the template '
            'since we allow custom categories'
        )

        # It should not be possible to add a category on entry creation when the template has no default
        # categories and allow_custom_categories is disabled
        self.template.chain.allow_custom_categories = False
        self.template.chain.save()
        self.template.categories.set([])
        payload = deepcopy(self.valid_create_params)
        payload['category_ids'] = [cat2.pk]
        api.create(self, 'entries', params=payload, user=self.student, status=400)

        # TODO: Test for entry bound to entrydeadline
        # TODO: Test with file upload
        # TODO: Test added index

    def test_create_entry_title(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        template = assignment.format.template_set.first()
        TemplateChain.objects.filter(template=template).update(allow_custom_title=False)
        journal = factory.Journal(assignment=assignment, entries__n=0)

        # Providing an empty title despite the template setting not allowing a custom title is allowed
        for val in ['', None]:
            params = factory.UnlimitedEntryCreationParams(title=val, journal=journal, author=journal.author)
            resp = api.create(self, 'entries', params=params, user=journal.author)['entry']
            entry = Entry.objects.get(pk=resp['id'])

            assert not entry.title, 'Entry title remains unset (None or empty string)'
            assert resp['title'] == template.name, (
                'The entry title is still serialized based on the template name despite having been passed an empty '
                'title during creation'
            )

        # A user cannot pass an actual value as title when the template setting does not allow as such
        params = factory.UnlimitedEntryCreationParams(title='A title', journal=journal, author=journal.author)
        api.create(self, 'entries', params=params, user=journal.author, status=403)

        # We now allow a custom title to be set
        TemplateChain.objects.filter(template=template).update(allow_custom_title=True)

        # Because an entry title is optional, it is still possible to provide an empty value as title.
        # In this scenario we expect the default title to be set (template name or preset node display name)
        for val in ['', None]:
            params = factory.UnlimitedEntryCreationParams(title=val, journal=journal, author=journal.author)
            resp = api.create(self, 'entries', params=params, user=journal.author)['entry']
            entry = Entry.objects.get(pk=resp['id'])

            assert not entry.title, 'Entry title remains unset (None or empty string)'
            assert resp['title'] == template.name, (
                'The entry title is still serialized based on the template name despite having been passed an empty '
                'title during creation'
            )

        title = 'A title'
        params = factory.UnlimitedEntryCreationParams(title=title, journal=journal, author=journal.author)
        resp = api.create(self, 'entries', params=params, user=journal.author)['entry']
        assert resp['title'] == title

    def test_patch_entry_title(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        template = assignment.format.template_set.first()
        TemplateChain.objects.filter(template=template).update(allow_custom_title=False)
        journal = factory.Journal(assignment=assignment, entries__n=0)
        entry = factory.UnlimitedEntry(node__journal=journal)
        params = EntrySerializer(entry).data
        params['pk'] = entry.pk

        # Providing an empty title despite the template setting not allowing a custom title is allowed
        for val in ['', None]:
            params['title'] = val
            resp = api.update(self, 'entries', params=params, user=journal.author)['entry']
            entry.refresh_from_db()

            assert not entry.title, 'Entry title remains unset (None or empty string)'
            assert resp['title'] == template.name, (
                'The entry title is still serialized based on the template name despite having been passed an empty '
                'title during creation'
            )

        # A user cannot pass an actual value as title when the template setting does not allow as such
        params['title'] = 'A value'
        api.update(self, 'entries', params=params, user=journal.author, status=403)

        # We now allow a custom title to be set
        TemplateChain.objects.filter(template=template).update(allow_custom_title=True)

        # Because an entry title is optional, it is still possible to provide an empty value as title.
        # In this scenario we expect the default title to be set (template name or preset node display name)
        for val in ['', None]:
            params['title'] = val
            resp = api.update(self, 'entries', params=params, user=journal.author)['entry']
            entry.refresh_from_db()

            assert not entry.title, 'Entry title remains unset (None or empty string)'
            assert resp['title'] == template.name, (
                'The entry title is still serialized based on the template name despite having been passed an empty '
                'title during creation'
            )

        title = 'A value'
        params['title'] = title
        resp = api.update(self, 'entries', params=params, user=journal.author)['entry']
        assert resp['title'] == title

    def test_create_invalid_preset_entry(self):
        # Entries cannot be created after lockdate
        create_params = factory.PresetEntryCreationParams(
            journal=self.group_journal
        )
        node = Node.objects.get(pk=create_params['node_id'])
        node.preset.due_date = timezone.now() - timedelta(weeks=1)
        node.preset.lock_date = timezone.now() - timedelta(weeks=1)
        node.preset.save()
        resp = api.create(self, 'entries', params=create_params, user=self.student, status=400)['description']
        assert 'lock date' in resp, 'Node should be locked, and not available for new entry'
        node.preset.due_date = timezone.now() + timedelta(weeks=1)
        node.preset.lock_date = timezone.now() + timedelta(weeks=1)
        node.preset.save()

        # It should not be possible to create a deadline entry using a template other than the preset's template
        invalid_params = create_params.copy()
        invalid_params['template_id'] = factory.Template(format=self.g_assignment.format).pk
        resp = api.create(self, 'entries', params=invalid_params, user=self.student, status=400)['description']
        assert 'Provided template is not used by the deadline' in resp, \
            'It should not be possible to create a deadline entry using a template other than the preset\'s template'

        # Node must be progress node if 'node_id' is supplied
        node.type = Node.PROGRESS
        node.save()
        resp = api.create(self, 'entries', params=create_params, user=self.student, status=400)['description']
        assert 'Provided deadline type does not support entries' in resp, \
            'You should not be able to create an entry in a PROGRESS node'
        node.type = Node.ENTRYDEADLINE
        node.save()

        # Passed node already contains an entry, this should also be indicated correctly
        api.create(self, 'entries', params=create_params, user=self.student)['description']
        resp = api.create(self, 'entries', params=create_params, user=self.student, status=400)['description']
        assert 'already contains an entry' in resp, \
            'Passed node already contains an entry, this should also be indicated correctly'

        # Passed fields should be from template
        invalid_params = create_params.copy()
        other_template = factory.Template(format=self.g_assignment.format)
        other_field_pk = Field.objects.exclude(template=other_template).first().pk
        invalid_params['content'][other_field_pk] = 'OTHER FIELD CONTENT'
        resp = api.create(self, 'entries', params=create_params, user=self.student, status=400)['description']
        assert 'Passed field is not from template.' in resp, \
            'Passed fields should be from template, if not, it should respond with a bad request'

    def test_entry_in_teacher_journal(self):
        assignment = factory.Assignment()
        teacher_journal = assignment.assignmentparticipation_set.get(user=assignment.author).journal
        template = assignment.format.template_set.first()
        # The creation of this entry should not be possible via API
        mocked_entry = factory.UnlimitedEntry(
            author=assignment.author, template=template, node__journal=teacher_journal)

        valid_creation_data = {
            'journal_id': teacher_journal.pk,
            'template_id': template.pk,
            'content': [{'data': c.data, 'id': c.field.id} for c in mocked_entry.content_set.all()]
        }

        # Teachers shouldn't be able to make entries on their own journal
        self.assertRaises(
            Journal.DoesNotExist,
            assignment.author.check_can_edit,
            mocked_entry,
        )
        # The journal for which we want to create an entry does not exist via normal query set.
        api.create(self, 'entries', params=valid_creation_data, user=assignment.author, status=404)

    def test_valid_entry(self):
        """Attempt to post an entry with valid and invalid content for each field."""
        # Get a template which contains all field types (each of them optional).
        template = factory.TemplateAllTypes(format=self.format)
        fields = Field.objects.filter(template=template)

        # Define valid and invalid contents for each of the fields.
        valid_content = {
            Field.TEXT: 'text',
            Field.RICH_TEXT: '<p> RICH </p>',
            Field.VIDEO: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            Field.URL: 'https://ejournal.app',
            Field.DATE: '2019-10-10',
            Field.DATETIME: '2019-10-10T12:12:00',
            Field.SELECTION: 'a',
        }
        invalid_content = {
            # Field.VIDEO: 'https://www.test.com/watch?v=dQw4w9WgXcQ', TODO: This should fail.
            Field.URL: 'textonly',
            Field.DATE: 6,
            Field.DATETIME: 'text',
            Field.SELECTION: 'x',
            Field.NO_SUBMISSION: 'a',
        }

        # Attempt to post an entry with valid and invalid content for each field.
        for field in fields:
            create_params = {
                'journal_id': self.group_journal.pk,
                'template_id': template.pk,
                'content': {},
            }

            # If valid input is defined for this field type, creating an entry should be succesful.
            if field.type in valid_content:
                create_params['content'][field.pk] = valid_content[field.type]
                api.create(self, 'entries', params=create_params, user=self.student)

            # If invalid input is defined for this field type, creating an entry should fail.
            if field.type in invalid_content:
                create_params['content'][field.pk] = invalid_content[field.type]
                api.create(self, 'entries', params=create_params, user=self.student, status=400)

    def test_required_and_optional(self):
        # Creation with only required params should work
        required_only_creation = {
            'journal_id': self.group_journal.pk,
            'template_id': self.template.pk,
            'content': {},
        }
        fields = Field.objects.filter(template=self.template)
        required_only_creation['content'] = {field.id: 'test_data' for field in fields if field.required}
        api.create(self, 'entries', params=required_only_creation, user=self.student)

        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        params = {
            'pk': entry['id'],
            'content': {field.id: '' for field in fields}
        }
        # Student should always provide required parameters
        api.update(self, 'entries', params=params.copy(), user=self.student, status=400)

        # Student should be able to update only the required fields, leaving the optinal fields empty
        factory.Field(template=self.template, required=False, type=Field.TEXT)
        fields = self.template.field_set.all()
        for empty_value in [None, '']:
            params = {
                'pk': entry['id'],
                'content': {field.pk: 'filled' if field.required else empty_value for field in fields}
            }
            resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
            assert len(resp['content']) == self.template.field_set.count(), \
                'Response should have emptied the optional fields, not deleted'
            assert any([val is None for val in resp['content'].values()]), \
                'Response should have emptied the optional fields, not deleted'
        # Student should be able to edit an optinal field
        params = {
            'pk': entry['id'],
            'content': {field.pk: 'filled' for field in fields}
        }
        resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
        assert len(resp['content']) == self.template.field_set.count()
        assert resp['content'][list(resp['content'])[0]] == 'filled', 'Response should have filled the optional fields'

    def test_optional_fields_are_none(self):
        # As all fields are optional, data None should also work
        all_types = factory.TemplateAllTypes(format=self.format)
        fields = Field.objects.filter(template=all_types)
        fields.update(required=False)
        empty_create_params = {
            'journal_id': self.group_journal.pk,
            'template_id': all_types.pk,
            'content': {}
        }
        empty_create_params['content'] = {field.id: None for field in fields}
        resp = api.create(self, 'entries', params=empty_create_params, user=self.student)['entry']
        api.update(self, 'entries', params={**empty_create_params, 'pk': resp['id']}, user=self.student)

    def test_update_entry(self):
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']

        params = {
            'pk': entry['id'],
            'content': entry['content'].copy()
        }

        updated_entry = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
        assert entry['last_edited'] != updated_entry['last_edited'], \
            'Last edited should update when entry content changes'

        # Cannot set a custom title when the template does not allow it
        payload = deepcopy(params)
        TemplateChain.objects.filter(template=entry['template']['id']).update(allow_custom_title=False)
        title = 'Custom'
        payload['title'] = title
        api.update(self, 'entries', params=payload, user=self.student, status=403)

        # But we can do so if the template does allow for a custom title
        TemplateChain.objects.filter(template=entry['template']['id']).update(allow_custom_title=True)
        resp = api.update(self, 'entries', params=payload, user=self.student)['entry']
        assert resp['title'] == title, \
            'It is possible to set a custom entry title if its template allows as such'

        # Check if last_edited_by gets set to the correct other user
        last_edited = factory.AssignmentParticipation(assignment=self.group_journal.assignment)
        self.group_journal.add_author(last_edited)
        resp = api.update(self, 'entries', params=params.copy(), user=last_edited.user)['entry']
        assert resp['last_edited_by'] == last_edited.user.full_name

        # Other users shouldn't be able to update an entry
        api.update(self, 'entries', params=params.copy(), user=self.teacher, status=403)

        # Check for assignment locked
        self.group_journal.assignment.unlock_date = datetime.today() - timedelta(3)
        self.group_journal.assignment.due_date = datetime.today() - timedelta(2)
        self.group_journal.assignment.lock_date = datetime.today() - timedelta(1)
        self.group_journal.assignment.save()
        api.update(self, 'entries', params=params.copy(), user=self.student, status=403)
        self.group_journal.assignment.unlock_date = datetime.now()
        self.group_journal.assignment.due_date = datetime.now() + timedelta(weeks=1)
        self.group_journal.assignment.lock_date = datetime.now() + timedelta(weeks=2)
        self.group_journal.assignment.save()

        # Entries can no longer be edited if the LTI link is outdated (new active uplink)
        assignment_old_lti_id = self.group_journal.assignment.active_lti_id
        self.group_journal.assignment.active_lti_id = 'new_lti_id_2'
        self.group_journal.assignment.save()
        resp = api.update(self, 'entries', params=params.copy(), user=self.student, status=403)
        assert resp['description'] == self.group_journal.outdated_link_warning_msg, \
            'When the active LTI uplink is outdated no more entries can be created.'
        self.group_journal.assignment.active_lti_id = assignment_old_lti_id
        self.group_journal.assignment.save()

        # Grade and publish an entry
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.student,
                   status=403)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.teacher)

        # Shouldn't be able to edit entries after grade
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(pk=entry['id']).first(),
        )
        api.update(self, 'entries', params=params.copy(), user=self.student, status=400)

        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': False}, user=self.teacher)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.teacher)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True},
                   user=factory.Teacher(), status=403)

        # Check if a published entry cannot be unpublished
        api.create(self, 'grades', params={'entry_id': entry['id'], 'published': False}, user=self.teacher, status=400)

    def test_update_entry_file_field(self):
        file_template = factory.Template(format=self.g_assignment.format, add_fields=[{'type': Field.FILE}])
        file_field = file_template.field_set.first()
        entry = factory.UnlimitedEntry(node__journal=self.group_journal, template=file_template)
        file_content = entry.content_set.first()

        new_fc = factory.TempFileContext(author=self.student)
        params = {
            'pk': entry.pk,
            'journal_id': self.group_journal.pk,
            'content': {file_field.pk: FileSerializer(new_fc).data}
        }
        updated_entry_resp = api.update(self, 'entries', params=params, user=self.student)['entry']

        file_content.refresh_from_db()
        assert int(file_content.data) == new_fc.pk, 'Entry file content is updated to match the new file'
        assert updated_entry_resp['content'][str(file_field.pk)]['id'] == new_fc.pk, \
            'The updated entry serializes the new file correctly'

    def test_destroy_entry(self):
        # Only a student can delete their own entry
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        api.delete(self, 'entries', params={'pk': entry['id']}, user=factory.Student(), status=403)
        api.delete(self, 'entries', params={'pk': entry['id']}, user=self.teacher, status=403)
        api.delete(self, 'entries', params={'pk': entry['id']}, user=self.student)

        # Superusers can delete all entries
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        api.delete(self, 'entries', params={'pk': entry['id']}, user=factory.Admin())

        # Only superusers should be allowed to delete graded entries
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.teacher)
        api.delete(self, 'entries', params={'pk': entry['id']}, user=self.student, status=403)
        api.delete(self, 'entries', params={'pk': entry['id']}, user=factory.Admin())

        # Entries can no longer be deleted if the LTI link is outdated (new active uplink)
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        entry = Entry.objects.get(pk=entry['id'])
        journal = entry.node.journal
        assignment_old_lti_id = journal.assignment.active_lti_id
        ap = journal.authors.first()
        ap_old_grade_url = ap.grade_url
        ap_old_sourcedid = ap.sourcedid
        journal.assignment.active_lti_id = 'new_lti_id_3'
        journal.assignment.save()

        resp = api.delete(self, 'entries', params={'pk': entry.pk}, user=self.student, status=403)
        assert resp['description'] == journal.outdated_link_warning_msg, 'When the active LTI uplink is outdated' \
            ' no more entries can be created.'
        journal.assignment.active_lti_id = assignment_old_lti_id
        journal.assignment.save()
        ap.grade_url = ap_old_grade_url
        ap.sourcedid = ap_old_sourcedid
        ap.save()

        # Only superusers should be allowed to delete locked entries
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        self.group_journal.assignment.unlock_date = datetime.today() - timedelta(3)
        self.group_journal.assignment.due_date = datetime.today() - timedelta(2)
        self.group_journal.assignment.lock_date = datetime.today() - timedelta(1)
        self.group_journal.assignment.save()
        api.delete(self, 'entries', params={'pk': entry['id']}, user=self.student, status=403)
        api.delete(self, 'entries', params={'pk': entry['id']}, user=factory.Admin())

    def test_grade(self):
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        graded_entry = api.create(
            self, 'grades', params={'entry_id': entry['id'], 'grade': 1, 'published': True},
            user=self.teacher)['entry']
        assert graded_entry['grade']['grade'] == 1
        assert entry['last_edited'] == graded_entry['last_edited'], \
            'Last edited of entry should not update when grade changes'
        entry = api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 0, 'published': True},
                           user=self.teacher)['entry']
        assert entry['grade']['grade'] == 0

    def test_grade_history(self):
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 1, 'published': True},
                   user=self.teacher)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 1, 'published': False},
                   user=self.teacher)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 10, 'published': True},
                   user=self.teacher)
        grade_history = api.get_list(self, 'grades', params={'entry_id': entry['id']},
                                     user=self.teacher)['grade_history']
        assert len(grade_history) == 3, 'Grade history is incomplete.'
        assert grade_history[0]['author'] == grade_history[1]['author'] == grade_history[2]['author'] == \
            self.teacher.full_name, 'Teacher should be author of all grades.'
        assert grade_history[0]['grade'] == grade_history[1]['grade'] == 1
        assert grade_history[2]['grade'] == 10
        assert grade_history[0]['published'] == grade_history[2]['published'] and grade_history[0]['published'], \
            'First and last grade should be published.'
        assert not grade_history[1]['published'], 'Second grade should be unpublished.'

    def test_keep_entry_on_delete_preset(self):
        entrydeadline = factory.DeadlinePresetNode(format=self.format)

        node = Node.objects.get(preset=entrydeadline, journal=self.group_journal)
        node_student2 = Node.objects.get(preset=entrydeadline, journal=self.journal2)
        create_params = {
            'journal_id': self.group_journal.pk,
            'template_id': entrydeadline.forced_template.pk,
            'content': {},
            'node_id': node.pk
        }

        fields = Field.objects.filter(template=entrydeadline.forced_template)
        create_params['content'] = {field.pk: 'test data' for field in fields}
        entry = api.create(self, 'entries', params=create_params, user=self.student)['entry']

        assert Entry.objects.filter(pk=entry['id']).exists(), \
            'Entry exists before deletion of preset'
        assert Node.objects.filter(entry=entry['id']).exists(), \
            'Node exist before deletion of preset'
        assert Node.objects.filter(pk=node_student2.pk).exists(), \
            'Node student 2 exist before deletion of preset'

        entrydeadline.delete()

        assert Entry.objects.filter(pk=entry['id']).exists(), \
            'Entry should also exist after deletion of preset'
        assert Node.objects.filter(entry=entry['id']).exists(), \
            'Node should also exist after deletion of preset'
        assert not Node.objects.filter(pk=node_student2.pk).exists(), \
            'Node student 2 does not exist after deletion of preset'

    def test_utils_delete_entry(self):
        assignment = factory.Assignment(format__templates=[])
        factory.TemplateAllTypes(format=assignment.format)
        factory.ProgressPresetNode(format=assignment.format)

        all_pre_setup_contents = list(Content.objects.all().values_list('pk', flat=True))
        all_pre_setup_comments = list(Comment.objects.all().values_list('pk', flat=True))
        all_pre_setup_fcs = list(FileContext.objects.all().values_list('pk', flat=True))

        journal = factory.Journal(assignment=assignment, entries__n=0)
        unlimited_entry = factory.UnlimitedEntry(node__journal=journal)
        assert journal.node_set.count() == 2
        progress_node = journal.node_set.get(type=Node.PROGRESS)
        factory.StudentComment(entry=unlimited_entry, n_att_files=1, n_rt_files=1)

        unlimited_entry.delete()

        assert journal.node_set.count() == 1, 'One node should remain, hopefully the progress node'
        node = journal.node_set.first()
        assert equal_models(node, progress_node), 'Progress node is unchanged'

        assert not Entry.objects.filter(pk=unlimited_entry.pk).exists(), 'The entry itself is deleted'

        assert not Content.objects.all().exclude(pk__in=all_pre_setup_contents).exists(), 'Content should cascade'
        assert not Comment.objects.all().exclude(pk__in=all_pre_setup_comments).exists(), 'Comments should cascade'
        assert not FileContext.objects.all().exclude(pk__in=all_pre_setup_fcs).exists(), \
            'All fcs should cascade (comment rt, comment attached files, content rt, content files)'

        deadline = factory.DeadlinePresetNode(format=assignment.format)
        deadline_entry = factory.PresetEntry(node=journal.node_set.get(preset=deadline))
        deadline_node = journal.node_set.get(type=Node.ENTRYDEADLINE)
        factory.StudentComment(entry=deadline_entry, n_att_files=1, n_rt_files=1)

        deadline_entry.delete()

        assert journal.node_set.count() == 2, 'Progress node and ENTRYDEADLINE node should remain'
        post_delete_progress_node = journal.node_set.get(type=Node.PROGRESS)
        post_delete_deadline_node = journal.node_set.get(type=Node.ENTRYDEADLINE)
        assert equal_models(post_delete_progress_node, post_delete_progress_node), \
            'Progress node is unchanged'
        assert equal_models(deadline_node, post_delete_deadline_node, ignore_keys=['entry'])
        assert post_delete_deadline_node.entry is None, 'Entry should be set to none after deletion'

        assert not Content.objects.all().exclude(pk__in=all_pre_setup_contents).exists(), 'Content should cascade'
        assert not Comment.objects.all().exclude(pk__in=all_pre_setup_comments).exists(), 'Comments should cascade'
        assert not FileContext.objects.all().exclude(pk__in=all_pre_setup_fcs).exists(), \
            'All fcs should cascade (comment rt, comment attached files, content rt, content files)'

        factory.UnlimitedEntry(node__journal=journal)
        factory.UnlimitedEntry(node__journal=journal)
        Entry.objects.filter(node__journal=journal).delete()

        assert not Content.objects.all().exclude(pk__in=all_pre_setup_contents).exists(), \
            'Cascade works properly on bulk delete as well'

    def test_entry_serializer_specific(self):
        grade = 3
        entry = factory.UnlimitedEntry(
            node__journal__assignment__format__templates=[{'type': Field.TEXT}],
            grade__grade=grade,
            categories=2,
        )
        journal = entry.node.journal
        assignment = journal.assignment
        student = journal.author
        teacher = journal.assignment.author

        def add_state(entry):
            category = factory.Category(assignment=journal.assignment, templates=entry.template)
            entry.categories.add(category)

        with QueryContext() as context_pre:
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': student}
            ).data
        add_state(entry)
        with QueryContext() as context_post:
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': student}
            ).data
        assert len(context_pre) == len(context_post) and len(context_pre) <= self.entry_serializer_base_query_count

        assert data['grade']['grade'] == grade

        entry = factory.UnlimitedEntry(
            node__journal__assignment__format__templates=[{'type': Field.TEXT}],
            grade__published=False,
            grade__grade=2,
            node__journal=journal
        )

        # Teacher requires one additional query to check can_grade
        expected_queries = self.entry_serializer_base_query_count + 1
        with QueryContext() as context_pre:
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': teacher}
            ).data
        add_state(entry)
        with QueryContext() as context_post:
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': teacher}
            ).data
        assert len(context_pre) == len(context_post) and len(context_pre) <= expected_queries

        def check_is_editable():
            entry_without_grade = factory.UnlimitedEntry(node__journal=journal, grade=None)

            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry_without_grade.pk))[0],
                context={'user': teacher}
            ).data
            assert data['editable']

            assignment.due_date = timezone.now()
            assignment.lock_date = timezone.now()
            assignment.save()

            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry_without_grade.pk))[0],
                context={'user': teacher}
            ).data
            assert not data['editable']

            assignment.unlock_date = timezone.now() - timedelta(2)
            assignment.due_date = timezone.now() - timedelta(1)
            assignment.lock_date = timezone.now() - timedelta(1)
            assignment.save()
            graded_entry = factory.UnlimitedEntry(node__journal=journal, grade__grade=1)

            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=graded_entry.pk))[0],
                context={'user': teacher}
            ).data
            assert not data['editable']

            entry_unpublished_grade = factory.UnlimitedEntry(
                node__journal=journal, grade__grade=1, grade__published=False)

            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry_unpublished_grade.pk))[0],
                context={'user': teacher}
            ).data
            assert not data['editable']

        def check_entry_title():
            entry = factory.UnlimitedEntry(node__journal=journal)
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': teacher}
            ).data
            assert data['title'] == entry.template.name, \
                '''An unlimited entry's title should be the template name.'''

            deadline = factory.DeadlinePresetNode(format=journal.assignment.format)
            preset_entry = factory.PresetEntry(node=journal.node_set.get(preset=deadline))
            preset_node_display_name = 'Display Name'
            preset_entry.node.preset.display_name = preset_node_display_name
            preset_entry.node.preset.save()
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=preset_entry.pk)).get(),
                context={'user': teacher}
            ).data
            assert data['title'] == preset_node_display_name, \
                '''A preset entry's title should be the display name of the preset node.'''

            custom_title = 'Custom title'
            preset_entry.title = custom_title
            preset_entry.save()
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=preset_entry.pk)).get(),
                context={'user': teacher}
            ).data
            assert data['title'] == custom_title, \
                '''A student's custom entry title should take precedence over the preset node display name.'''
            preset_entry.title = None
            preset_entry.save()

            preset_entry.node.preset.delete()
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=preset_entry.pk)).get(),
                context={'user': teacher}
            ).data
            assert data['title'] == preset_entry.template.name, \
                '''A preset entry's title should be the display name of its template if the preset is deleted.
                Instead of the now deleted preset node's display name.'''

            params = factory.TeacherEntryCreationParams(assignment=assignment, show_title_in_timeline=True)
            te_id = api.create(self, 'teacher_entries', params=params, user=teacher)['teacher_entry']['id']
            te = TeacherEntry.objects.get(pk=te_id)
            entry = Entry.objects.filter(teacher_entry_id=te_id, node__journal=journal).latest('pk')
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': teacher}
            ).data
            assert data['title'] == te.title, \
                '''A teacher iniated entry's title should be the title of the teacher entry, provided
                show_title_in_timeline flag is set to True'''

            te.show_title_in_timeline = False
            te.save()
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': teacher}
            ).data
            assert data['title'] == entry.template.name, \
                '''A teacher iniated entry's title should fallback to the template's title if show_title_in_timeline
                flag is set to False'''

        def check_default_fields():
            assert data['author'] == student.full_name
            assert data['last_edited_by'] == student.full_name

            User.objects.filter(pk=entry.author_id).delete()
            student_deleted_data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
                context={'user': teacher}
            ).data
            assert student_deleted_data['author'] == User.UNKNOWN_STR
            assert student_deleted_data['last_edited_by'] == User.UNKNOWN_STR

        check_is_editable()
        check_entry_title()
        check_default_fields()

    def test_entry_serializer_files(self):
        n_file_fields = 3
        entry = factory.UnlimitedEntry(
            node__journal__assignment__format__templates=[{'type': Field.FILE} for _ in range(n_file_fields)],
        )
        journal = entry.node.journal
        student = journal.author

        # The entry serializer query count is invariant to the number of FILE fields.
        with assert_num_queries_less_than(self.entry_serializer_base_query_count):
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk)).get(),
                context={'user': student}
            ).data

        fc_ids = list(FileContext.objects.filter(content__entry=entry).values_list('pk', flat=True))
        for _, content in data['content'].items():
            assert content['id'] in fc_ids

    def test_entry_serializer_jir(self):
        source_journal = factory.Journal()
        student = source_journal.author

        jir = factory.JournalImportRequest(
            source=source_journal,
            state=JournalImportRequest.APPROVED_INC_GRADES,
            processor=factory.Teacher()
        )
        entry = factory.UnlimitedEntry(
            node__journal__ap__user=student,
            node__journal__assignment__author=jir.processor,
            node__journal__assignment__format__templates=[{'type': Field.TEXT}],
            jir=jir
        )

        # Jir requires a can_view_course check
        # Jir requires access to all source assignment's courses to provide the correct abbreviation
        with assert_num_queries_less_than(self.entry_serializer_base_query_count + 2):
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
                context={'user': student}
            ).data

        # JIR data required front end is serialized per entry
        assert data['jir']['processor']['full_name'] == jir.processor.full_name
        assert data['jir']['source']['assignment']['name'] == jir.source.assignment.name
        assert data['jir']['source']['assignment']['course']['abbreviation'] == \
            jir.source.assignment.courses.first().abbreviation

    def test_validate_categories(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        template = assignment.format.template_set.first()
        cat1 = factory.Category(assignment=assignment, templates=template)

        category_ids = Entry.validate_categories(None, assignment, template)
        assert not category_ids, 'If no categories are provided, the category_ids should be empty'

        category_ids = list(Category.objects.filter(pk=cat1.pk).values_list('pk', flat=True))
        category_ids = Entry.validate_categories(category_ids, assignment, template)
        assert category_ids == set([cat1.pk]), 'If validated, a set of the category pks should be returned'

        # Categories must be part of the provided assignment
        cat2 = factory.Category(assignment=factory.Assignment())
        category_ids = list(Category.objects.filter(pk__in=[cat1.pk, cat2.pk]).values_list('pk', flat=True))
        with self.assertRaises(ValidationError):
            Entry.validate_categories(category_ids, assignment, template)

        # If the template has fixed categories, the categories must be part of the template
        cat2 = factory.Category(assignment=factory.Assignment())
        category_ids = list(Category.objects.filter(pk=cat1.pk).values_list('pk', flat=True))
        template.categories.set([])
        assert not template.chain.allow_custom_categories
        with self.assertRaises(ValidationError):
            Entry.validate_categories(category_ids, assignment, template)

    def test_entry_add_category(self):
        category = factory.Category(assignment=self.g_assignment)
        entry = Entry.objects.filter(node__journal=self.group_journal).first()
        student = entry.author
        teacher = self.g_assignment.author

        entry.add_category(category, student)
        link_student = category.entrycategorylink_set.get(entry=entry, author=student)
        entry.add_category(category, teacher)
        link_teacher = category.entrycategorylink_set.get(entry=entry)
        assert link_student == link_teacher, 'Row can be reused.'
        assert link_student.author == student == link_teacher.author, \
            'Author should not be changed if the category was already part of the entry'

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_draft(self):
        create_draft_params = {
            **self.valid_create_params,
            'is_draft': True,
        }
        notification_count = Notification.objects.filter(type=Notification.NEW_ENTRY).count()
        resp = api.create(self, 'entries', params=create_draft_params, user=self.student)['entry']
        assert resp['is_draft'], 'Entry response should be draft if is_draft is set to true'
        assert Entry.objects.get(pk=resp['id']).is_draft, 'Entry should be draft if is_draft is set to true'

        assert notification_count == Notification.objects.filter(type=Notification.NEW_ENTRY).count(), \
            'No new notifications should be created for drafted entries'
        notification_count = Notification.objects.filter(type=Notification.NEW_ENTRY).count()
        params = {
            'pk': resp['id'],
            'content': resp['content'].copy(),
            'is_draft': True,
        }

        resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
        assert resp['is_draft'], 'Entry response should stay drafted if so supplied'
        assert Entry.objects.get(pk=resp['id']).is_draft, 'Entry should stay drafted if so supplied'

        assert notification_count == Notification.objects.filter(type=Notification.NEW_ENTRY).count(), \
            'No new notifications should be created when draft does not change'
        notification_count = Notification.objects.filter(type=Notification.NEW_ENTRY).count()

        params.pop('is_draft')
        resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
        assert not resp['is_draft'], 'Entry response should NO LONGER be drafted if not supplied'
        assert not Entry.objects.get(pk=resp['id']).is_draft, 'Entry should NO LONGER be drafted if not supplied'

        assert notification_count + 1 == Notification.objects.filter(type=Notification.NEW_ENTRY).count(), \
            'New notifications should be created when draft changes'

        params['is_draft'] = True
        resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
        assert Entry.objects.get(pk=resp['id']).is_draft, 'Entry should be able to be drafted after posting'

        assert notification_count == Notification.objects.filter(type=Notification.NEW_ENTRY).count(), \
            'Notifications should be delete when posted entry changes to draft'
        notification_count = Notification.objects.filter(type=Notification.NEW_ENTRY).count()
        Field.objects.update(required=True)
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
        needs_marking_before = self.group_journal.needs_marking

        create_draft_params['content'] = {}
        # Without content, an entry should still be able to be drafted
        resp = api.create(self, 'entries', params=create_draft_params, user=self.student)['entry']
        assert resp['is_draft'], 'Entry response should be draft if is_draft is set to true'
        assert Entry.objects.get(pk=resp['id']).is_draft, 'Entry should be draft if is_draft is set to true'

        params = {
            'pk': resp['id'],
            'content': resp['content'].copy(),
            'is_draft': True,
        }

        # But a drafted entry should not be able to be posted when it has invalid fields
        params.pop('is_draft')
        api.update(self, 'entries', params=params.copy(), user=self.student, status=400)
        assert Entry.objects.get(pk=resp['id']).is_draft, 'Entry should NOT be posted without all required fields'

        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
        assert needs_marking_before == self.group_journal.needs_marking, \
            'needs_marking should not get updated for drafted entries'
        assert notification_count == Notification.objects.filter(type=Notification.NEW_ENTRY).count(), \
            'No new notifications should be created for drafted entries'

        data = timeline.get_nodes(self.group_journal, user=self.student)
        found = False
        for node in data:
            if 'entry' in node and resp['id'] == node['entry']['id']:
                found = True
        assert found, 'Student should be able to see the draft entry'

        data = timeline.get_nodes(self.group_journal, user=self.teacher)
        found = False
        for node in data:
            if 'entry' in node and resp['id'] == node['entry']['id']:
                found = True
        assert not found, 'Teacher should NOT be able to see the draft entry'

        graded_entry = factory.Grade(entry__node__journal=self.group_journal).entry
        params = {
            'pk': graded_entry.pk,
            'content': {},
            'is_draft': True,
        }
        resp = api.update(self, 'entries', params=params.copy(), user=self.student, status=400)
        assert 'draft an entry' in resp['description'], \
            'Student should not be allowed to draft an entry that is no longer editable (e.g. graded)'
