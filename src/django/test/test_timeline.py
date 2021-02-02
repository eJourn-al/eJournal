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
from VLE.models import Field, Journal, Node, Role
from VLE.serializers import EntrySerializer
from VLE.utils import generic_utils as utils


class TimelineTests(TestCase):
    """Test the timeline."""

    def setUp(self):
        """Setup."""
        self.student = factory.Student()

        f_colloq = VLE.factory.make_default_format()

        self.deadlineentry = factory.DeadlinePresetNode(
            format=f_colloq, due_date=datetime.datetime.now() - datetime.timedelta(days=10),
            forced_template=f_colloq.template_set.first())
        self.progressnode = factory.ProgressPresetNode(
            format=f_colloq, due_date=datetime.datetime.now() + datetime.timedelta(days=10), target=10)

        self.template = f_colloq.template_set.first()

        self.course = factory.Course()
        self.teacher = self.course.author
        factory.Participation(
            user=self.student, course=self.course, role=Role.objects.get(course=self.course, name='Student'))

        assignment = factory.Assignment(author=self.teacher, format=f_colloq, courses=[self.course])

        self.journal = Journal.objects.get(assignment=assignment, authors__user=self.student)

        # See respective tests for info
        self.template_serializer_query_count = 2
        self.entry_serializer_default_query_count = len(EntrySerializer.prefetch_related) + 1

    def test_due_date_format(self):
        """Test if the due date is correctly formatted."""
        due_date = datetime.date.today()

        format = VLE.factory.make_default_format()
        format.save()
        preset = factory.DeadlinePresetNode(
            format=format, due_date=due_date, forced_template=format.template_set.first())

        self.assertEqual(due_date, preset.due_date)

        assignment = factory.Assignment(author=self.teacher, format=format, courses=[self.course])
        journal = Journal.objects.get(assignment=assignment, authors__user=self.student)

        self.assertTrue(journal.node_set.get(preset__due_date=due_date))

    def test_sorted(self):
        """Test is the sort function works."""
        node = VLE.factory.make_node(self.journal)
        VLE.factory.make_entry(self.template, self.journal.authors.first().user, node)
        nodes = utils.get_sorted_nodes(self.journal)

        self.assertEqual(nodes[0].preset, self.deadlineentry)
        self.assertEqual(nodes[1], node)
        self.assertEqual(nodes[2].preset, self.progressnode)

    def test_json(self):
        """Test is the to dict function works correctly."""
        node = VLE.factory.make_node(self.journal)
        VLE.factory.make_entry(self.template, self.journal.authors.first().user, node)

        nodes = timeline.get_nodes(self.journal, self.student)

        self.assertEqual(len(nodes), 4)

        self.assertEqual(nodes[0]['type'], 'd')
        self.assertEqual(nodes[0]['entry'], None)

        self.assertEqual(nodes[1]['type'], 'e')

        self.assertEqual(nodes[2]['type'], 'a')

        self.assertEqual(nodes[3]['type'], 'p')
        self.assertEqual(nodes[3]['target'], 10)

    def test_get_add_node(self):
        journal = factory.Journal(entries__n=0)

        with self.assertNumQueries(self.template_serializer_query_count):
            data = timeline.get_add_node(journal)

        assert data['type'] == VLE.models.Node.ADDNODE
        assert data['nID'] == -1

    def test_get_entry_node(self):
        entry = factory.UnlimitedEntry(node__journal__assignment__format__templates=[{'type': Field.TEXT}])
        journal = entry.node.journal
        node = entry.node
        student = journal.author

        # With the node in memory, serializing the entry node should only cost queries for the entry serializer.
        with self.assertNumQueries(5):
            data = timeline.get_entry_node(journal, node, student)

        assert data['type'] == node.type
        assert data['nID'] == node.id
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
        assert data['nID'] == node.pk
        assert data['jID'] == node.journal.pk
        assert data['due_date'] == node.preset.due_date
        assert data['target'] == node.preset.target

    def test_get_deadline(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT} for _ in range(3)])
        preset_entry = factory.PresetEntry(node__journal__assignment=assignment)
        node = preset_entry.node
        journal = preset_entry.node.journal
        author = preset_entry.node.journal.author

        # No additional queries are performed besides the nested serializer queries plus fetching the attached files
        with self.assertNumQueries(
                self.template_serializer_query_count + self.entry_serializer_default_query_count + 1):
            data = timeline.get_deadline(journal, node, author)

        assert data['description'] == node.preset.description
        assert data['type'] == node.type
        assert data['nID'] == node.id
        assert data['jID'] == journal.pk
        assert data['unlock_date'] == node.preset.unlock_date
        assert data['due_date'] == node.preset.due_date
        assert data['lock_date'] == node.preset.lock_date
        assert not data['deleted_preset'], 'Preset is not deleted, so flag should also be false'

        # Test if get_entry_node does not crash when preset is deleted
        utils.delete_presets([{'id': node.preset.pk}])
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
        factory.PresetEntry(node__journal=journal)
        factory.ProgressPresetNode(format=journal.assignment.format)

        # Can add checks 4
        # Prefetch preset node attached files 1
        # get_deadline_node 7
        # get_entry_node 4
        # get_add_node 2
        # No additional queries are performed
        with assert_num_queries_less_than(20):
            data = timeline.get_nodes(journal, author=student)

        assert data[-1]['type'] == Node.PROGRESS, 'Progress goal should be the last timeline node'
        assert data[-2]['type'] == Node.ADDNODE, 'Add node should be positioned before the final progress goal'

        assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}])
        journal = factory.LtiJournal(entries__n=1, assignment=assignment)
        journal = Journal.objects.get(pk=journal.pk)
        student = journal.author

        data = timeline.get_nodes(journal, author=student)
        assert data[-1]['type'] == Node.ADDNODE, \
            'Add node should be positioned as the final node if no progress goals are set'

        assignment.lock_date = timezone.now()
        assignment.save()
        journal = Journal.objects.get(pk=journal.pk)
        data = timeline.get_nodes(journal, author=student)
        for n in data:
            assert n['type'] != Node.ADDNODE, 'When the assignment is locked no add node should be serialized'
