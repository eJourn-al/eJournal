import test.factory as factory
from test.utils.performance import QueryContext

from django.db.utils import IntegrityError
from django.test import TestCase

from VLE.models import Assignment, Course, Field, Format, Journal, Template, TemplateChain
from VLE.serializers import TemplateSerializer
from VLE.utils.error_handling import VLEProgrammingError


class TemplateTest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment(format__templates=False)
        self.format = self.assignment.format
        self.template = factory.Template(format=self.format, name='Text', add_fields=[{'type': Field.TEXT}])
        self.journal = factory.Journal(assignment=self.assignment, entries__n=0)

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

    def test_template_create(self):
        template = Template.objects.create(format=self.format)
        assert TemplateChain.objects.filter(template=template).count() == 1, \
            'A template chain is created alongside the new template'

    def test_template_delete_with_content(self):
        format = factory.Assignment(format__templates=[]).format
        template = factory.MentorgesprekTemplate(format=format)

        # It should be no issue to delete a template without content
        template.delete()

        template = factory.MentorgesprekTemplate(format=format)
        factory.Journal(assignment=format.assignment, entries__n=1)

        # If any content relies on a template, it should not be possible to delete the template
        self.assertRaises(VLEProgrammingError, template.delete)

    def test_template_can_be_deleted(self):
        assert self.template.can_be_deleted(), \
            'Without preset nodes or entries associated with the template, it can safely be deleted'

        preset = factory.DeadlinePresetNode(forced_template=self.template, format=self.format)
        entry = factory.UnlimitedEntry(template=preset, node__journal=self.journal)
        assert not self.template.can_be_deleted(), 'Cannot delete due to dependant preset and entry'

        preset.delete()
        assert not self.template.can_be_deleted(), 'Cannot delete due to dependant entry'

        preset = factory.DeadlinePresetNode(forced_template=self.template, format=self.format)
        entry.delete()
        assert not self.template.can_be_deleted(), 'Cannot delete due to dependant preset'

        preset.delete()
        assert self.template.can_be_deleted(), 'No entry or preset remaining, entry can be deleted'

    def test_template_serializer(self):
        assignment = factory.Assignment(format__templates=False)
        format = assignment.format

        def add_state():
            factory.Template(
                format=format,
                add_fields=[{'type': Field.TEXT, 'location': 1}, {'type': Field.URL, 'location': 0}],
                categories=1,
            )

        def check_field_set_serialization_order(serialized_template):
            for i, field in enumerate(serialized_template['field_set']):
                assert field['location'] == i, 'Fields are ordered by location'

        def test_template_list_serializer():
            factory.Template(
                format=format,
                add_fields=[{'type': Field.TEXT, 'location': 1}, {'type': Field.URL, 'location': 0}],
                categories=1,
            )
            factory.Template(format=format, add_fields=[{'type': Field.URL}, {'type': Field.TEXT}])

            with QueryContext() as context_pre:
                data = TemplateSerializer(
                    TemplateSerializer.setup_eager_loading(format.template_set.all()),
                    many=True
                ).data
            add_state()
            with QueryContext() as context_post:
                data = TemplateSerializer(
                    TemplateSerializer.setup_eager_loading(format.template_set.all()),
                    many=True
                ).data

            expected_number_of_queries = len(TemplateSerializer.prefetch_related) + 1
            assert len(context_pre) == len(context_post) and len(context_pre) <= expected_number_of_queries

            # Fields are ordered by location
            for template in data:
                check_field_set_serialization_order(template)

        def test_template_instance_serializer():
            template = factory.Template(format=format, add_fields=[
                {'type': Field.TEXT, 'location': 1},
                {'type': Field.URL, 'location': 0}
            ])
            # Template is already in memory, we still need one query to fetch the template set and categories
            with self.assertNumQueries(len(TemplateSerializer.prefetch_related)):
                data = TemplateSerializer(template).data

            assert data['id'] == template.pk
            assert data['name'] == template.name
            assert data['format'] == template.format.pk
            assert data['preset_only'] == template.preset_only
            assert data['archived'] == template.archived
            assert data['fixed_categories'] == template.fixed_categories

            check_field_set_serialization_order(data)

        test_template_list_serializer()
        test_template_instance_serializer()
