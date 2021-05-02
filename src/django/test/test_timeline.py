"""
test_timeline.py.

Test all about the timeline.
"""
import datetime
import test.factory as factory
from test.utils.performance import assert_num_queries_less_than

from django.test import TestCase
from django.utils import timezone

import VLE.factory
import VLE.timeline as timeline
from VLE.models import Field, Journal, Node
from VLE.serializers import EntrySerializer, TemplateSerializer


class TimelineTests(TestCase):
    def setUp(self):
        self.course = factory.Course()
        self.teacher = self.course.author
        self.student = factory.Student()

        assignment = VLE.factory.make_assignment(
            name='name', description='description', author=self.teacher, courses=[self.course])
        f_colloq = assignment.format
        self.template = f_colloq.template_set.first()

        self.deadline_preset = factory.DeadlinePresetNode(
            format=f_colloq,
            due_date=datetime.datetime.now() - datetime.timedelta(days=10),
            forced_template=f_colloq.template_set.first(),
        )
        self.progress_preset = factory.ProgressPresetNode(
            format=f_colloq,
            due_date=datetime.datetime.now() + datetime.timedelta(days=10),
            target=10,
        )

        self.journal = factory.Journal(assignment=assignment, ap__user=self.student)
        self.journal = Journal.objects.get(pk=self.journal.pk)

        # See respective tests for info
        self.template_serializer_query_count = 1 + len(TemplateSerializer.prefetch_related)
        self.entry_serializer_default_query_count = (
            1
            + len(EntrySerializer.prefetch_related)
            + len(TemplateSerializer.prefetch_related)
        )

    def test_get_add_node(self):
        journal = factory.Journal(entries__n=0)

        with self.assertNumQueries(self.template_serializer_query_count):
            data = timeline.get_add_node(journal)

        assert data['type'] == VLE.models.Node.ADDNODE
        assert data['id'] == -1

    def test_get_entry_node(self):
        entry = factory.UnlimitedEntry(node__journal__assignment__format__templates=[{'type': Field.TEXT}])
        journal = entry.node.journal
        node = entry.node
        student = journal.author

        # With the node in memory, serializing the entry node should only cost queries for the entry serializer.
        with self.assertNumQueries(7):
            data = timeline.get_entry_node(journal, node, student)

        assert data['type'] == node.type
        assert data['id'] == node.id
        assert data['jID'] == journal.pk

    def test_get_progress(self):
        assignment = factory.Assignment()
        journal = factory.Journal(assignment=assignment)
        progress_preset = factory.ProgressPresetNode(format=assignment.format)
        node = VLE.models.Node.objects.filter(
            preset=progress_preset, journal=journal).prefetch_related('preset', 'preset__attached_files').first()

        # Provided the preset is prefetched, serialization should occur in memory
        with self.assertNumQueries(0):
            data = timeline.get_progress(journal, node)

        assert data['description'] == node.preset.description
        assert data['type'] == node.type
        assert data['id'] == node.pk
        assert data['jID'] == node.journal.pk
        assert data['due_date'] == node.preset.due_date
        assert data['target'] == node.preset.target

    def test_get_deadline(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT} for _ in range(3)])
        journal = factory.Journal(assignment=assignment)
        template = assignment.format.template_set.first()
        deadline = factory.DeadlinePresetNode(forced_template=template, format=assignment.format)
        node = journal.node_set.get(preset=deadline)
        preset_entry = factory.PresetEntry(node=node)
        author = preset_entry.node.journal.author

        # No additional queries are performed besides the nested serializer queries plus fetching the attached files
        with assert_num_queries_less_than(
                self.template_serializer_query_count + self.entry_serializer_default_query_count + 1):
            data = timeline.get_deadline(journal, node, author)

        assert data['description'] == node.preset.description
        assert data['type'] == node.type
        assert data['id'] == node.id
        assert data['jID'] == journal.pk
        assert data['unlock_date'] == node.preset.unlock_date
        assert data['due_date'] == node.preset.due_date
        assert data['lock_date'] == node.preset.lock_date
        assert not data['deleted_preset'], 'Preset is not deleted, so flag should also be false'

        # Test if get_entry_node does not crash when preset is deleted
        node.preset.delete()
        node.refresh_from_db()
        data = timeline.get_deadline(journal, node, author)
        assert data['deleted_preset'], 'Preset is deleted, so flag should also be true'

        resp = timeline.get_deadline(journal, None, author)
        assert resp is None, 'Not providing a node should not crash get_deadline and simply return None back'

    def test_get_nodes(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        journal = factory.LtiJournal(entries__n=0, assignment=assignment)
        journal = Journal.objects.get(pk=journal.pk)
        student = journal.author
        factory.UnlimitedEntry(node__journal=journal)

        template = journal.assignment.format.template_set.first()
        deadline = factory.DeadlinePresetNode(format=assignment.format, forced_template=template)
        deadline_node = journal.node_set.get(preset=deadline)
        factory.PresetEntry(node=deadline_node)

        factory.ProgressPresetNode(format=journal.assignment.format)

        # NOTE: Does not grow linearly, see Z#1435
        data = timeline.get_nodes(journal, user=student)

        assert data[-1]['type'] == Node.PROGRESS, 'Progress goal should be the last timeline node'
        assert data[-2]['type'] == Node.ADDNODE, 'Add node should be positioned before the final progress goal'

        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        journal = factory.LtiJournal(entries__n=1, assignment=assignment)
        journal = Journal.objects.get(pk=journal.pk)
        student = journal.author

        data = timeline.get_nodes(journal, user=student)
        assert data[-1]['type'] == Node.ADDNODE, \
            'Add node should be positioned as the final node if no progress goals are set'

        assignment.due_date = timezone.now()
        assignment.lock_date = timezone.now()
        assignment.save()
        journal = Journal.objects.get(pk=journal.pk)
        data = timeline.get_nodes(journal, user=student)
        for n in data:
            assert n['type'] != Node.ADDNODE, 'When the assignment is locked no add node should be serialized'
