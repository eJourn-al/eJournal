"""
test_timeline.py.

Test all about the timeline.
"""
import datetime
import test.factory as factory

from django.test import TestCase

import VLE.factory
import VLE.timeline as timeline
from VLE.models import Journal, Role
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
        entry = VLE.factory.make_entry(self.template, self.journal.authors.first().user)
        node = VLE.factory.make_node(self.journal, entry)
        nodes = utils.get_sorted_nodes(self.journal)

        self.assertEqual(nodes[0].preset, self.deadlineentry)
        self.assertEqual(nodes[1], node)
        self.assertEqual(nodes[2].preset, self.progressnode)

    def test_json(self):
        """Test is the to dict function works correctly."""
        entry = VLE.factory.make_entry(self.template, self.journal.authors.first().user)
        VLE.factory.make_node(self.journal, entry)

        nodes = timeline.get_nodes(self.journal, self.student)

        self.assertEqual(len(nodes), 4)

        self.assertEqual(nodes[0]['type'], 'd')
        self.assertEqual(nodes[0]['entry'], None)

        self.assertEqual(nodes[1]['type'], 'e')

        self.assertEqual(nodes[2]['type'], 'a')

        self.assertEqual(nodes[3]['type'], 'p')
        self.assertEqual(nodes[3]['target'], 10)
