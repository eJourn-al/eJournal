from django.core.management import call_command
from django.test import TestCase


class CommandsTestCase(TestCase):
    """Test the self made commands."""

    def test_preset_db(self):
        """Test preset_db."""
        call_command('preset_db')

    def test_add_performance_course(self):
        call_command('add_performance_course', 1)
