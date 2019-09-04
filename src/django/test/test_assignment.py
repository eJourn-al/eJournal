import test.factory as factory
from test.utils import api

from django.test import TestCase

import VLE.utils.generic_utils as utils


class AssignmentAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.admin = factory.Admin()
        self.course = factory.Course(author=self.teacher)
        self.create_params = {'name': 'test', 'description': 'test_description', 'course_id': self.course.pk}

    def test_rest(self):
        # Test the basic rest functionality as a superuser
        api.test_rest(self, 'assignments',
                      create_params=self.create_params,
                      get_params={'course_id': self.course.pk},
                      update_params={'description': 'test_description2'},
                      delete_params={'course_id': self.course.pk},
                      user=factory.Admin())

        # Test the basic rest functionality as a teacher
        api.test_rest(self, 'assignments',
                      create_params=self.create_params,
                      get_params={'course_id': self.course.pk},
                      update_params={'description': 'test_description2'},
                      delete_params={'course_id': self.course.pk},
                      user=self.teacher)

        # Test the basic rest functionality as a student
        api.test_rest(self, 'assignments',
                      create_params=self.create_params,
                      create_status=403,
                      user=factory.Student())

    def test_update(self):
        assignment = api.create(self, 'assignments', params=self.create_params, user=self.teacher)['assignment']

        # Try to publish the assignment
        # TODO: Test cannot unpublish when there are entries inside
        api.update(self, 'assignments', params={'pk': assignment['id'], 'published': True},
                   user=factory.Student(), status=403)
        api.update(self, 'assignments', params={'pk': assignment['id'], 'published': True},
                   user=self.teacher)
        api.update(self, 'assignments', params={'pk': assignment['id'], 'published': True},
                   user=factory.Admin())

    def test_delete(self):
        teach_course = factory.Course(author=self.teacher)
        other_course = factory.Course()
        assignment = factory.Assignment(courses=[self.course, teach_course, other_course])

        # Test no course specified
        api.delete(self, 'assignments', params={'pk': assignment.pk}, user=self.teacher, status=400)

        # Test normal removal
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': teach_course.id}, user=self.teacher)
        assert 'removed' in resp['description'] and 'deleted' not in resp['description'], \
            'The assignment should be removed from the course, not deleted'

        # Test if only admins can delete assignments they are not part of
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': other_course.id}, user=self.teacher, status=403)
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': other_course.id}, user=self.teacher, status=403)
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': other_course.id}, user=self.admin, status=200)

        # Test delete
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': self.course.id}, user=self.teacher)
        assert 'removed' not in resp['description'] and 'deleted' in resp['description'], \
            'The assignment should be deleted from the course, not removed'

    def test_copyable(self):
        teacher = factory.Teacher()
        course = factory.Course(author=teacher)
        assignment = factory.TemplateAssignment(courses=[course])
        factory.TemplateFormat(assignment=assignment)
        assignment2 = factory.TemplateAssignment(courses=[course])
        factory.TemplateFormat(assignment=assignment2)
        journal = factory.Journal(assignment=assignment2)
        [factory.Entry(node__journal=journal) for _ in range(4)]

        resp = api.get(self, 'assignments/copyable', params={'pk': assignment.pk}, user=teacher)['data']
        assert len(resp[0]['assignments']) == 1
        assert resp[0]['course']['id'] == course.id, 'copyable assignments should be displayed'

        before_id = api.get(self, 'formats', params={'pk': assignment2.pk},
                            user=teacher)['format']['templates'][0]['id']
        before_from_id = api.get(self, 'formats', params={'pk': assignment.pk},
                                 user=teacher)['format']['templates'][0]['id']
        resp = api.update(self, 'formats/copy', params={'pk': assignment2.pk, 'from_assignment_id': assignment.pk},
                          user=teacher)
        after_id = api.get(self, 'formats', params={'pk': assignment2.pk}, user=teacher)['format']['templates'][0]['id']

        after_from_id = api.get(self, 'formats', params={'pk': assignment.pk},
                                user=teacher)['format']['templates'][0]['id']
        assert before_id != after_id, 'Assignment should be changed'
        assert before_from_id == after_from_id, 'From assignment templates should be unchanged'

        assert len(utils.get_journal_entries(journal)) == 4, 'Old entries should not be removed'
