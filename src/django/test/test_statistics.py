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
        self.journal = factory.Journal()
        self.entries = [factory.Entry(node__journal=self.journal) for _ in range(4)]

    def test_journal_stats(self):
        """Test the journal stats functions in the serializer."""
        entries = VLE.models.Entry.objects.filter(node__journal=self.journal)
        for entry in entries[1:]:
            api.create(self, 'grades', params={'entry_id': entry.id, 'grade': 1, 'published': True},
                       user=self.journal.assignment.courses.first().author)
        self.journal.refresh_from_db()
        assert self.journal.grade == 3
        self.journal.bonus_points = 5
        self.journal.save()
        assert self.journal.grade == 8
        assert entries.count() == 4
