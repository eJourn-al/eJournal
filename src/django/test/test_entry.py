import copy
import json
import os
import test.factory as factory
from datetime import date, timedelta
from test.utils import api
from test.utils.generic_utils import equal_models

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.test import TestCase
from django.utils import timezone
from faker import Faker

from VLE.models import (Assignment, Comment, Content, Course, Entry, Field, FileContext, Format, Grade, Journal,
                        JournalImportRequest, Node, PresetNode, Template, User)
from VLE.serializers import EntrySerializer
from VLE.utils import generic_utils as utils
from VLE.utils.error_handling import VLEMissingRequiredField, VLEPermissionError
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

        # Queries:
        # Select Entry and related tables 1
        # Template is selected, but its field set is also serialized 1
        self.entry_serializer_base_query_count = len(EntrySerializer.prefetch_related) + 1 + 1

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

        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment, node__journal__entries__n=0)
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

        journal = entry.node.journal
        assert Content.objects.filter(entry=entry).exists(), 'Content is created for the generated entry'
        assert Content.objects.filter(entry__node__journal=journal).exists(), \
            'Content is attached to the journal of the entry'
        assert Node.objects.filter(type=Node.ENTRY, journal__assignment=assignment, entry=entry).count() == 1, \
            'An entry node is correctly attached and of the correct type'
        assert entry.grade is None, 'Entry is ungraded by default'

        grade = 7
        grade_c = Grade.objects.count()

        entry = factory.UnlimitedEntry(
            node__journal__assignment=assignment, node__journal__entries__n=0, grade__grade=grade)
        assert grade_c + 1 == Grade.objects.count(), 'A single grade instance is created for the grade entry'
        assert entry.grade.grade == grade, 'Deep syntax works for entry grade instance'

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
        journal.refresh_from_db()  # Journal is created before the entry and grade in the factory
        assert journal.grade == entry.grade.grade + entry2.grade.grade

        factory.Grade(entry=entry, grade=2, published=False)
        journal.refresh_from_db()
        assert journal.grade == entry2.grade.grade, 'Journal grade consists only of published grades'

        factory.Grade(entry=entry, grade=5, published=True)
        journal.refresh_from_db()
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
        entry = factory.PresetEntry(node__journal=journal)

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

        deadline_preset_node = factory.DeadlinePresetNode(forced_template=template, format=assignment.format)
        journal = factory.Journal(assignment=assignment, entries__n=0)
        entry = factory.PresetEntry(node__journal=journal, node__preset=deadline_preset_node)
        journal = entry.node.journal
        assert journal.node_set.count() == 1, 'Only a single node should be added to the journal'
        assert Node.objects.get(
            type=Node.ENTRYDEADLINE, journal=journal, preset__forced_template=template, preset=deadline_preset_node), \
            'Correct node type is created, attached to the journal, whose PresetNode links to the correct template'

        # Again creating a preset deadline in advance, but now we only specify the format
        deadline_preset_node = factory.DeadlinePresetNode(format=assignment.format)
        template = deadline_preset_node.forced_template
        entry = factory.PresetEntry(
            node__journal__assignment=assignment, node__journal__entries__n=0, node__preset=deadline_preset_node)

        assert Node.objects.get(type=Node.ENTRYDEADLINE, journal=journal, preset__forced_template=template), \
            'Correct node type is created, attached to the journal, whose PresetNode links to the correct template'

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

        # Test Url and Video with allowed schemes
        validate_entry_content(faker.url(schemes=Field.ALLOWED_URL_SCHEMES), factory.UrlField(template=template))
        validate_entry_content(faker.url(schemes=Field.ALLOWED_URL_SCHEMES), factory.VideoField(template=template))
        # Unallowed scheme should raise validation error
        self.assertRaises(
            ValidationError, validate_entry_content, faker.url(schemes=('illega')), factory.UrlField(template=template))

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

        # Check if students cannot update journals without required parts filled in
        create_params = self.valid_create_params.copy()
        create_params['content'] = {
            list(self.valid_create_params['content'])[0]: 'only one field filled',
        }
        api.create(self, 'entries', params=create_params, user=self.student, status=400)

        # Check for assignment locked
        self.group_journal.assignment.lock_date = date.today() - timedelta(1)
        self.group_journal.assignment.save()
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(node__journal=self.group_journal).first(),
        )
        api.create(self, 'entries', params=create_params, user=self.student, status=403)
        self.group_journal.assignment.lock_date = date.today() + timedelta(1)
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

        # TODO: Test for entry bound to entrydeadline
        # TODO: Test with file upload
        # TODO: Test added index

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
            VLEPermissionError,
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

        # Check if last_edited_by gets set to the correct other user
        last_edited = factory.AssignmentParticipation(assignment=self.group_journal.assignment)
        self.group_journal.add_author(last_edited)
        resp = api.update(self, 'entries', params=params.copy(), user=last_edited.user)['entry']
        assert resp['last_edited_by'] == last_edited.user.full_name

        # Other users shouldn't be able to update an entry
        api.update(self, 'entries', params=params.copy(), user=self.teacher, status=403)

        # Check for assignment locked
        self.group_journal.assignment.lock_date = date.today() - timedelta(1)
        self.group_journal.assignment.save()
        api.update(self, 'entries', params=params.copy(), user=self.student, status=403)
        self.group_journal.assignment.lock_date = date.today() + timedelta(1)
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
        self.group_journal.assignment.lock_date = date.today() - timedelta(1)
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

        utils.delete_presets([{'id': entrydeadline.pk}])

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
        deadline_entry = factory.PresetEntry(node__journal=journal, node__preset=deadline)
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

    def test_entry_serializer(self):
        grade = 3
        entry = factory.UnlimitedEntry(
            node__journal__assignment__format__templates=[{'type': Field.TEXT}],
            grade__grade=grade
        )
        journal = entry.node.journal
        student = journal.author
        teacher = journal.assignment.author

        with self.assertNumQueries(self.entry_serializer_base_query_count):
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
                context={'user': student}
            ).data

        assert data['grade']['grade'] == grade

        entry = factory.UnlimitedEntry(
            node__journal__assignment__format__templates=[{'type': Field.TEXT}],
            grade__published=False,
            grade__grade=2,
            node__journal=journal
        )

        # Teacher requires one additional query to check can_grade
        with self.assertNumQueries(self.entry_serializer_base_query_count + 1):
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
                context={'user': teacher}
            ).data

        def check_is_editable():
            assignment = journal.assignment

            entry_without_grade = factory.UnlimitedEntry(node__journal=journal, grade=None)

            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry_without_grade.pk))[0],
                context={'user': teacher}
            ).data
            assert data['editable']

            assignment.lock_date = timezone.now()
            assignment.save()

            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry_without_grade.pk))[0],
                context={'user': teacher}
            ).data
            assert not data['editable']

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

        def check_default_fields():
            assert data['author'] == student.full_name
            assert data['last_edited_by'] == student.full_name

            User.objects.filter(pk=entry.author_id).delete()
            # student.delete()
            student_deleted_data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
                context={'user': teacher}
            ).data
            assert student_deleted_data['author'] == User.UNKNOWN_STR
            assert student_deleted_data['last_edited_by'] == User.UNKNOWN_STR

        check_is_editable()
        check_default_fields()

    def test_entry_serializer_files(self):
        n_file_fields = 3
        entry = factory.UnlimitedEntry(
            node__journal__assignment__format__templates=[{'type': Field.FILE} for _ in range(n_file_fields)],
        )
        journal = entry.node.journal
        student = journal.author

        # The entry serializer query count is invariant to the number of FILE fields.
        with self.assertNumQueries(self.entry_serializer_base_query_count):
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
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
        with self.assertNumQueries(self.entry_serializer_base_query_count + 2):
            data = EntrySerializer(
                EntrySerializer.setup_eager_loading(Entry.objects.filter(pk=entry.pk))[0],
                context={'user': student}
            ).data

        # JIR data required front end is serialized per entry
        assert data['jir']['processor']['full_name'] == jir.processor.full_name
        assert data['jir']['source']['assignment']['name'] == jir.source.assignment.name
        assert data['jir']['source']['assignment']['course']['abbreviation'] == \
            jir.source.assignment.courses.first().abbreviation
