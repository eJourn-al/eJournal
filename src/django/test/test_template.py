import test.factory as factory
from copy import deepcopy
from test.utils import api
from test.utils.generic_utils import equal_models
from test.utils.performance import QueryContext
from unittest import mock

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

import VLE.utils.template as template_utils
from VLE.models import Assignment, Course, Field, Format, Journal, Template, TemplateChain
from VLE.serializers import TemplateSerializer
from VLE.utils.error_handling import VLEProgrammingError


def _validate_field_creation(template, field_set_params):
    assert len(field_set_params) == template.field_set.count()

    location_set = set()
    for field in field_set_params:
        assert field['location'] not in location_set, 'Field location should be unique'
        location_set.add(field['location'])

        assert template.field_set.filter(
            type=field['type'],
            title=field['title'],
            description=field['description'],
            options=field['options'],
            location=field['location'],
            required=field['required'],
        ).exists(), 'The templates created field set matches the provided data'


class TemplateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assignment = factory.Assignment(format__templates=False)
        cls.format = cls.assignment.format
        cls.template = factory.Template(format=cls.format, name='Text', add_fields=[{'type': Field.TEXT}])
        cls.category = factory.Category(assignment=cls.assignment)
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
        template1_of_chain1 = Template.objects.create(format=self.format, name='A')
        template1_of_chain2 = Template.objects.create(format=self.format, name='B')

        assert Template.objects.full_chain(template1_of_chain1).get() == template1_of_chain1, \
            'The full chain of a single template is the template itself'

        template2_of_chain1 = Template.objects.create(format=self.format, chain=template1_of_chain1.chain, name='C')
        assert template2_of_chain1.chain == template1_of_chain1.chain
        full_chain1 = set([template1_of_chain1, template2_of_chain1])
        # Full chain yields all templates part of the chain regardless which template we start with.
        assert set(Template.objects.full_chain(template1_of_chain1)) == full_chain1
        assert set(Template.objects.full_chain(template2_of_chain1)) == full_chain1

        # Full chain also works for templates part of different chains, all templates part their respective chains
        # should be queried.
        template2_of_chain2 = Template.objects.create(format=self.format, chain=template1_of_chain2.chain, name='D')
        full_chain2 = set([template1_of_chain2, template2_of_chain2])
        assert set(Template.objects.full_chain([template1_of_chain1, template1_of_chain2])) \
            == full_chain1.union(full_chain2)

    def test_template_manager_create(self):
        template = Template.objects.create(format=self.format, name='A')
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

    def test_template_constraints(self):
        with self.assertRaises(IntegrityError):
            Template.objects.create(name='', format=self.format)

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

    def test_template_validate(self):
        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
        valid_data = TemplateSerializer(template).data

        def test_concrete_fields_validation():
            name_with_white_space = deepcopy(valid_data)
            name = 'Name'
            name_with_white_space['name'] = name + '  '
            Template.validate(name_with_white_space, assignment=self.assignment)
            assert name_with_white_space['name'] == name, 'White space should be trimmed'

            empty_name = deepcopy(valid_data)
            empty_name['name'] = ''
            self.assertRaises(ValidationError, Template.validate, empty_name, self.assignment)

        def test_category_validation():
            category = factory.Category(assignment=self.assignment)
            unrelated_category = factory.Category()

            duplicate_category = deepcopy(valid_data)
            duplicate_category['categories'] = [{'id': category.pk}, {'id': category.pk}]
            self.assertRaises(ValidationError, Template.validate, duplicate_category, self.assignment)

            category_from_different_assignment = deepcopy(valid_data)
            category_from_different_assignment['categories'] = [{'id': category.pk}, {'id': unrelated_category.pk}]
            self.assertRaises(ValidationError, Template.validate, category_from_different_assignment, self.assignment)

        def test_field_set_validation():
            duplicate_field_locations = deepcopy(valid_data)
            duplicate_field_locations['field_set'] = [{'location': 0}, {'location': 0}]
            self.assertRaises(ValidationError, Template.validate, duplicate_field_locations, self.assignment)

            oob_field_locations = deepcopy(valid_data)
            oob_field_locations['field_set'] = [{'location': 0}, {'location': -1}]
            self.assertRaises(ValidationError, Template.validate, oob_field_locations, self.assignment)

            oob_field_locations = deepcopy(valid_data)
            oob_field_locations['field_set'] = [{'location': 0}, {'location': 2}]
            self.assertRaises(ValidationError, Template.validate, oob_field_locations, self.assignment)

        test_concrete_fields_validation()
        test_category_validation()
        test_field_set_validation()

    def test_update_categories_of_template_chain(self):
        template1 = Template.objects.create(format=self.format, archived=True, name='A')
        template2 = Template.objects.create(format=self.format, chain=template1.chain, name='B')
        template_different_chain_with_category = factory.Template(format=self.format, categories=1)
        template_different_chain_without_category = factory.Template(format=self.format)

        category1 = factory.Category(assignment=self.assignment)
        category2 = factory.Category(assignment=self.assignment)
        categories = {category1, category2}

        data = {'categories': [{'id': category.pk} for category in categories]}
        template_utils.update_categories_of_template_chain(data, template2)

        for template in [template1, template2]:
            assert set(template.categories.all()) == categories, \
                'Categories are set correctly, for each template part of the chain'

        assert not template_different_chain_with_category.categories.filter(
            pk__in=[category1.pk, category2.pk]).exists(), 'Templates of a different chain are unaffected.'
        assert not template_different_chain_without_category.categories.filter(
            pk__in=[category1.pk, category2.pk]).exists(), 'Templates of a different chain are unaffected.'

    def test_template_list(self):
        with mock.patch('VLE.models.User.can_view') as can_view_mock:
            resp = api.get(self, 'templates', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            can_view_mock.assert_called_with(self.assignment), 'Template list permission depends on can view assignment'

        assignment_template_set = set(self.assignment.format.template_set.values_list('pk', flat=True))
        assert all(template['id'] in assignment_template_set for template in resp['templates']), \
            'All serialized templates belong to the provided assignment id'

    def test_template_create(self):
        category = factory.Category(assignment=self.assignment)

        params = factory.TemplateCreationParams(assignment_id=self.assignment.pk)
        params['categories'] = [{'id': category.pk}]

        resp = api.create(self, 'templates', params=params, user=self.assignment.author)
        assert resp['template'], 'A create template is returned'
        assert self.assignment.format.template_set.filter(pk=resp['template']['id']).exists(), \
            'The created template is linked to the correct assignment'

        # Check if the template itself is created according to the provided data
        template = Template.objects.get(pk=resp['template']['id'])
        assert template.name == params['name']
        assert template.fixed_categories == params['fixed_categories']
        assert template.preset_only == params['preset_only']

        _validate_field_creation(template, params['field_set'])
        assert set(template.categories.all()) == {category}, 'The category is correctly linked to the template'

        def test_creation_validation():
            with mock.patch('VLE.models.Template.validate', side_effect=ValidationError('msg')) as validate_mock:
                api.create(self, 'templates', params=params, user=self.assignment.author, status=400)
                validate_mock.assert_called

        test_creation_validation()

    def test_template_patch(self):
        def test_used_template_patch():
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            factory.UnlimitedEntry(node__journal=self.journal, template=template)

            valid_patch_data = TemplateSerializer(template).data
            valid_patch_data['name'] = 'New'
            valid_patch_data['fixed_categories'] = False
            valid_patch_data['archived'] = True
            valid_patch_data['pk'] = template.pk
            new_field_data = deepcopy(valid_patch_data['field_set'][0])
            new_field_data['location'] = valid_patch_data['field_set'][0]['location'] + 1
            valid_patch_data['field_set'].append(new_field_data)

            with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
                resp = api.patch(self, 'templates', params=valid_patch_data, user=self.assignment.author)
                check_permission_mock.assert_called_with('can_edit_assignment', template.format.assignment)

            archived_template = Template.objects.get(pk=template.pk)
            new_template = Template.objects.get(pk=resp['template']['id'])

            assert valid_patch_data['name'] == new_template.name
            assert valid_patch_data['fixed_categories'] == new_template.fixed_categories
            assert not new_template.archived, 'Archived should be ignored as request data'
            _validate_field_creation(new_template, valid_patch_data['field_set'])

            assert equal_models(template, archived_template, ignore_keys=['update_date', 'archived']), \
                'The archived template should not be modified'

        def test_unused_template_patch():
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])

            valid_patch_data = TemplateSerializer(template).data
            valid_patch_data['name'] = 'New'
            valid_patch_data['pk'] = template.pk

            resp = api.patch(self, 'templates', params=valid_patch_data, user=self.assignment.author)

            assert not Template.objects.filter(pk=template.pk).exists(), \
                'An unused template should simply be removed instead of archived when updated.'

            new_template = Template.objects.get(pk=resp['template']['id'])
            assert valid_patch_data['name'] == new_template.name
            _validate_field_creation(new_template, valid_patch_data['field_set'])

        def test_patch_validation():
            template = factory.Template(format=self.format)

            patch_data = TemplateSerializer(template).data
            patch_data['pk'] = template.pk

            with mock.patch('VLE.models.Template.validate', side_effect=ValidationError('msg')) as validate_mock:
                api.patch(self, 'templates', params=patch_data, user=self.assignment.author, status=400)
                validate_mock.assert_called

        test_used_template_patch()
        test_unused_template_patch()
        test_patch_validation()

    def test_template_delete(self):
        def test_unused_template_delete():
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            self.category.templates.add(template)

            with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
                resp = api.delete(self, 'templates', params={'pk': template.pk}, user=self.assignment.author)
                check_permission_mock.assert_called_with('can_edit_assignment', template.format.assignment)

            assert template.name in resp['description'], 'The deleted templates name is part of the success message'
            assert not Template.objects.filter(pk=template.pk).exists(), \
                'The template is successfully removed from the DB'
            assert not Field.objects.filter(template=template).exists(), \
                '''The template's field set is deleted alongside the template'''
            assert not self.category.templates.filter(pk=template.pk).exists(), \
                '''Any category template links are deleted alongside the template'''

        def test_used_template_archive():
            # Test usage via an unlimited entry
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            factory.UnlimitedEntry(node__journal=self.journal, template=template)

            api.delete(self, 'templates', params={'pk': template.pk}, user=self.assignment.author)
            template.refresh_from_db()
            assert template.archived, \
                '''A used template (an entry exists which relies on the template) should be archived
                instead of actually deleted'''

            # Test usage via a preset node
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            factory.DeadlinePresetNode(format=self.format, forced_template=template)

            api.delete(self, 'templates', params={'pk': template.pk}, user=self.assignment.author)
            template.refresh_from_db()
            assert template.archived, \
                '''A used template (a deadline exists which makes use of the template)
                should be archived instead of actually deleted'''

        test_unused_template_delete()
        test_used_template_archive()
