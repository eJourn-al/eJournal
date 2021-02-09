import test.factory as factory
from copy import deepcopy
from datetime import datetime, timedelta
from test.utils import api
from test.utils.generic_utils import equal_models
from unittest import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

import VLE.utils.file_handling as file_handling
from VLE.models import Field, FileContext, Node, PresetNode
from VLE.serializers import PresetNodeSerializer, TemplateSerializer
from VLE.utils.error_handling import VLEMissingRequiredKey, VLEParamWrongType
from VLE.views.preset_node import _update_attached_files


def _validate_preset_based_on_params(data, params, assignment):
    preset_base_fields = [
        'display_name',
        'type',
        'description',
        'due_date',
        'attached_files',
    ]

    deadline_specific_fields = [
        'unlock_date',
        'lock_date',
        #  NOTE: 'template' is deadline specific, but is a serialized instance -> Checked manually
    ]

    progress_specific_fields = [
        'target',
    ]

    preset = PresetNode.objects.select_related('forced_template').get(format__assignment=assignment, pk=data['id'])

    for field in preset_base_fields:
        assert data[field] == params[field]
    assert all(data[field] == params[field] for field in preset_base_fields), \
        'All base fields of the preset node are correctly updated according to the provided parameters'

    if params['type'] == Node.ENTRYDEADLINE:
        assert all(data[field] == params[field] for field in deadline_specific_fields), \
            'The deadline preset node specific fields are correctly updated according to the provided parameters'
        assert all(data[field] is None for field in progress_specific_fields), \
            'The deadline preset node has no value set specific to a progress preset node'
        assert preset.forced_template.pk == params['template']['id'], 'The forced template is correctly set'

    if params['type'] == Node.PROGRESS:
        assert all(data[field] == params[field] for field in progress_specific_fields), \
            'The progress preset node specific fields are correctly updated according to the provided parameters'
        assert all(data[field] is None for field in deadline_specific_fields), \
            'The progress preset node has no value set specific to a deadline preset node'
        assert not preset.forced_template, 'A progress preset node is not linked to a template'

    for access_id in file_handling.get_access_ids_from_rich_text(params['description']):
        assert FileContext.objects.filter(
            in_rich_text=True,
            assignment=assignment,
            access_id=access_id,
            is_temp=False,
        ).exists(), \
            '''The files part of the preset node's description are correctly updated to no longer reflect their
            initial temporary status'''


class PresetNodeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assignment = factory.Assignment(format__templates=False)
        cls.format = cls.assignment.format
        cls.template = factory.Template(format=cls.format, add_fields=[{'type': Field.TEXT}])
        cls.journal = factory.Journal(assignment=cls.assignment, entries__n=0)
        cls.deadline = factory.DeadlinePresetNode(format=cls.format)
        cls.progress = factory.ProgressPresetNode(format=cls.format, forced_template=cls.template)
        cls.unrelated_user = factory.Student()

    def test_preset_node_factory(self):
        journal = factory.Journal(entries__n=0)
        format = journal.assignment.format
        template = journal.assignment.format.template_set.first()

        assert PresetNode.objects.filter(format=journal.assignment.format).count() == 0, \
            'An assignment format is initialized without preset nodes'
        assert not journal.node_set.exists(), 'Journal is initialized without any nodes'

        deadline_preset_node = factory.DeadlinePresetNode(format=format, forced_template=template)
        assert deadline_preset_node.is_deadline, 'Deadline preset node is of the correct type'
        assert deadline_preset_node.forced_template.pk == template.pk, 'Forced template is correctly set'
        assert deadline_preset_node.display_name == deadline_preset_node.forced_template.name

        progress_preset_node = factory.ProgressPresetNode(format=format)
        assert progress_preset_node.is_progress, 'Progress preset node is of the correct type'
        assert progress_preset_node.target, 'Progress preset node holds a target'

        assert journal.node_set.count() == 2, 'Exactly two nodes have been added to the journal'
        assert journal.node_set.filter(preset=deadline_preset_node, type=Node.ENTRYDEADLINE).exists(), \
            'An entry deadline node has been added to the journal'
        assert journal.node_set.filter(preset=progress_preset_node, type=Node.PROGRESS).exists(), \
            'A progress node has been added to the journal'

    def test_preset_node_constrains(self):
        # Display name cannot be empty
        with self.assertRaises(IntegrityError):
            PresetNode.objects.create(
                display_name='',
                type=Node.ENTRYDEADLINE,
                due_date=timezone.now(),
                format=self.format,
            )

    def test_preset_node_validate(self):
        def test_validate_deadline_preset_node():
            deadline_data = PresetNodeSerializer(
                PresetNodeSerializer.setup_eager_loading(PresetNode.objects.filter(pk=self.deadline.pk)).get(),
                context={'user': self.assignment.author}
            ).data

            # The serializer data should pass validation without any modifications
            PresetNode.validate(deadline_data, self.assignment, self.assignment.author)

            # Validation for a deadline preset node runs validation for all dates
            with mock.patch('VLE.models.PresetNode.validate_unlock_date') as validate_unlock_date, mock.patch(
                'VLE.models.PresetNode.validate_due_date') as validate_due_date, mock.patch(
                    'VLE.models.PresetNode.validate_lock_date') as validate_lock_date:
                PresetNode.validate(deadline_data, self.assignment, self.assignment.author)
                validate_unlock_date.assert_called_with(deadline_data, self.assignment)
                validate_due_date.assert_called_with(deadline_data, self.assignment)
                validate_lock_date.assert_called_with(deadline_data, self.assignment)

            unknown_type = deepcopy(deadline_data)
            unknown_type['type'] = 'unknown'
            self.assertRaises(
                ValidationError, PresetNode.validate, unknown_type, self.assignment, self.assignment.author)

            # An empty display name is not allowed
            empty_name = deepcopy(deadline_data)
            empty_name['display_name'] = ''
            self.assertRaises(ValidationError, PresetNode.validate, empty_name, self.assignment, self.assignment.author)

            # If a file is not correctly uploaded, ask the user to try again
            incorectly_uploaded_attached_file = deepcopy(deadline_data)
            fc = factory.TempFileContext(author=self.assignment.author)
            incorectly_uploaded_attached_file['attached_files'] = [{'id': fc.pk}]
            fc.delete()
            self.assertRaises(
                ValidationError,
                PresetNode.validate, incorectly_uploaded_attached_file, self.assignment, self.assignment.author
            )

            # It is not possible to claim an unrelated file as 'attached'
            unrelated_attached_file = deepcopy(deadline_data)
            unrelated_assignment = factory.Assignment()
            unrelated_fc = factory.RichTextAssignmentDescriptionFileContext(assignment=unrelated_assignment)
            unrelated_attached_file['attached_files'] = [{'id': unrelated_fc.pk}]
            self.assertRaises(
                ValidationError,
                PresetNode.validate, unrelated_attached_file, self.assignment, self.assignment.author
            )

            # You can't claim someone else's temporary file as 'attached'
            someone_elses_temp_fc = deepcopy(deadline_data)
            unrelated_user = factory.Teacher()
            fc = factory.TempFileContext(author=unrelated_user)
            someone_elses_temp_fc['attached_files'] = [{'id': fc.pk}]
            with self.assertRaises(ValidationError) as context:
                PresetNode.validate(someone_elses_temp_fc, self.assignment, self.assignment.author)
            assert 'One or more files recently uploaded are not owned by you.' in context.exception.message

            # An preset node's forced template has to be part of the assignment
            unrelated_template = factory.Template(format=unrelated_assignment.format)
            unrelated_forced_template = deepcopy(deadline_data)
            unrelated_forced_template['template'] = TemplateSerializer(unrelated_template).data
            self.assertRaises(
                ValidationError,
                PresetNode.validate, unrelated_forced_template, self.assignment, self.assignment.author
            )

            required_keys = [
                'display_name',
                'type',
                'description',
                'template',
            ]
            for key in required_keys:
                missing_key = deepcopy(deadline_data)
                missing_key.pop(key)
                self.assertRaises(
                    VLEMissingRequiredKey, PresetNode.validate, missing_key, self.assignment, self.assignment.author)

            missing_due_date = deepcopy(deadline_data)
            missing_due_date['due_date'] = ''
            self.assertRaises(
                ValidationError, PresetNode.validate, missing_due_date, self.assignment, self.assignment.author)

        def test_validate_progress_preset_node():
            self.assignment.due_date = self.assignment.due_date + timedelta(days=2)
            self.assignment.save()

            progress_data = PresetNodeSerializer(
                PresetNodeSerializer.setup_eager_loading(PresetNode.objects.filter(pk=self.progress.pk)).get(),
                context={'user': self.assignment.author}
            ).data

            # The serializer data should pass validation without any modifications
            PresetNode.validate(progress_data, self.assignment, self.assignment.author)

            # Validation for a deadline preset node runs validation for all dates
            with mock.patch('VLE.models.PresetNode.validate_due_date') as validate_due_date:
                PresetNode.validate(progress_data, self.assignment, self.assignment.author)
                validate_due_date.assert_called_with(progress_data, self.assignment)

            # Target should be positive
            target_less_than_zero = deepcopy(progress_data)
            target_less_than_zero['target'] = -1
            self.assertRaises(
                ValidationError, PresetNode.validate, target_less_than_zero, self.assignment, self.assignment.author)

            # A progress preset node's goal should not exceed the points possible of the assignment
            target_exceeds_assignment_max = deepcopy(progress_data)
            target_exceeds_assignment_max['target'] = self.assignment.points_possible + 1
            self.assertRaises(
                ValidationError,
                PresetNode.validate, target_exceeds_assignment_max, self.assignment, self.assignment.author
            )

            # The following missing keys should raise a missing key error
            required_keys = [
                'display_name',
                'type',
                'description',
                'target',
            ]
            for key in required_keys:
                missing_key = deepcopy(progress_data)
                missing_key.pop(key)
                self.assertRaises(
                    VLEMissingRequiredKey, PresetNode.validate, missing_key, self.assignment, self.assignment.author)

            # Due date is required, but should yield validation error (more user friendly) as warning
            missing_due_date = deepcopy(progress_data)
            missing_due_date['due_date'] = ''
            self.assertRaises(
                ValidationError, PresetNode.validate, missing_due_date, self.assignment, self.assignment.author)

            # No deadline should exist with a higher points total, that comes before the provided due date
            earlier_higher_target = deepcopy(progress_data)
            earlier_higher_target_progress = factory.ProgressPresetNode(
                target=self.progress.target + 1,
                due_date=self.progress.due_date - timedelta(days=1),
                format=self.format,
            )
            with self.assertRaises(ValidationError) as context:
                PresetNode.validate(earlier_higher_target, self.assignment, self.assignment.author)
            assert earlier_higher_target_progress.display_name in context.exception.message, (
                'Progress goals are ordered by due date, and no higher target comes before the previous. If it does,'
                ' the user is informed which deadlines do'
            )
            earlier_higher_target_progress.delete()
            # Unless we update an existing preset
            earlier_higher_target['due_date'] = (datetime.strptime(
                earlier_higher_target['due_date'],
                settings.ALLOWED_DATETIME_FORMAT,
            ) - timedelta(days=1)).strftime(settings.ALLOWED_DATETIME_FORMAT)
            earlier_higher_target['target'] = earlier_higher_target['target'] + 1
            PresetNode.validate(earlier_higher_target, self.assignment, self.assignment.author, old=self.progress)

            # No deadline should exist with a lower points total, that comes after the provided due date
            later_lower_target = deepcopy(progress_data)
            later_lower_target_progress = factory.ProgressPresetNode(
                target=self.progress.target - 1,
                due_date=self.progress.due_date + timedelta(days=1),
                format=self.format,
            )
            with self.assertRaises(ValidationError) as context:
                PresetNode.validate(later_lower_target, self.assignment, self.assignment.author)
            assert later_lower_target_progress.display_name in context.exception.message, (
                'Progress goals are ordered by due date, and no lower target comes after the previous. If it does,'
                ' the user is informed which deadlines do'
            )
            later_lower_target_progress.delete()
            # Unless we update an existing preset
            later_lower_target['due_date'] = (datetime.strptime(
                later_lower_target['due_date'],
                settings.ALLOWED_DATETIME_FORMAT,
            ) + timedelta(days=1)).strftime(settings.ALLOWED_DATETIME_FORMAT)
            later_lower_target['target'] = later_lower_target['target'] - 1
            PresetNode.validate(later_lower_target, self.assignment, self.assignment.author, old=self.progress)

        test_validate_deadline_preset_node()
        test_validate_progress_preset_node()

    def test_preset_node_validate_dates(self):
        assignment = factory.Assignment()
        deadline = factory.DeadlinePresetNode(format=assignment.format)

        one_second = timedelta(seconds=1)

        def reset_preset_node_dates(preset):
            preset.unlock_date = assignment.unlock_date
            preset.due_date = assignment.due_date
            preset.lock_date = assignment.lock_date

        # Default state should pass validation
        reset_preset_node_dates(deadline)
        PresetNode.validate_unlock_date(PresetNodeSerializer(deadline).data, assignment)
        PresetNode.validate_due_date(PresetNodeSerializer(deadline).data, assignment)
        PresetNode.validate_lock_date(PresetNodeSerializer(deadline).data, assignment)

        def test_unlock_date():
            # Assignment unlocks after unlock date
            deadline.unlock_date = assignment.unlock_date - one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_unlock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Assignment is due before unlock date
            deadline.unlock_date = assignment.due_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_unlock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Assignment is locked before unlock date
            deadline.unlock_date = assignment.lock_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_unlock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline locks before unlock date
            deadline.unlock_date = deadline.lock_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_unlock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

        def test_due_date():
            empty_due_date = PresetNodeSerializer(deadline).data
            empty_due_date['due_date'] = ''
            self.assertRaises(ValidationError, PresetNode.validate_due_date, empty_due_date, assignment)

            incorrect_format_due_date = PresetNodeSerializer(deadline).data
            incorrect_format_due_date['due_date'] = '2000a-10-10'
            self.assertRaises(VLEParamWrongType, PresetNode.validate_due_date, incorrect_format_due_date, assignment)

            # Deadline is due before assignment unlocks
            deadline.due_date = assignment.unlock_date - one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_due_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline is due after the assignment is due
            deadline.due_date = assignment.due_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_due_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline is due after the assignment locks
            deadline.due_date = assignment.lock_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_due_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline is due before it unlocks.
            deadline.due_date = deadline.unlock_date - one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_due_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline is due after it locks
            deadline.due_date = deadline.lock_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_due_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

        def test_lock_date():
            # Deadline locks before the assignment unlocks
            deadline.lock_date = assignment.unlock_date - one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_lock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline locks after the assignment locks
            deadline.lock_date = assignment.lock_date + one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_lock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

            # Deadline locks before it unlocks
            deadline.lock_date = deadline.unlock_date - one_second
            self.assertRaises(
                ValidationError, PresetNode.validate_lock_date, PresetNodeSerializer(deadline).data, assignment)
            reset_preset_node_dates(deadline)

        test_unlock_date()
        test_due_date()
        test_lock_date()

    def test_preset_node__update_attached_files(self):
        deadline = factory.DeadlinePresetNode(format=self.format, n_att_files=2)
        att_fc_1 = deadline.attached_files.first()
        att_fc_2 = deadline.attached_files.last()

        other_user = factory.Teacher()
        other_user_temp_file = factory.TempFileContext(author=other_user)

        new_att_file = factory.TempFileContext(author=self.assignment.author)

        new_att_file_ids = [att_fc_1.pk, new_att_file.pk, other_user_temp_file.pk]
        _update_attached_files(deadline, self.assignment.author, new_att_file_ids)

        assert not FileContext.objects.filter(pk=att_fc_2.pk).exists(), 'No longer attached files should be removed'
        assert deadline.attached_files.filter(pk=att_fc_1.pk).exists(), \
            'Files which were attached and still part of the new ids should remain'
        assert deadline.attached_files.filter(pk=new_att_file.pk, is_temp=False, assignment=self.assignment).exists(), \
            'Temporary files part of the new ids are correctly attached and linked'

        assert deadline.attached_files.filter(pk=other_user_temp_file.pk).exists(), \
            'A user can only claim ones own temporary files (to attach).'
        other_user_temp_file.refresh_from_db()
        assert other_user_temp_file.author == other_user, \
            'Other users temporary file author remains unchanged despite being part of the list of new ids'
        assert other_user_temp_file.is_temp, \
            'Other users temporary file remains temporary despite being part of the list of new ids'

    def test_preset_node_list(self):
        with mock.patch('VLE.models.User.can_view') as can_view_mock:
            resp = api.get(
                self, 'preset_nodes', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            can_view_mock.assert_called_with(self.assignment), \
                'PresetNode list permission depends on can view assignment'
        api.get(
            self, 'preset_nodes', params={'assignment_id': self.assignment.pk}, user=self.unrelated_user, status=403)

        presets = self.assignment.format.presetnode_set.all()
        preset_set = set(presets.values_list('pk', flat=True))
        assert all(preset['id'] in preset_set for preset in resp['presets']), \
            'All serialized preset nodes belong to the provided assignment id'

        presets_ordered = list(presets)
        presets_ordered.sort(key=lambda x: x.due_date)
        presets_ordered = [preset.pk for preset in presets_ordered]
        resp_presets_order = [data['id'] for data in resp['presets']]
        assert presets_ordered == resp_presets_order, 'Serialized preset nodes are ordered by due date'

    def test_preset_node_create(self):
        deadline_creation_params = factory.DeadlinePresetNodeCreationParams(
            format=self.format, forced_template=self.template, n_files_in_description=1)
        deadline_creation_params['target'] = 10  # This should be ignored during creation

        # Creating a preset node depends on the permission 'can_edit_assignment', and validation should run
        with mock.patch('VLE.models.User.check_permission') as check_permission_mock, mock.patch(
                'VLE.models.PresetNode.validate') as validate_mock:
            resp = api.create(self, 'preset_nodes', params=deadline_creation_params, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)
            validate_mock.assert_called_with(
                deadline_creation_params, assignment=self.assignment, user=self.assignment.author)

        _validate_preset_based_on_params(resp['preset'], deadline_creation_params, self.assignment)

        # A progress preset node holds different fields than a deadline despite being the same model.
        progress_creation_params = factory.ProgressPresetNodeCreationParams(
            format=self.format, n_files_in_description=1)
        progress_creation_params['template'] = {'id': self.template.pk}  # Should be ignored during creation

        resp = api.create(self, 'preset_nodes', params=progress_creation_params, user=self.assignment.author)
        _validate_preset_based_on_params(resp['preset'], progress_creation_params, self.assignment)

    def test_preset_node_update(self):
        deadline = factory.DeadlinePresetNode(format=self.format)
        update_params = PresetNodeSerializer(
            PresetNodeSerializer.setup_eager_loading(
                PresetNode.objects.filter(pk=deadline.pk)
            ).get()
        ).data

        # Updating a preset node depends on the permission 'can_edit_assignment', and validation should run
        with mock.patch('VLE.models.User.check_permission') as check_permission_mock, mock.patch(
                'VLE.models.PresetNode.validate') as validate_mock:
            resp = api.update(self, f'preset_nodes/{deadline.pk}/', params=update_params, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)
            validate_mock.assert_called_with(
                update_params, assignment=self.assignment, user=self.assignment.author, old=deadline)

        # Cast rest_framework.utils.serializer_helpers.ReturnDict to dict for equal models check
        update_params = dict(update_params)
        update_params['template'] = dict(update_params['template'])
        assert equal_models(update_params, resp['preset']), \
            'Without any changes to the update params, the preset should be unchanged after an update.'

        # Make many changes, including new fc in description, fields which do not belong to a deadline, a new template
        params = deepcopy(update_params)
        fc = factory.TempFileContext(author=self.assignment.author)
        params['description'] += f'<img src="{fc.download_url(access_id=fc.access_id)}"/>'
        params['target'] = 3
        params['display_name'] = 'Something new'
        new_template = factory.TextTemplate(format=self.format)
        params['template'] = {'id': new_template.pk}
        resp = api.update(self, f'preset_nodes/{deadline.pk}/', params=params, user=self.assignment.author)
        _validate_preset_based_on_params(resp['preset'], params, self.assignment)

        update_type = deepcopy(resp['preset'])
        update_type['type'] = Node.PROGRESS
        resp = api.update(self, f'preset_nodes/{deadline.pk}/', params=params, user=self.assignment.author)
        assert resp['preset']['type'] == deadline.type, 'Updating the type of an existing deadline is not possible'
        # Type does not update according to params, this should fail an assert
        self.assertRaises(
            AssertionError, _validate_preset_based_on_params, resp['preset'], update_type, self.assignment)

        # Make some changes, this time updating a preset node of type progress
        progress = factory.ProgressPresetNode(format=self.format)
        params = PresetNodeSerializer(
            PresetNodeSerializer.setup_eager_loading(
                PresetNode.objects.filter(pk=progress.pk)
            ).get()
        ).data
        params['display_name'] = 'New name'
        params['lock_date'] = datetime.now().strftime(settings.ALLOWED_DATETIME_FORMAT)
        resp = api.update(self, f'preset_nodes/{progress.pk}/', params=params, user=self.assignment.author)
        _validate_preset_based_on_params(resp['preset'], params, self.assignment)

    def test_preset_node_delete(self):
        def test_unused_preset_node_delete():
            deadline = factory.DeadlinePresetNode(format=self.format)

            with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
                resp = api.delete(self, 'preset_nodes', params={'pk': deadline.pk}, user=self.assignment.author)
                check_permission_mock.assert_called_with('can_edit_assignment', deadline.format.assignment)

            assert deadline.display_name in resp['description'], \
                'The deleted preset node\'s display name is part of the success message'
            assert not PresetNode.objects.filter(pk=deadline.pk).exists(), \
                'The preset node is successfully removed from the DB'
            assert not Node.objects.filter(journal=self.journal, preset=deadline).exists(), \
                'Any journal nodes created due to the preset node are also deleted if they hold no entry'

        def test_used_preset_node_delete():
            # Test usage via an unlimited entry
            deadline = factory.DeadlinePresetNode(format=self.format, forced_template=self.template)
            node = self.journal.node_set.get(preset=deadline)
            entry = factory.PresetEntry(node=node)

            api.delete(self, 'preset_nodes', params={'pk': deadline.pk}, user=self.assignment.author)
            assert not PresetNode.objects.filter(pk=deadline.pk).exists(), \
                'The preset node is successfully removed from the DB'

            entry.refresh_from_db()
            assert entry.node, \
                'The node of the entry created for the deadline still exists, despite the deadline having been deleted'
            assert not entry.node.preset, 'The deadline of the entry node is removed and correctly set to None'

        test_unused_preset_node_delete()
        test_used_preset_node_delete()
