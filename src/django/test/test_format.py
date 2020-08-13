import test.factory as factory
from test.utils import api

from django.test import TestCase

import VLE.serializers as serialize
from VLE.models import Entry, Group, Journal, Field


class FormatAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.admin = factory.Admin()
        self.course = factory.Course(author=self.teacher)
        self.assignment = factory.Assignment(courses=[self.course])
        self.format = factory.Format(assignment=self.assignment)
        self.template = factory.Template(format=self.format)
        self.update_dict = {
            'assignment_details': {
                'name': 'Colloq',
                'description': 'description1',
                'is_published': True
            },
            'templates': serialize.TemplateSerializer(self.format.template_set.filter(archived=False), many=True).data,
            'removed_presets': [],
            'removed_templates': [],
            'presets': []
        }

    def test_template_factory(self):
        template = factory.Template()
        assert not template.field_set.exists(), 'By default a template should be iniated without fields'

        template = factory.Template(gen_fields=[{'type': Field.URL}])
        Field.objects.get(template=template, type=Field.URL)
        assert template.field_set.count() == 1, 'It is possible to generate fields including kwargs'

    def test_update_assign_to(self):
        def check_groups(groups, status=200):
            api.update(
                self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                user=self.teacher, status=status)
            if status == 200:
                self.assignment.refresh_from_db()
                assert self.assignment.assigned_groups.count() == len(groups), \
                    'Assigned group amount should be correct'
                for group in Group.objects.all():
                    if group in groups:
                        assert self.assignment.assigned_groups.filter(pk=group.pk).exists(), \
                            'Group should be in assigned groups'
                    else:
                        assert not self.assignment.assigned_groups.filter(pk=group.pk).exists(), \
                            'Group should not be in assigned groups'

        group = factory.Group(course=self.course)
        self.update_dict['assignment_details']['assigned_groups'] = [
            {'id': group.pk},
        ]
        self.update_dict['course_id'] = self.course.pk
        check_groups([group])

        # Test groups from other courses are not added when course_id is wrong
        course2 = factory.Course()
        self.assignment.add_course(course2)
        group2 = factory.Group(course=course2)
        self.update_dict['assignment_details']['assigned_groups'] = [
            {'id': group.pk},
            {'id': group2.pk},
        ]
        self.update_dict['course_id'] = self.course.pk
        check_groups([group])

        # Test group gets added when other course is supplied, also check if other group does not get removed
        self.update_dict['assignment_details']['assigned_groups'] = [
            {'id': group2.pk},
        ]
        self.update_dict['course_id'] = course2.pk
        check_groups([group, group2])

        # Test if only groups from supplied course get removed
        self.update_dict['assignment_details']['assigned_groups'] = []
        self.update_dict['course_id'] = course2.pk
        check_groups([group])

    def test_update_format(self):
        # TODO: Improve template testing
        api.update(
            self, 'formats', params={
                'pk': self.assignment.pk, 'assignment_details': None,
                'templates': [], 'presets': [], 'removed_presets': [],
                'removed_templates': []
            }, user=factory.Student(), status=403)
        api.update(
            self, 'formats', params={
                'pk': self.assignment.pk, 'assignment_details': None,
                'templates': [], 'presets': [], 'removed_presets': [],
                'removed_templates': []
            }, user=self.teacher)
        api.update(
            self, 'formats', params={
                'pk': self.assignment.pk, 'assignment_details': None,
                'templates': [], 'presets': [], 'removed_presets': [],
                'removed_templates': []
            }, user=factory.Admin())

        # Try to publish the assignment
        api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                   user=factory.Student(), status=403)
        api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                   user=self.teacher)
        api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                   user=factory.Admin())

        # Check cannot unpublish/change assignment type if there are entries
        factory.Entry(node__journal__assignment=self.assignment)
        group_dict = self.update_dict.copy()
        group_dict['assignment_details']['is_group_assignment'] = True
        self.update_dict['assignment_details']['is_published'] = False
        api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                   user=self.teacher, status=400)
        api.update(self, 'formats', params={'pk': self.assignment.pk, **group_dict},
                   user=self.teacher, status=400)
        Entry.objects.filter(node__journal__assignment=self.assignment).delete()
        api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                   user=self.teacher, status=200)
        api.update(self, 'formats', params={'pk': self.assignment.pk, **group_dict},
                   user=self.teacher, status=200)
        assert not Journal.objects.filter(node__journal__assignment=self.assignment).exists(), \
            'All journals should be deleted after type change'
        self.update_dict['assignment_details']['is_published'] = True
        api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                   user=self.teacher, status=200)

        # Test script sanitation
        self.update_dict['assignment_details']['description'] = '<script>alert("asdf")</script>Rest'
        resp = api.update(self, 'formats', params={'pk': self.assignment.pk, **self.update_dict},
                          user=self.teacher)
        assert resp['assignment_details']['description'] == 'Rest'
