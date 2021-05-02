import test.factory as factory
from test.utils import api

from django.test import TestCase

from VLE.models import Preferences


class PreferencesAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.assignment = factory.Assignment(author=self.teacher)
        self.preferences = Preferences.objects.get(user=self.teacher)

    def test_get_preferences(self):
        self.preferences.hide_past_deadlines_of_assignments.add(self.assignment)

        # Should respond with preferences
        resp = api.get(self, 'preferences', params={'pk': self.teacher.pk}, user=self.teacher)
        assert 'preferences' in resp
        assert 'new_grade_notifications' in resp['preferences'], 'preferences should also be returned'
        assert resp['preferences']['hide_past_deadlines_of_assignments'] == [self.assignment.pk], \
            'Hide past deadlines of assignments is serialized as a list of assignment ids'
        assert resp['preferences'].get('user', None) == self.teacher.pk, 'user should be own pk'

        # Should not be able to see preferences of other users
        api.get(self, 'preferences', params={'pk': factory.Student().pk}, user=self.teacher, status=403)
        # Except for admins
        api.get(self, 'preferences', params={'pk': factory.Student().pk}, user=factory.Admin())

    def test_update_preferences(self):
        assignment = factory.Assignment()
        assignment2 = factory.Assignment()
        self.preferences.hide_past_deadlines_of_assignments.add(self.assignment)

        data = {
            'pk': self.teacher.pk,
            'new_grade_notifications': Preferences.PUSH,
            'hide_past_deadlines_of_assignments': [assignment.pk, assignment2.pk],
        }
        # Should not be able to update preferences of other users
        api.update(self, 'preferences', params=data, user=factory.Teacher(), status=403)
        # Except for admins or self
        prefs = api.update(self, 'preferences', params=data, user=factory.Admin())['preferences']
        assert prefs['new_grade_notifications'] == data['new_grade_notifications']
        assert set(prefs['hide_past_deadlines_of_assignments']) == set(data['hide_past_deadlines_of_assignments'])
        prefs = api.update(self, 'preferences', params=data, user=self.teacher)['preferences']

        # Invalid data should not work
        data = {
            'pk': self.teacher.pk,
            'new_grade_notifications': 'not a bool',
        }
        api.update(self, 'preferences', params=data, user=self.teacher, status=400)
