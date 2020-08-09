import test.factory as factory
from datetime import date, timedelta
from test.utils import api

from django.test import TestCase

from VLE.models import Entry, Field, Node
from VLE.utils import generic_utils as utils
from VLE.utils.error_handling import VLEPermissionError


class EntryAPITest(TestCase):
    def setUp(self):
        self.admin = factory.Admin()
        self.g_assignment = factory.GroupAssignment()
        self.journal = factory.Journal(assignment=self.g_assignment)
        self.student = self.journal.authors.first().user
        self.journal2 = factory.Journal(assignment=self.journal.assignment)
        self.student2 = self.journal2.authors.first().user
        self.teacher = self.journal.assignment.courses.first().author
        APteacher = factory.AssignmentParticipation(user=self.teacher)
        self.journal_teacher = factory.Journal(assignment=self.journal.assignment)
        self.journal_teacher.add_author(APteacher)
        self.journal_teacher.save()
        # self.teacher = self.journal_teacher.authors.first().user
        self.format = self.journal.assignment.format
        self.template = factory.Template(format=self.format)
        factory.Template(format=self.format)
        factory.Template(format=self.format)

        self.valid_create_params = {
            'journal_id': self.journal.pk,
            'template_id': self.template.pk,
            'content': []
        }
        fields = Field.objects.filter(template=self.template)
        self.valid_create_params['content'] = [{'data': 'test data', 'id': field.id} for field in fields]

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
        create_params['content'] = [{
            'data': 'test title',
            'id': self.valid_create_params['content'][0]['id']
        }]
        api.create(self, 'entries', params=create_params, user=self.student, status=400)

        # Check for assignment locked
        self.journal.assignment.lock_date = date.today() - timedelta(1)
        self.journal.assignment.save()
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(node__journal=self.journal).first(),
        )
        api.create(self, 'entries', params=create_params, user=self.student, status=403)
        self.journal.assignment.lock_date = date.today() + timedelta(1)
        self.journal.assignment.save()

        # Check if template for other assignment wont work
        create_params = self.valid_create_params.copy()
        alt_journal = factory.Journal()
        template = factory.Template(format=alt_journal.assignment.format)
        create_params['template_id'] = template.pk
        api.create(self, 'entries', params=create_params, user=self.student, status=403)

        # Teachers shouldn't be able to make entries on their own journal
        self.assertRaises(
            VLEPermissionError,
            self.teacher.check_can_edit,
            Entry.objects.filter(node__journal=self.journal).first(),
        )
        teacher_params = self.valid_create_params.copy()
        teacher_params['journal_id'] = self.journal_teacher.pk
        api.create(self, 'entries', params=teacher_params, user=self.teacher, status=403)

        # Entries can no longer be created if the LTI link is outdated (new active uplink)
        assignment_old_lti_id = self.journal.assignment.active_lti_id
        self.journal.assignment.active_lti_id = 'new_lti_id_1'
        self.journal.assignment.save()
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(node__journal=self.journal).first(),
        )
        resp = api.create(self, 'entries', params=self.valid_create_params, user=self.student, status=403)
        assert resp['description'] == self.journal.outdated_link_warning_msg, 'When the active LTI uplink is outdated' \
            ' no more entries can be created.'
        self.journal.assignment.active_lti_id = assignment_old_lti_id
        self.journal.assignment.save()

        # TODO: Test for entry bound to entrydeadline
        # TODO: Test with file upload
        # TODO: Test added index

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
                'journal_id': self.journal.pk,
                'template_id': template.pk,
            }

            # If valid input is defined for this field type, creating an entry should be succesful.
            if field.type in valid_content:
                create_params['content'] = [{
                    'id': field.pk,
                    'data': valid_content[field.type]
                }]
                api.create(self, 'entries', params=create_params, user=self.student)

            # If invalid input is defined for this field type, creating an entry should fail.
            if field.type in invalid_content:
                create_params['content'] = [{
                    'id': field.pk,
                    'data': invalid_content[field.type]
                }]
                api.create(self, 'entries', params=create_params, user=self.student, status=400)

    def test_required_and_optional(self):
        # Creation with only required params should work
        required_only_creation = {
            'journal_id': self.journal.pk,
            'template_id': self.template.pk,
            'content': []
        }
        fields = Field.objects.filter(template=self.template)
        required_only_creation['content'] = [{'data': 'test data', 'id': field.id}
                                             for field in fields if field.required]
        api.create(self, 'entries', params=required_only_creation, user=self.student)

        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        params = {
            'pk': entry['id'],
            'content': [{
                'id': field['field'],
                'data': ''
            } for field in entry['content']]
        }
        # Student should always provide required parameters
        api.update(self, 'entries', params=params.copy(), user=self.student, status=400)

        # Student should be able to update only the required fields, leaving the optinal fields empty
        factory.Field(template=self.template, required=False, type=Field.TEXT)
        fields = self.template.field_set.all()
        for empty_value in [None, '']:
            params = {
                'pk': entry['id'],
                'content': [{
                    'id': field.pk,
                    'data': 'filled' if field.required else empty_value
                } for field in fields]
            }
            resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
            assert len(resp['content']) == self.template.field_set.count(), \
                'Response should have emptied the optional fields, not deleted'
            assert any([c['data'] is None for c in resp['content']]), \
                'Response should have emptied the optional fields, not deleted'
        # Student should be able to edit an optinal field
        params = {
            'pk': entry['id'],
            'content': [{
                'id': field.pk,
                'data': 'filled'
            } for field in fields]
        }
        resp = api.update(self, 'entries', params=params.copy(), user=self.student)['entry']
        assert len(resp['content']) == self.template.field_set.count() and resp['content'][2]['data'] == 'filled', \
            'Response should have filled the optional fields'

    def test_optional_fields_are_none(self):
        # As all fields are optional, data None should also work
        all_types = factory.TemplateAllTypes(format=self.format)
        fields = Field.objects.filter(template=all_types)
        fields.update(required=False)
        empty_create_params = {
            'journal_id': self.journal.pk,
            'template_id': all_types.pk,
            'content': []
        }
        empty_create_params['content'] = [{'data': None, 'id': field.id} for field in fields]
        resp = api.create(self, 'entries', params=empty_create_params, user=self.student)['entry']
        api.update(self, 'entries', params={**empty_create_params, 'pk': resp['id']}, user=self.student)

    def test_update_entry(self):
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']

        params = {
            'pk': entry['id'],
            'content': [{
                'id': field['field'],
                'data': field['data']
            } for field in entry['content']]
        }

        api.update(self, 'entries', params=params.copy(), user=self.student)

        # Check if last_edited_by gets set to the correct other user
        last_edited = factory.AssignmentParticipation(assignment=self.journal.assignment)
        self.journal.add_author(last_edited)
        resp = api.update(self, 'entries', params=params.copy(), user=last_edited.user)['entry']
        assert resp['last_edited_by'] == last_edited.user.full_name

        # Other users shouldn't be able to update an entry
        api.update(self, 'entries', params=params.copy(), user=self.teacher, status=403)

        # Check for assignment locked
        self.journal.assignment.lock_date = date.today() - timedelta(1)
        self.journal.assignment.save()
        api.update(self, 'entries', params=params.copy(), user=self.student, status=403)
        self.journal.assignment.lock_date = date.today() + timedelta(1)
        self.journal.assignment.save()

        # Entries can no longer be edited if the LTI link is outdated (new active uplink)
        assignment_old_lti_id = self.journal.assignment.active_lti_id
        self.journal.assignment.active_lti_id = 'new_lti_id_2'
        self.journal.assignment.save()
        resp = api.update(self, 'entries', params=params.copy(), user=self.student, status=403)
        assert resp['description'] == self.journal.outdated_link_warning_msg, 'When the active LTI uplink is outdated' \
            ' no more entries can be created.'
        self.journal.assignment.active_lti_id = assignment_old_lti_id
        self.journal.assignment.save()

        # Grade and publish an entry
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.student,
                   status=403)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.teacher)

        # Shouldn't be able to edit entries after grade
        self.assertRaises(
            VLEPermissionError,
            self.student.check_can_edit,
            Entry.objects.filter(node__journal=self.journal).first(),
        )
        api.update(self, 'entries', params=params.copy(), user=self.student, status=400)

        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': False}, user=self.teacher)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True}, user=self.teacher)
        api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 5, 'published': True},
                   user=factory.Teacher(), status=403)

        # Check if a published entry cannot be unpublished
        api.create(self, 'grades', params={'entry_id': entry['id'], 'published': False}, user=self.teacher, status=400)

    def test_destroy(self):
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
        journal.assignment.active_lti_id = 'new_lti_id_3'
        journal.assignment.save()

        resp = api.delete(self, 'entries', params={'pk': entry.pk}, user=self.student, status=403)
        assert resp['description'] == journal.outdated_link_warning_msg, 'When the active LTI uplink is outdated' \
            ' no more entries can be created.'
        journal.assignment.active_lti_id = assignment_old_lti_id
        journal.assignment.save()

        # Only superusers should be allowed to delete locked entries
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        self.journal.assignment.lock_date = date.today() - timedelta(1)
        self.journal.assignment.save()
        api.delete(self, 'entries', params={'pk': entry['id']}, user=self.student, status=403)
        api.delete(self, 'entries', params={'pk': entry['id']}, user=factory.Admin())

    def test_grade(self):
        entry = api.create(self, 'entries', params=self.valid_create_params, user=self.student)['entry']
        entry = api.create(self, 'grades', params={'entry_id': entry['id'], 'grade': 1, 'published': True},
                           user=self.teacher)['entry']
        assert entry['grade']['grade'] == 1
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
        entrydeadline = factory.EntrydeadlineNode(format=self.format)

        node = Node.objects.get(preset=entrydeadline, journal=self.journal)
        node_student2 = Node.objects.get(preset=entrydeadline, journal=self.journal2)
        create_params = {
            'journal_id': self.journal.pk,
            'template_id': entrydeadline.forced_template.pk,
            'content': [],
            'node_id': node.pk
        }

        fields = Field.objects.filter(template=entrydeadline.forced_template)
        create_params['content'] = [{'data': 'test data', 'id': field.pk} for field in fields]
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
