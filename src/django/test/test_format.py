import test.factory as factory
import test.utils.generic_utils
from test.utils import api

from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from VLE.models import Assignment, Course, Entry, Field, FileContext, Format, Group, Journal, Node, PresetNode, Template
from VLE.serializers import (AssignmentFormatSerializer, FileSerializer, FormatSerializer, PresetNodeSerializer,
                             TemplateSerializer)
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

        assignment = factory.Assignment(
            format__templates=[{'type': Field.URL, 'location': 1}, {'type': Field.TEXT, 'location': 0}])
        assert assignment.format.template_set.count() == 1, 'One template is created'
        # For the template two fields are generated
        field = Field.objects.get(template=assignment.format.template_set.first(), location=0)
        field = Field.objects.get(template=assignment.format.template_set.first(), location=1)

    def test_assignment_format_update_params_factory(self):
        assignment = factory.Assignment()

        pre_update_format = AssignmentFormatSerializer(
            AssignmentFormatSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
            context={'user': assignment.author},
        ).data

        format_update_dict = factory.AssignmentFormatUpdateParams(assignment=assignment)
        api.update(self, 'formats', params=format_update_dict, user=assignment.author)

        post_update_format = AssignmentFormatSerializer(
            AssignmentFormatSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
            context={'user': assignment.author},
        ).data

        assert test.utils.generic_utils.equal_models(pre_update_format, post_update_format), \
            'Unmodified update paramaters should be able to succesfully update the format without making any changes'

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

        # Course id has to be related to the provided assignment
        unrelated_course = factory.Course()
        self.update_dict['course_id'] = unrelated_course.pk
        api.update(
                self, 'formats', params={'pk': self.assignment.pk, **self.update_dict}, user=self.teacher, status=400)
        self.update_dict['course_id'] = self.course.pk

        # Unrelated groups cannot be assigned to
        unrelated_group = factory.Group(course=unrelated_course)
        self.update_dict['assignment_details']['assigned_groups'] = [
            {'id': group.pk},
            {'id': unrelated_group.pk}
        ]
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
            due_date=timezone.now(),
            display_name=assignment.format.template_set.first().name,
        )
        # This should not use the factory, as that kills the testing of updating presets
        progress = PresetNode.objects.create(
            format=assignment.format,
            type=Node.PROGRESS,
            due_date=timezone.now(),
            target=5,
            display_name='Progress goal',
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
        presets[0]['attached_files'].append(FileSerializer(file).data)
        other_template = factory.Template(format=assignment.format)
        utils.update_presets(assignment.author, assignment, presets, {other_template.pk: new_template.pk})
        entrydeadline.refresh_from_db()
        assert entrydeadline.forced_template == new_template, 'Template should not get changed to the other template'
        assert entrydeadline.attached_files.filter(pk=file.pk).exists()
        file.refresh_from_db()
        assert not file.is_temp

        # Presets with ID < 0 should be newly created
        journal = factory.Journal(assignment=assignment)
        old_node_count = journal.node_set.count()
        old_preset_count = assignment.format.presetnode_set.count()
        presets = PresetNodeSerializer([entrydeadline, progress], many=True).data
        video = SimpleUploadedFile('file.mp4', b'file_content', content_type='video/mp4')
        file = FileContext.objects.create(file=video, author=assignment.author, file_name=video.name)
        presets[1]['attached_files'].append(FileSerializer(file).data)
        presets[1]['id'] = '-1'
        utils.update_presets(assignment.author, assignment, presets, {})
        journal = Journal.objects.get(pk=journal.pk)
        assert old_preset_count + 1 == assignment.format.presetnode_set.count(), 'Format should have a new node'
        assert old_node_count + 1 == journal.node_set.count(), 'New node should also be added to all connected journals'

        progress.refresh_from_db()
        assert PresetNode.objects.order_by('creation_date').last().attached_files.filter(pk=file.pk).exists()
        file.refresh_from_db()
        assert not file.is_temp

    def test_template_serializer(self):
        assignment = factory.Assignment(format__templates=False)
        format = assignment.format

        def check_field_set_serialization_order(serialized_template):
            for i, field in enumerate(serialized_template['field_set']):
                assert field['location'] == i, 'Fields are ordered by location'

        def test_template_list_serializer():
            factory.Template(format=format, add_fields=[
                {'type': Field.TEXT, 'location': 1}, {'type': Field.URL, 'location': 0}])
            factory.Template(format=format, add_fields=[
                {'type': Field.URL}, {'type': Field.TEXT}])

            # Minimum number of queries is performed (select templates, prefetch all fields)
            with self.assertNumQueries(2):
                data = TemplateSerializer(
                    TemplateSerializer.setup_eager_loading(format.template_set.all()),
                    many=True
                ).data

            # Fields are ordered by location
            for template in data:
                check_field_set_serialization_order(template)

        def test_template_instance_serializer():
            template = factory.Template(format=format, add_fields=[
                {'type': Field.TEXT, 'location': 1},
                {'type': Field.URL, 'location': 0}
            ])
            # Template is already in memory, we still need one query to fetch the template set
            with self.assertNumQueries(1):
                data = TemplateSerializer(template).data

            check_field_set_serialization_order(data)

        test_template_list_serializer()
        test_template_instance_serializer()

    def test_format_serializer(self):
        # Fetch the format itself (1), prefetches (presetnodes, templates, fields, field_set of forced templates 4
        # and attached_files for preset node
        expected_number_of_queries = 6
        assignment = factory.Assignment(format__templates=False)
        factory.TextTemplate(format=assignment.format)
        factory.DeadlinePresetNode(format=assignment.format)
        factory.ProgressPresetNode(format=assignment.format)

        with self.assertNumQueries(expected_number_of_queries):
            FormatSerializer(
                FormatSerializer.setup_eager_loading(Format.objects.filter(pk=assignment.format.pk)).get()
            ).data

        # Additional fields and templates have no impact on the serialization of a format
        factory.TextTemplate(format=assignment.format)
        factory.DeadlinePresetNode(format=assignment.format)
        factory.ProgressPresetNode(format=assignment.format)
        with self.assertNumQueries(expected_number_of_queries):
            FormatSerializer(
                FormatSerializer.setup_eager_loading(Format.objects.filter(pk=assignment.format.pk)).get()
            ).data
