import test.factory as factory
from test.utils import api
from test.utils.response import is_response

from VLE.models import Assignment, Course, Participation, Role, User

from django.conf import settings
from django.test import TestCase


class CourseAPITest(TestCase):
    def setUp(self):
        self.create_params = {'name': 'test_course', 'abbreviation': 'TC'}
        self.student = factory.Student()
        self.teacher1 = factory.Teacher()
        self.teacher2 = factory.Teacher()
        self.admin = factory.Admin()

        self.course1 = factory.Course(author=self.teacher1)
        self.course2 = factory.Course(author=self.teacher1)
        self.course3 = factory.Course(author=self.teacher2)

    def test_rest(self):
        # Test the basic rest functionality as a superuser
        api.test_rest(self, 'courses',
                      create_params=self.create_params,
                      update_params={'abbreviation': 'TC2'},
                      user=factory.Admin())

        # Test the basic rest functionality as a teacher
        api.test_rest(self, 'courses',
                      create_params=self.create_params,
                      update_params={'abbreviation': 'TC2'},
                      user=factory.Teacher())

        # Test the basic rest functionality as a student
        api.test_rest(self, 'courses',
                      create_params=self.create_params,
                      create_status=403,
                      user=factory.Student())

    def test_course_factory(self):
        c_c = Course.objects.count()
        u_c = User.objects.count()
        a_c = Assignment.objects.count()

        course = factory.Course()

        assert c_c + 1 == Course.objects.count(), 'One course is generated'
        assert u_c + 1 == User.objects.count() and User.objects.last().pk == course.author.pk, 'One user is generated'
        assert a_c == Assignment.objects.count(), 'No assignment is generated'

        for expected_role in settings.ROLES.keys():
            assert Role.objects.filter(course=course, name=expected_role).exists()

        teacher_role = Role.objects.get(name='Teacher', course=course)
        assert Participation.objects.filter(course=course, role=teacher_role, user=course.author).exists(), \
            'Author of the course is made a teacher by default'

    def test_get(self):
        factory.Participation(user=self.teacher2, course=self.course2)

        # Get all courses
        get_resp = api.get(self, 'courses', user=self.teacher1)['courses']
        assert len(get_resp) == 2, 'The teacher did not get all the courses it is the author of'
        assert {self.course1.pk, self.course2.pk} == set([c['id'] for c in get_resp]), \
            'The teacher did not get all the courses it is the author of'

        get_resp = api.get(self, 'courses', user=self.teacher2)['courses']
        assert len(get_resp) == 2, 'The teacher did not get all the courses it is the author of or is participating in'
        assert is_response(get_resp, self.course2, self.course3), \
            'The teacher did not get all the courses it is the author of'

        # Get author course
        get_resp = api.get(self, 'courses', params={'pk': self.course1.pk}, user=self.teacher1)

        # Check not participating
        get_resp = api.get(self, 'courses', params={'pk': self.course1.pk}, user=self.teacher2, status=403)

        # Check participating
        get_resp = api.get(self, 'courses', params={'pk': self.course2.pk}, user=self.teacher2)

    def test_create_course(self):
        # Test courses with same name and abbreviation
        resp = api.create(self, 'courses', params=self.create_params, user=self.teacher1)['course']
        course = Course.objects.get(pk=resp['id'])
        teacher_role = Role.objects.get(course=course, name='Teacher')
        assert teacher_role.can_manage_journal_import_requests, 'A teacher should be able to manage JIRs by default'

        api.create(self, 'courses', params=self.create_params, user=self.teacher1)

        # Test admin without is_teacher can make a course
        self.admin.is_teacher = False
        self.admin.save()
        api.create(self, 'courses', params=self.create_params, user=self.admin)

        # Check that students cannot make new courses
        api.create(self, 'courses', params=self.create_params, user=self.student, status=403)

    def test_update_course(self):
        # Test if other then a superuser or the author self can update the course
        api.update(self, 'courses', params={'pk': self.course1.pk, 'abbreviation': 'TC2'},
                   user=self.teacher2, status=403)
        api.update(self, 'courses', params={'pk': self.course2.pk, 'abbreviation': 'TC2'},
                   user=self.teacher2, status=403)

        update_resp = api.update(self, 'courses', params={'pk': self.course2.pk, 'abbreviation': 'TC2'},
                                 user=self.teacher1)['course']
        assert update_resp['abbreviation'] == 'TC2', 'Teacher should be able to update the course'
        update_resp = api.update(self, 'courses', params={'pk': self.course2.pk, 'abbreviation': 'TC3'},
                                 user=self.admin)['course']
        assert update_resp['abbreviation'] == 'TC3', 'Superuser should be able to update the course'
        api.update(self, 'courses', params={'pk': self.course2.pk, 'lti_id': 'new-lti-id'}, user=self.teacher1)
        self.course2.refresh_from_db()
        assert self.course2.active_lti_id == 'new-lti-id', 'Teacher should be able to update the lti_id'
        assert self.course2.abbreviation == 'TC3', 'abbreviation should not update on change of lti_id'
        api.update(
            self, 'courses', params={'pk': self.course2.pk, 'lti_id': 'new-lti-id2'}, user=self.teacher1, status=400)
        self.course2.refresh_from_db()
        assert self.course2.active_lti_id == 'new-lti-id', \
            'Teacher should be not able to update the lti_id when already set'
        assert self.course2.abbreviation == 'TC3', 'abbreviation should not update on change of lti_id'

    def test_delete_course(self):
        # Test if only authors and superusers can delete courses
        api.delete(self, 'courses', params={'pk': self.course1.pk}, user=self.teacher2, status=403)
        api.delete(self, 'courses', params={'pk': self.course1.pk}, user=self.teacher1)
        api.delete(self, 'courses', params={'pk': self.course2.pk}, user=self.admin)

        # Test if (lti) assignment functions corrently when courses get deleted
        c0 = factory.Course()
        c1 = factory.LtiCourse()
        c2 = factory.LtiCourse()
        assignment = factory.Assignment(courses=[c0])
        assignment.add_course(c1)
        assignment.add_course(c2)
        assignment.add_lti_id('lti_id_c1', c1)
        assignment.add_lti_id('lti_id_c2', c2)
        assignment.refresh_from_db()
        c2.refresh_from_db()
        assert assignment.active_lti_id in c2.assignment_lti_id_set

        api.delete(self, 'courses', params={'pk': c2.pk}, user=self.admin)
        assignment.refresh_from_db()
        c1.refresh_from_db()
        assert assignment.active_lti_id in c1.assignment_lti_id_set

        api.delete(self, 'courses', params={'pk': c1.pk}, user=self.admin)
        assignment.refresh_from_db()
        assert assignment.active_lti_id is None

        # Test if you cannot delete course when you dont also have delete assignment permission
        r = Role.objects.get(course=c0, name='Teacher')
        r.can_delete_assignment = False
        r.save()
        api.delete(self, 'courses', params={'pk': c0.pk}, user=c0.author, status=403)
        r.can_delete_assignment = True
        r.save()
        api.delete(self, 'courses', params={'pk': c0.pk}, user=c0.author)
        assert not Assignment.objects.filter(pk=assignment.pk).exists()

    def test_functions(self):
        course = factory.Course()
        course.add_assignment_lti_id('lti_id1')
        assert 'lti_id1' in course.assignment_lti_id_set, 'test if add_assignment_lti_id works'
        course.add_assignment_lti_id('lti_id2')
        course.add_assignment_lti_id('lti_id2')
        assert len(course.assignment_lti_id_set) == 2, 'test if add_assignment_lti_id does not add duplicates'
