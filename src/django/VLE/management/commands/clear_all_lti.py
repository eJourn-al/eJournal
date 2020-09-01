"""Remove all LTI fields of current database. Useful when testing LTI integration."""
from django.core.management.base import BaseCommand

from VLE.models import Assignment, Course, User


class Command(BaseCommand):
    help = 'Remove all LTI fields of current database. Useful when testing LTI integration.'

    def handle(self, *args, **options):
        """
        Generates a dummy data for a testing environment.
        """
        User.objects.filter(is_test_student=True).delete()
        User.objects.filter(lti_id__isnull=False).exclude(username='teacher').delete()
        User.objects.filter(username='teacher').update(lti_id=None)
        Assignment.objects.filter(active_lti_id__isnull=False).update(active_lti_id=None, lti_id_set=[])
        Course.objects.filter(active_lti_id__isnull=False).update(active_lti_id=None, assignment_lti_id_set=[])
