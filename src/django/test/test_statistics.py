"""
test_statistics.py.

Test the authentication calls.
"""

import test.factory as factory
from test.utils import api

from django.test import TestCase

import VLE.models


class StatisticsTests(TestCase):
    """Test statistics functions."""
    def setUp(self):
        """Set up the test file."""
        self.n_entries = 4
        self.journal = factory.Journal(entries__n=self.n_entries)

    def test_journal_stats(self):
        """Test the journal stats functions in the serializer."""
        entries = VLE.models.Entry.objects.filter(node__journal=self.journal)
        n_graded_entries = self.n_entries - 1
        for entry in entries[self.n_entries - n_graded_entries:]:
            api.create(self, 'grades', params={'entry_id': entry.id, 'grade': 1, 'published': True},
                       user=self.journal.assignment.courses.first().author)
        self.journal.refresh_from_db()
        assert self.journal.grade == n_graded_entries
        bonus_points = 5
        self.journal.bonus_points = bonus_points
        self.journal.save()
        self.journal.refresh_from_db()
        assert self.journal.grade == n_graded_entries + bonus_points
        assert entries.count() == self.n_entries
        assert entries.exclude(grade=None).exclude(grade__grade=None).count() == n_graded_entries
