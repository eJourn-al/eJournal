import test.factory as factory
from test.utils import api

from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from VLE.models import Assignment, Course, Entry, Field, FileContext, Format, Group, Journal, Node, PresetNode, Template
from VLE.serializers import FileSerializer, PresetNodeSerializer, TemplateSerializer
from VLE.utils import generic_utils as utils
from VLE.utils.error_handling import VLEProgrammingError


class FormatAPITest(TestCase):
    def setUp(self):
        self.teacher = factory.Teacher()
        self.admin = factory.Admin()
        self.course = factory.Course(author=self.teacher)
        self.assignment = factory.Assignment(courses=[self.course])
        self.format = self.assignment.format
        self.template = factory.Template(format=self.format)
        self.update_dict = {
            'assignment_details': {
                'name': 'Colloq',
                'description': 'description1',
                'is_published': True
            },
            'templates': TemplateSerializer(self.format.template_set.filter(archived=False), many=True).data,
            'removed_presets': [],
            'removed_templates': [],
            'presets': []
        }

    def test_format_factory(self):
        self.assertRaises(VLEProgrammingError, factory.Format)
        assignment = factory.Assignment(format__templates=[])

        template = factory.TemplateAllTypes(format=assignment.format)
        assert template.format.pk == assignment.format.pk and assignment.format.template_set.count() == 1 \
            and assignment.format.template_set.get(pk=template.pk), \
            'A format can be generated via an assignment, and its templates can be set'

        assignment = factory.Assignment(format__templates=[{'type': Field.URL}])
        assert assignment.format.template_set.count() == 1, 'One template is created'
        field = Field.objects.get(template=assignment.format.template_set.first())
        assert field.type == Field.URL, 'And the template consists only out of the specified field'

    def test_template_without_format(self):
        self.assertRaises(IntegrityError, factory.Template)

    def test_template_factory(self):
        assignment = factory.Assignment()

        t_c = Template.objects.count()
        a_c = Assignment.objects.count()
        j_c = Journal.objects.count()
        c_c = Course.objects.count()
        f_c = Format.objects.count()

        template = factory.Template(format=assignment.format)
        assert not template.field_set.exists(), 'By default a template should be iniated without fields'

        assert f_c == Format.objects.count(), 'No additional format is generated'
        assert a_c == Assignment.objects.count(), 'No additional assignment should be generated'
        assert c_c == Course.objects.count(), 'No additional course should be generated'
        assert j_c == Journal.objects.count(), 'No journals should be generated'
        assert t_c + 1 == Template.objects.count(), 'One template should be generated'

    def test_template_delete_with_content(self):
        format = factory.Assignment(format__templates=[]).format
        template = factory.MentorgesprekTemplate(format=format)

        # It should be no issue to delete a template without content
        template.delete()

        template = factory.MentorgesprekTemplate(format=format)
        factory.Journal(assignment=format.assignment, entries__n=1)

        # If any content relies on a template, it should not be possible to delete the template
        self.assertRaises(VLEProgrammingError, template.delete)

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
        factory.UnlimitedEntry(node__journal__assignment=self.assignment)
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

    def test_update_presets(self):
        should_be_updated = {
            'description': 'newly updated description',
            'unlock_date': timezone.now() + relativedelta(days=1),
        }
        assignment = factory.Assignment()
        # This should not use the factory, as that kills the testing of updating presets
        entrydeadline = PresetNode.objects.create(
            forced_template=assignment.format.template_set.first(),
            format=assignment.format,
            type=Node.ENTRYDEADLINE,
            due_date=timezone.now()
        )
        # This should not use the factory, as that kills the testing of updating presets
        progress = PresetNode.objects.create(
            format=assignment.format,
            type=Node.PROGRESS,
            due_date=timezone.now(),
            target=5,
        )
        presets = PresetNodeSerializer([entrydeadline, progress], many=True).data
        # Update the entry data
        presets[0].update(should_be_updated)
        utils.update_presets(assignment.author, assignment, presets, {})
        entrydeadline.refresh_from_db()
        for key, value in should_be_updated.items():
            assert getattr(entrydeadline, key) == value
            assert getattr(progress, key) != value

        # Update the template of the entry
        presets = PresetNodeSerializer([entrydeadline, progress], many=True).data
        new_template = factory.Template(format=assignment.format)

        utils.update_presets(
            assignment.author, assignment, presets, {entrydeadline.forced_template.pk: new_template.pk})
        entrydeadline.refresh_from_db()
        assert entrydeadline.forced_template == new_template, 'Template should be updated'

        # Unrelated template should not be updated
        presets = PresetNodeSerializer([entrydeadline, progress], many=True).data
        video = SimpleUploadedFile('file.mp4', b'file_content', content_type='video/mp4')
        file = FileContext.objects.create(file=video, author=assignment.author, file_name=video.name)
        presets[0]['files'].append(FileSerializer(file).data)
        other_template = factory.Template(format=assignment.format)
        utils.update_presets(assignment.author, assignment, presets, {other_template.pk: new_template.pk})
        entrydeadline.refresh_from_db()
        assert entrydeadline.forced_template == new_template, 'Template should not get changed to the other template'
        assert entrydeadline.files.filter(pk=file.pk).exists()
        file.refresh_from_db()
        assert not file.is_temp

        # Presets with ID < 0 should be newly created
        journal = factory.Journal(assignment=assignment)
        old_node_count = journal.node_set.count()
        old_preset_count = assignment.format.presetnode_set.count()
        presets = PresetNodeSerializer([entrydeadline, progress], many=True).data
        video = SimpleUploadedFile('file.mp4', b'file_content', content_type='video/mp4')
        file = FileContext.objects.create(file=video, author=assignment.author, file_name=video.name)
        presets[1]['files'].append(FileSerializer(file).data)
        presets[1]['id'] = '-1'
        utils.update_presets(assignment.author, assignment, presets, {})
        journal.refresh_from_db()
        assert old_preset_count + 1 == assignment.format.presetnode_set.count(), 'Format should have a new node'
        assert old_node_count + 1 == journal.node_set.count(), 'New node should also be added to all connected journals'
        progress.refresh_from_db()
        assert PresetNode.objects.order_by('creation_date').last().files.filter(pk=file.pk).exists()
        file.refresh_from_db()
        assert not file.is_temp
