import test.factory as factory
from test.utils import api
from test.utils.response import in_response

from django.test import TestCase

import VLE.factory as nfac
from VLE.models import Group, Participation


class GroupAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.course = factory.Course(author=self.teacher)
        self.create_params = {'name': 'test', 'course_id': self.course.pk}
        self.group = factory.Group(course=self.course)

    def test_rest(self):
        # Test the basic rest functionality as a superuser
        api.test_rest(self, 'groups',
                      create_params=self.create_params,
                      get_params={'course_id': self.course.pk}, get_status=405, get_is_create=False,
                      update_params={'name': 'test2'},
                      user=factory.Admin())

        # Test the basic rest functionality as a teacher
        api.test_rest(self, 'groups',
                      create_params=self.create_params,
                      get_params={'course_id': self.course.pk}, get_status=405, get_is_create=False,
                      update_params={'name': 'test2'},
                      user=self.teacher)

        # Test the basic rest functionality as a student
        api.test_rest(self, 'groups',
                      create_params=self.create_params, get_status=405, get_is_create=False,
                      create_status=403,
                      user=factory.Student())

    def test_list_limited(self):
        def check_ids(groups):
            ids = [g['id'] for g in groups]
            assert empty_group.pk not in ids, 'empty groups should not be shown'
            assert test_student_group.pk not in ids, 'groups with only test student should not be shown'
            assert teacher_group.pk not in ids, 'groups with only teacher should not be shown'

            assert student_group.pk in ids, 'groups with student should be shown'
            assert other_group.pk in ids, 'groups with student should be shown'
            assert test_and_student_group.pk in ids, 'groups with student and test student should be shown'

            assert all_group.pk not in ids, 'groups with all students should not be shown'

        empty_group = self.group

        test_student = factory.TestUser()
        journal = factory.Journal(assignment__courses=[self.course])
        journal.authors.set([])
        journal.add_author(factory.AssignmentParticipation(user=test_student))
        assignment = journal.assignment

        test_student_group = factory.Group(course=self.course)
        test_participation = Participation.objects.get(user=test_student)
        test_participation.groups.add(test_student_group)

        student = factory.Journal(assignment=assignment).authors.first().user
        student_group = factory.Group(course=self.course)
        student_in_group = Participation.objects.get(user=student)
        student_in_group.groups.add(student_group)

        test_and_student_group = factory.Group(course=self.course)
        student_in_group.groups.add(test_and_student_group)
        test_participation.groups.add(test_and_student_group)

        teacher_group = factory.Group(course=self.course)
        teacher_participation = Participation.objects.get(user=self.teacher)
        teacher_participation.groups.add(teacher_group)

        other_student = factory.Journal(assignment=assignment).authors.first().user
        other_group = factory.Group(course=self.course)
        other_student_participation = Participation.objects.get(user=other_student)
        other_student_participation.groups.add(other_group)

        all_group = factory.Group(course=self.course)
        student_in_group.groups.add(all_group)
        test_participation.groups.add(all_group)
        teacher_participation.groups.add(all_group)
        other_student_participation.groups.add(all_group)

        groups = api.get(
            self, 'groups', params={'course_id': self.course.pk, 'assignment_id': assignment.pk},
            user=self.teacher)['groups']
        check_ids(groups)

        # Check if the same groups are returned when students are together in one group journal
        group_journal = factory.GroupJournal()
        for ap in group_journal.authors.all():
            ap.user.delete()
        group_journal.assignment.courses.set([self.course])
        group_journal.add_author(factory.AssignmentParticipation(user=student))
        group_journal.add_author(factory.AssignmentParticipation(user=other_student))
        other_group_journal = factory.GroupJournal(assignment=group_journal.assignment)
        for ap in other_group_journal.authors.all():
            ap.user.delete()
        other_group_journal.add_author(factory.AssignmentParticipation(user=test_student))

        groups = api.get(
            self, 'groups', params={'course_id': self.course.pk, 'assignment_id': assignment.pk},
            user=self.teacher)['groups']
        check_ids(groups)

    def test_get(self):
        # Test all groups from course
        api.get(self, 'groups', user=self.teacher, status=400)
        api.get(self, 'groups', params={'course_id': self.course.pk}, user=factory.Student(), status=403)
        api.get(self, 'groups', params={'course_id': self.course.pk}, user=factory.Admin())
        get_resp = api.get(self, 'groups', params={'course_id': self.course.pk}, user=self.teacher)['groups']
        assert in_response(get_resp, self.group), 'Group that is added to  the course, should also be returned'

    def test_create(self):
        # Test required params
        api.create(self, 'groups', user=self.teacher, status=400)

        # Test connected teacher
        resp = api.create(self, 'groups',
                          params={'course_id': self.course.pk, 'name': 'Test', 'lti_id': 'lti'}, user=self.teacher)
        assert resp['group']['name'] == 'Test'

        # Test unconnected admin
        api.create(self, 'groups', params={'course_id': self.course.pk, 'name': 'Test2'}, user=factory.Admin())

        # Test duplicate
        api.create(self, 'groups', params={'course_id': self.course.pk, 'name': 'Test', 'lti_id': 'lti'},
                   user=self.teacher, status=400)

        # Test not authorized teacher
        api.create(self, 'groups', params={'course_id': self.course.pk, 'name': 'Test'},
                   user=factory.Teacher(), status=403)

        # Test student
        api.create(self, 'groups', params={'course_id': self.course.pk, 'name': 'Test'},
                   user=factory.Student(), status=403)

    def test_update(self):
        # Test required params
        api.update(self, 'groups', params={'pk': self.group.pk}, user=factory.Admin(), status=400)

        # Test unconnected admin
        resp = api.update(self, 'groups', params={'pk': self.group.pk, 'name': 'Test2'}, user=factory.Admin())
        assert resp['group']['name'] == 'Test2'

        # Test duplicate
        factory.Group(name='duplicate', course=self.course)
        factory.Group(name='other_duplicate')
        api.update(self, 'groups', params={'pk': self.group.pk, 'name': 'duplicate'}, user=factory.Admin())
        api.update(self, 'groups', params={'pk': self.group.pk, 'name': 'other_duplicate'}, user=factory.Admin())

    def test_delete(self):
        api.delete(self, 'groups', params={'pk': self.group.pk}, user=factory.Student(), status=403)
        api.delete(self, 'groups', params={'pk': self.group.pk}, user=factory.Teacher(), status=403)
        api.delete(self, 'groups', params={'pk': self.group.pk}, user=factory.Admin())

    def test_members(self):
        members = api.get(self, 'members', params={'group_id': self.group.pk}, user=self.teacher)['members']
        assert len(members) == 0, 'Default there should be 0 members in a group'

        api.create(self, 'members',
                   params={'group_id': self.group.pk, 'user_id': self.teacher.pk}, user=self.teacher)

        members = api.get(self, 'members', params={'group_id': self.group.pk}, user=self.teacher)['members']
        assert len(members) == 1, 'Teacher should be added to the group'

        members = api.delete(self, 'members',
                             params={'pk': self.group.pk, 'user_id': self.teacher.pk},
                             user=self.teacher)

        members = api.get(self, 'members', params={'group_id': self.group.pk}, user=self.teacher)['members']
        assert len(members) == 0, 'Teacher should be removed from the group'

        # Check not viewable for students
        api.delete(self, 'members',
                   params={'pk': self.group.pk, 'user_id': self.teacher.pk}, user=factory.Student(), status=403)
        api.create(self, 'members',
                   params={'group_id': self.group.pk, 'user_id': self.teacher.pk}, user=factory.Student(), status=403)
        api.get(self, 'members', params={'group_id': self.group.pk}, user=factory.Student(), status=403)

    def test_group_api(self):
        course = factory.Course(active_lti_id='6068')
        nfac.make_lti_groups(course)
        assert Group.objects.filter(course=course).count() > 0
