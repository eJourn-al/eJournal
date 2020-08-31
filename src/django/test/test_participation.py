import test.factory as factory
from test.utils import api

from django.test import TestCase

from VLE.models import Role, User


class ParticipationAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.course = factory.Course(author=self.teacher)
        factory.Assignment(courses=[self.course])
        participation = factory.Participation(course=self.course)
        self.student = participation.user
        # Username is 4 chartacters for the unenrolled check
        self.not_connected = factory.Student(username='4444', full_name='Not Connected')
        self.create_params = {'course_id': self.course.pk, 'user_id': self.not_connected.pk}
        self.group1 = factory.Group(course=self.course)
        self.group2 = factory.Group(course=self.course)
        self.update_params = {
            'pk': self.course.pk,
            'user_id': self.student.pk,
            'role': 'Teacher'
        }

    def test_get(self):
        api.get(self, 'participations', params={'course_id': self.course.pk}, user=self.student, status=403)
        api.get(self, 'participations', params={'course_id': self.course.pk}, user=self.teacher)

        resp = api.get(self, 'participations', params={'pk': self.course.pk}, user=self.student)
        assert resp['participant']['user']['id'] == self.student.pk
        resp = api.get(self, 'participations', params={'pk': self.course.pk}, user=self.teacher)
        assert resp['participant']['user']['id'] == self.teacher.pk

    def test_create(self):
        api.create(self, 'participations', params=self.create_params, user=self.student, status=403)
        api.create(self, 'participations', params=self.create_params, user=self.teacher)

    def test_update(self):
        api.update(self, 'participations', params=self.update_params, user=self.student, status=403)

        api.update(self, 'participations', params=self.update_params, user=self.teacher)

        # Check cannot update role without can_edit_course_roles permissions
        Role.objects.filter(course=self.course).update(can_edit_course_roles=False)
        api.update(self, 'participations', params=self.update_params, user=self.teacher, status=403)
        self.update_params.pop('role', None)
        api.update(self, 'participations', params=self.update_params, user=self.teacher)

    def test_delete(self):
        api.delete(self, 'participations', params={'pk': self.course.pk}, user=self.teacher, status=400)
        api.delete(self, 'participations',
                   params={'pk': self.course.pk, 'user_id': self.student.pk}, user=self.student, status=403)
        api.delete(self, 'participations',
                   params={'pk': self.course.pk, 'user_id': self.student.pk}, user=self.teacher)
        api.delete(self, 'participations',
                   params={'pk': self.course.pk, 'user_id': self.student.pk}, user=self.teacher, status=404)

    def test_delete_test_user_participation(self):
        test_user = factory.TestUser()
        factory.Participation(user=test_user, course=self.course)
        api.delete(self, 'participations', params={'pk': self.course.pk, 'user_id': test_user.pk}, user=self.teacher)
        assert not User.objects.filter(pk=test_user.pk).exists(), 'A test user should be deleted upon removal from a ' \
            'course, if the test user has no remaining participations.'

        test_user = factory.TestUser()
        factory.Participation(user=test_user, course=self.course)
        factory.Participation(user=test_user, course=factory.Course())
        api.delete(self, 'participations', params={'pk': self.course.pk, 'user_id': test_user.pk}, user=self.teacher)
        assert User.objects.filter(pk=test_user.pk).exists(), 'A test user should not be deleted upon removal from a ' \
            'course, if the test user has remaining participations.'

    def test_unenrolled(self):
        api.get(self, 'participations/unenrolled',
                params={'course_id': self.course.pk, 'unenrolled_query': ''}, user=self.student, status=403)
        resp = api.get(self, 'participations/unenrolled',
                       params={'course_id': self.course.pk, 'unenrolled_query': ''}, user=self.teacher)
        assert len(resp['participants']) == 0

        # Check perfect name that is small
        resp = api.get(self, 'participations/unenrolled',
                       params={'course_id': self.course.pk, 'unenrolled_query': self.not_connected.username},
                       user=self.teacher)['participants']
        assert len(resp) == 1, 'A single participant should be found (perfect match)'
        resp = resp[0]
        assert resp['username'] == self.not_connected.username, 'Username should be returned to display front end'
        assert resp['full_name'] == self.not_connected.full_name, 'Username should be returned to display front end'

        # Check first and last name
        resp = api.get(self, 'participations/unenrolled',
                       params={
                           'course_id': self.course.pk,
                           'unenrolled_query': self.not_connected.full_name[:5] + ' ' + 'invalid_last_name'},
                       user=self.teacher)
        assert len(resp['participants']) == 0
        resp = api.get(self, 'participations/unenrolled',
                       params={
                           'course_id': self.course.pk,
                           'unenrolled_query': self.not_connected.full_name},
                       user=self.teacher)
        assert len(resp['participants']) == 1

        # Check subnames of longer names
        other_not_conn = factory.Student(username='longusername', full_name='longfirstname longlastname')
        resp = api.get(self, 'participations/unenrolled',
                       params={'course_id': self.course.pk, 'unenrolled_query': other_not_conn.full_name[:6]},
                       user=self.teacher)
        assert len(resp['participants']) == 1
        resp = api.get(self, 'participations/unenrolled',
                       params={'course_id': self.course.pk, 'unenrolled_query': other_not_conn.full_name[-6:]},
                       user=self.teacher)
        assert len(resp['participants']) == 1
        resp = api.get(self, 'participations/unenrolled',
                       params={'course_id': self.course.pk, 'unenrolled_query': other_not_conn.username[:6]},
                       user=self.teacher)
        assert len(resp['participants']) == 1

        # Check too small, not found
        resp = api.get(self, 'participations/unenrolled',
                       params={'course_id': self.course.pk, 'unenrolled_query': other_not_conn.full_name[:4]},
                       user=self.teacher)
        assert len(resp['participants']) == 0
