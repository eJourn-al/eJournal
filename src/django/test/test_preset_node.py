import test.factory as factory
from datetime import date, datetime
from test.utils import api

from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

import VLE.models


class PresetNodeTest(TestCase):
    def test_preset_node_factory(self):
        journal = factory.Journal(entries__n=0)
        format = journal.assignment.format
        template = journal.assignment.format.template_set.first()

        assert VLE.models.PresetNode.objects.filter(format=journal.assignment.format).count() == 0, \
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
        assert journal.node_set.filter(preset=deadline_preset_node, type=VLE.models.Node.ENTRYDEADLINE).exists(), \
            'An entry deadline node has been added to the journal'
        assert journal.node_set.filter(preset=progress_preset_node, type=VLE.models.Node.PROGRESS).exists(), \
            'A progress node has been added to the journal'

    def test_preset_node_constrains(self):
        assignment = factory.Assignment()

        # Display name cannot be empty
        with self.assertRaises(IntegrityError):
            VLE.models.PresetNode.objects.create(
                display_name='',
                type=VLE.models.Node.ENTRYDEADLINE,
                due_date=timezone.now(),
                format=assignment.format,
            )

    def test_preset_node_format_serialization(self):
        assignment = factory.Assignment(format__templates=[{'type': VLE.models.Field.TEXT}])
        template = assignment.format.template_set.first()
        deadline = factory.DeadlinePresetNode(format=assignment.format)
        progress = factory.ProgressPresetNode(format=assignment.format, forced_template=template)

        format_update_dict = factory.AssignmentFormatUpdateParams(assignment=assignment)
        presets = api.update(self, 'formats', params=format_update_dict, user=assignment.author)['format']['presets']

        deadline_fields_to_check = [
            'description',
            'display_name',
            'due_date',
            'id',
            'lock_date',
            'target',
            'type',
            'unlock_date',
        ]

        progress_fields_to_check = [
            'description',
            'display_name',
            'due_date',
            'id',
            'target',
            'type',
        ]

        def check_fields(data, instance, fields):
            for field in fields:
                instance_val = getattr(instance, field)
                if isinstance(instance_val, datetime):
                    instance_val = instance_val.strftime(settings.ALLOWED_DATETIME_FORMAT)
                elif isinstance(instance_val, date):
                    instance_val = instance_val.strftime(settings.ALLOWED_DATE_FORMAT)

                assert data[field] == instance_val, f'Field: {field} not correctly serialized'

        for preset in presets:
            if preset['id'] == deadline.pk:
                check_fields(preset, deadline, fields=deadline_fields_to_check)
                assert preset['template']['id'] == deadline.forced_template.pk

            if preset['id'] == progress.pk:
                check_fields(preset, progress, fields=progress_fields_to_check)
