import test.factory as factory
from test.utils.performance import QueryContext

from django.db.utils import IntegrityError
from django.test import TestCase

import VLE.utils.template as template_utils
from VLE.models import Assignment, Course, Field, Format, Journal, Template, TemplateChain
from VLE.serializers import TemplateSerializer
from VLE.utils.error_handling import VLEProgrammingError


class TemplateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assignment = factory.Assignment(format__templates=False)
        cls.format = cls.assignment.format
        cls.template = factory.Template(format=cls.format, name='Text', add_fields=[{'type': Field.TEXT}])
        cls.journal = factory.Journal(assignment=cls.assignment, entries__n=0)

    def test_template_without_format(self):
        self.assertRaises(IntegrityError, factory.Template)

    def test_template_factory(self):
        t_c = Template.objects.count()
        a_c = Assignment.objects.count()
        j_c = Journal.objects.count()
        c_c = Course.objects.count()
        f_c = Format.objects.count()

        template = factory.Template(format=self.assignment.format)
        assert not template.field_set.exists(), 'By default a template should be initialized without fields'

        assert f_c == Format.objects.count(), 'No additional format is generated'
        assert a_c == Assignment.objects.count(), 'No additional assignment should be generated'
        assert c_c == Course.objects.count(), 'No additional course should be generated'
        assert j_c == Journal.objects.count(), 'No journals should be generated'
        assert t_c + 1 == Template.objects.count(), 'One template should be generated'

    def test_full_chain(self):
        template1_of_chain1 = Template.objects.create(format=self.format)
        template1_of_chain2 = Template.objects.create(format=self.format)

        assert Template.objects.full_chain(template1_of_chain1).get() == template1_of_chain1, \
            'The full chain of a single template is the template itself'

        template2_of_chain1 = Template.objects.create(format=self.format, chain=template1_of_chain1.chain)
        assert template2_of_chain1.chain == template1_of_chain1.chain
        full_chain1 = set([template1_of_chain1, template2_of_chain1])
        # Full chain yields all templates part of the chain regardless which template we start with.
        assert set(Template.objects.full_chain(template1_of_chain1)) == full_chain1
        assert set(Template.objects.full_chain(template2_of_chain1)) == full_chain1

        # Full chain also works for templates part of different chains, all templates part their respective chains
        # should be queried.
        template2_of_chain2 = Template.objects.create(format=self.format, chain=template1_of_chain2.chain)
        full_chain2 = set([template1_of_chain2, template2_of_chain2])
        assert set(Template.objects.full_chain([template1_of_chain1, template1_of_chain2])) \
            == full_chain1.union(full_chain2)

    def test_template_create(self):
        template = Template.objects.create(format=self.format)
        assert TemplateChain.objects.filter(template=template).count() == 1, \
            'A template chain is created alongside the new template'

    def test_delete_floating_empty_template_chain(self):
        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
        chain = template.chain
        assert chain.template_set.count() == 1
        template.delete()
        assert not TemplateChain.objects.filter(pk=chain.pk).exists()

    def test_template_delete_with_content(self):
        template = factory.MentorgesprekTemplate(format=self.format)

        # It should be no issue to delete a template without content
        template.delete()

        template = factory.MentorgesprekTemplate(format=self.format)
        factory.UnlimitedEntry(node__journal=self.journal, template=template)

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

    def test_delete_or_archive_templates_and_test_template_unused(self):
        template = self.template
        data = [{'id': template.pk}]

        assert Template.objects.unused().filter(pk=template.pk).exists()
        template_utils.delete_or_archive_templates(data)
        assert not Template.objects.filter(pk=template.pk).exists(), \
            'Without preset nodes or entries associated with the template, it can safely be deleted'

        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
        data = [{'id': template.pk}]
        preset = factory.DeadlinePresetNode(forced_template=template, format=self.format)
        entry = factory.UnlimitedEntry(template=template, node__journal=self.journal)
        template_utils.delete_or_archive_templates(data)
        template.refresh_from_db()
        assert not Template.objects.unused().filter(pk=template.pk).exists()
        assert template.archived, 'Cannot delete due to dependant preset and entry'
        template.archived = False
        template.save()

        preset.delete()
        template_utils.delete_or_archive_templates(data)
        template.refresh_from_db()
        assert not Template.objects.unused().filter(pk=template.pk).exists()
        assert template.archived, 'Cannot delete due to dependant entry'
        template.archived = False
        template.save()

        preset = factory.DeadlinePresetNode(forced_template=template, format=self.format)
        entry.delete()
        template_utils.delete_or_archive_templates(data)
        template.refresh_from_db()
        assert not Template.objects.unused().filter(pk=template.pk).exists()
        assert template.archived, 'Cannot delete due to dependant preset'
        template.archived = False
        template.save()

        preset.delete()
        assert Template.objects.unused().filter(pk=template.pk).exists()
        template_utils.delete_or_archive_templates(data)
        assert not Template.objects.filter(pk=template.pk).exists(), \
            'Without preset nodes or entries associated with the template, it can safely be deleted'

    def test_template_serializer(self):
        format = self.format

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
            template = factory.Template(format=self.format, add_fields=[
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
