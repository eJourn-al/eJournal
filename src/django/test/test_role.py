import test.factory as factory
from test.utils import api

import VLE.models

from django.test import TestCase


class RoleAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.course = factory.Course(author=self.teacher)
        self.assignment = factory.Assignment(courses=[self.course])
        participation = factory.Participation(course=self.course)
        self.student = participation.user
        self.roles = VLE.models.Role.objects.all()

    def test_get(self):
        # Test list only done by teachers
        api.get(self, 'roles', params={'course_id': self.course.pk}, user=self.student, status=403)
        api.get(self, 'roles', params={'course_id': self.course.pk}, user=self.teacher)

        # Test not in course/assignment
        api.get(self, 'roles', params={'pk': 0, 'course_id': self.course.pk}, user=factory.Student(), status=403)
        api.get(self, 'roles', params={'pk': 0, 'assignment_id': self.assignment.pk}, user=factory.Student(),
                status=403)

        # Test get own role
        api.get(self, 'roles', params={'pk': 0, 'course_id': self.course.pk}, user=self.student)
        api.get(self, 'roles', params={'pk': 0, 'assignment_id': self.assignment.pk}, user=self.student)
        api.get(self, 'roles', params={'pk': self.student.pk, 'course_id': self.course.pk}, user=self.student)

        # Test other role
        api.get(self, 'roles', params={'pk': self.teacher.pk, 'course_id': self.course.pk}, user=self.student,
                status=403)
        api.get(self, 'roles', params={'pk': self.student.pk, 'course_id': self.course.pk}, user=self.teacher)

    def test_create_role(self):
        api.create(self, 'roles', user=self.teacher, status=400)

        # Test not author of course
        api.create(self, 'roles', params={'course_id': factory.Course().pk, 'name': 'name'}, user=self.teacher,
                   status=403)
        api.create(self, 'roles', params={'course_id': self.course.pk, 'name': 'name'}, user=self.student, status=403)

        api.create(self, 'roles', params={'course_id': self.course.pk, 'name': 'name'}, user=self.teacher)
        # Test cannot create the same role twice
        api.create(self, 'roles', params={'course_id': self.course.pk, 'name': 'name'}, user=self.teacher, status=400)

        # Test invalid permissions
        api.create(
            self, 'roles',
            params={
                'course_id': self.course.pk,
                'name': 'name',
                'permissions': 'invalid_string'
            }, user=self.teacher, status=400)
        api.create(
            self, 'roles',
            params={
                'course_id': self.course.pk,
                'name': 'name2',
                'permissions': ['invalid', 'list']
            }, user=self.teacher, status=400)
        api.create(
            self, 'roles',
            params={
                'course_id': self.course.pk,
                'name': 'name3',
                'permissions': {'invalid': 'object'}
            }, user=self.teacher, status=400)
        resp = api.create(
            self, 'roles',
            params={
                'course_id': self.course.pk,
                'name': 'name4',
                'permissions': {'can_edit_course_roles': True}
            }, user=self.teacher)

        assert resp['role']['can_edit_course_roles'], 'Check if extra permission is also set'

    def test_update(self):
        # Test invalid params
        api.update(self, 'roles', params={'pk': self.course.pk}, user=self.teacher, status=400)

        # Test successful
        role = VLE.models.Role.objects.filter(course=self.course, name='Teacher').first()
        resp = api.update(
            self, 'roles',
            params={
                'pk': self.course.pk,
                'roles': [{'name': role.name, 'can_edit_course_roles': not role.can_edit_course_roles}]
            }, user=self.teacher)
        assert role.can_edit_course_roles != resp['roles'][0]['can_edit_course_roles']

        # Test not can_edit_course_roles
        api.update(self, 'roles', params={'pk': self.course.pk}, user=self.teacher, status=403)

    def test_delete(self):
        # Test not can_edit_course_roles
        api.delete(self, 'roles', params={'pk': self.course.pk, 'name': self.roles.first().name}, user=self.student,
                   status=403)
        # Test delete main role should not be possible
        api.delete(self, 'roles', params={'pk': self.course.pk, 'name': self.roles.filter(name='TA').first().name},
                   user=self.teacher, status=400)
        role = factory.Role(course=self.course)
        api.delete(self, 'roles', params={'pk': self.course.pk, 'name': role.name},
                   user=self.teacher)
