import datetime
import test.factory as factory
from test.utils import api

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

import VLE.models
from VLE.utils.error_handling import VLEProgrammingError


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
        assert deadline_preset_node.is_deadline, 'Deadline preset node is of the correct type'
        assert deadline_preset_node.forced_template.pk == template.pk, 'Forced template is correctly set'

        progress_preset_node = factory.ProgressPresetNode(format=format)
        assert progress_preset_node.is_progress, 'Progress preset node is of the correct type'
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

    def test_node_properties(self):
        assignment = factory.Assignment()
        journal = factory.Journal(assignment=assignment, entries__n=0)
        progress = factory.ProgressPresetNode(format=assignment.format)
        deadline = factory.DeadlinePresetNode(format=assignment.format)

        assert progress.is_progress and progress.type == VLE.models.Node.PROGRESS
        assert deadline.is_deadline and deadline.type == VLE.models.Node.ENTRYDEADLINE

        entry = factory.UnlimitedEntry(node__journal=journal)
        deadline = factory.PresetEntry(node__journal=journal, node__preset=deadline)
        progress_node = journal.node_set.get(preset=progress)

        assert entry.node.is_entry and entry.node.type == VLE.models.Node.ENTRY
        assert deadline.node.is_deadline and deadline.node.type == VLE.models.Node.ENTRYDEADLINE
        assert progress_node.is_progress and progress_node.type == VLE.models.Node.PROGRESS

    def test_open_deadline(self):
        assignment = factory.Assignment()
        journal = factory.Journal(assignment=assignment, entries__n=0)
        journal = VLE.models.Journal.objects.get(pk=journal.pk)
        progress = factory.ProgressPresetNode(
            format=assignment.format, due_date=timezone.now() + datetime.timedelta(days=1), target=3)
        deadline = factory.DeadlinePresetNode(
            format=assignment.format, due_date=timezone.now() + datetime.timedelta(days=1))

        entry = factory.PresetEntry(node__journal=journal, node__preset=deadline)
        node = entry.node
        assert not node.open_deadline(), 'Node holds an entry so the deadline is not outstanding'
        entry.delete()
        node.refresh_from_db()
        assert node.open_deadline(), 'The nodes preset is still in the future'
        node.preset.due_date = timezone.now() - datetime.timedelta(days=1)
        assert not node.open_deadline(), 'No entry and deadline has passed'

        assert journal.grade == 0
        node = journal.node_set.get(preset=progress)
        assert node.open_deadline(), 'Grade not met but due date not passed'
        journal.grade = 3
        node.preset.due_date = timezone.now() - datetime.timedelta(days=1)
        assert not node.open_deadline(), 'Due date passed but progress goal met'
        journal.grade = 2.99
        assert not node.open_deadline(), 'Due date passed and progress goal unmet'
        journal.grade = 3
        node.preset.due_date = timezone.now() + datetime.timedelta(days=1)
        assert node.open_deadline(grade=2), 'Provided grade takes presedence over journal grade'

        entry = factory.UnlimitedEntry(node__journal=journal)
        assert not entry.node.open_deadline(), 'Unlimited entry has no deadline to begin with'

        node.type = '?'
        self.assertRaises(VLEProgrammingError, node.open_deadline)
