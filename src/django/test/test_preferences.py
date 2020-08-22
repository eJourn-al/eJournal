import test.factory as factory
from test.utils import api

from django.test import TestCase

from VLE.models import Preferences


class PreferencesAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.preferences = Preferences.objects.get(user=self.teacher)

    def test_get(self):
        # Should respond with preferences
        resp = api.get(self, 'preferences', params={'pk': self.teacher.pk}, user=self.teacher)
        assert 'preferences' in resp
        assert 'new_grade_notifications' in resp['preferences'], 'preferences should also be returned'
        assert resp['preferences'].get('user', None) == self.teacher.pk, 'user should be own pk'

        # Should not be able to see preferences of other users
        api.get(self, 'preferences', params={'pk': factory.Student().pk}, user=self.teacher, status=403)
        # Except for admins
        api.get(self, 'preferences', params={'pk': factory.Student().pk}, user=factory.Admin())

    def test_update(self):
        data = {
            'pk': self.teacher.pk,
            'new_grade_notifications': Preferences.PUSH,
        }
        # Should not be able to update preferences of other users
        api.update(self, 'preferences', params=data, user=factory.Teacher(), status=403)
        # Except for admins or self
        prefs = api.update(self, 'preferences', params=data, user=factory.Admin())['preferences']
        assert prefs['new_grade_notifications'] != self.preferences
        prefs = api.update(self, 'preferences', params=data, user=self.teacher)['preferences']
        assert prefs['new_grade_notifications'] != self.preferences

        # Invalid data should not work
        data = {
            'pk': self.teacher.pk,
            'new_grade_notifications': 'not a bool',
        }
        api.update(self, 'preferences', params=data, user=self.teacher, status=400)
