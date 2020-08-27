import test.factory as factory
from test.utils import api

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

import VLE.models


class NodeTest(TestCase):
    def setUp(self):
        self.journal = factory.Journal()
        self.student = self.journal.authors.first().user
        self.teacher = self.journal.assignment.courses.first().author

    def test_preset_node_factory(self):
        journal = factory.Journal(entries__n=0)
        format = journal.assignment.format
        template = journal.assignment.format.template_set.first()

        assert VLE.models.PresetNode.objects.filter(format=journal.assignment.format).count() == 0, \
            'An assignment format is initialized without preset nodes'
        assert not journal.node_set.exists(), 'Journal is initialized without any nodes'

        deadline_preset_node = factory.DeadlinePresetNode(format=format, forced_template=template)
        assert deadline_preset_node.type == VLE.models.Node.ENTRYDEADLINE, 'Deadline preset node is of the correct type'
        assert deadline_preset_node.forced_template.pk == template.pk, 'Forced template is correctly set'

        progress_preset_node = factory.ProgressPresetNode(format=format)
        assert progress_preset_node.type == VLE.models.Node.PROGRESS, 'Progress preset node is of the correct type'
        assert progress_preset_node.target, 'Progress preset node holds a target'

        assert journal.node_set.count() == 2, 'Exactly two nodes have been added to the journal'
        assert journal.node_set.filter(preset=deadline_preset_node, type=VLE.models.Node.ENTRYDEADLINE).exists(), \
            'An entry deadline node has been added to the journal'
        assert journal.node_set.filter(preset=progress_preset_node, type=VLE.models.Node.PROGRESS).exists(), \
            'A progress node has been added to the journal'

    def test_node_validation(self):
        journal = factory.Journal(entries__n=0)
        assignment = journal.assignment
        deadline = factory.DeadlinePresetNode(format=assignment.format)

        entry = factory.PresetEntry(node__preset=deadline, node__journal=journal)
        self.assertRaises(ValidationError, factory.PresetEntry, node=entry.node)
        self.assertRaises(IntegrityError, VLE.models.Node.objects.create, preset=deadline, journal=journal)

    def test_get(self):
        api.get(self, 'nodes', params={'journal_id': self.journal.pk}, user=self.student)
        api.get(self, 'nodes', params={'journal_id': self.journal.pk}, user=factory.Admin())
        api.get(self, 'nodes', params={'journal_id': self.journal.pk}, user=factory.Teacher(), status=403)
        api.get(self, 'nodes', params={'journal_id': self.journal.pk}, user=self.teacher)
