import datetime
import test.factory as factory
from copy import deepcopy
from test.utils import api
from test.utils.generic_utils import check_equality_of_imported_file_context, equal_models
from test.utils.performance import QueryContext
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase

import VLE.tasks.beats.cleanup as cleanup
import VLE.utils.file_handling as file_handling
import VLE.utils.template as template_utils
from VLE.models import (Assignment, Course, EntryCategoryLink, Field, FileContext, Format, Journal, Template,
                        TemplateChain)
from VLE.serializers import TemplateSerializer
from VLE.utils.error_handling import VLEProgrammingError
from VLE.utils.file_handling import get_files_from_rich_text


def _validate_field_creation(template, field_set_params, template_import=False):
    keys_to_check = [
        'type',
        'title',
        'description',
        'options',
        'location',
        'required',
    ]

    assert len(field_set_params) == template.field_set.count(), \
        '''The number of actual fields created is equal to the number of fields provided in the request data'''

    location_set = set()
    for field_data in field_set_params:
        assert field_data['location'] not in location_set, 'Field location should be unique'
        location_set.add(field_data['location'])

        field = template.field_set.get(location=field_data['location'])
        if template_import:
            keys_to_check.remove('description')
        for key in keys_to_check:
            assert getattr(field, key) == field_data[key], f'Field {key} is correctly updated'

        for access_id in file_handling.get_access_ids_from_rich_text(field.description):
            assert FileContext.objects.filter(
                in_rich_text=True,
                assignment=template.format.assignment,
                access_id=access_id,
                is_temp=False,
            ).exists(), (
                '''The files part of the field's description are succesfully copied or no longer reflect their '''
                'initial temporary status'
            )


class TemplateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assignment = factory.Assignment(format__templates=False)
        cls.format = cls.assignment.format
        cls.template = factory.Template(format=cls.format, name='Text', add_fields=[{'type': Field.TEXT}])
        cls.category = factory.Category(assignment=cls.assignment)
        cls.journal = factory.Journal(assignment=cls.assignment, entries__n=0)
        cls.unrelated_user = factory.Student()

    def test_template_without_format(self):
        self.assertRaises(IntegrityError, factory.Template)

    def test_delete_template_with_preset_nodes(self):
        template = factory.Template(format=self.format)
        factory.DeadlinePresetNode(format=self.format, forced_template=template)
        self.assertRaises(IntegrityError, template.delete)

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

        template = factory.Template(
            format=self.assignment.format,
            allow_custom_categories=True,
            allow_custom_title=True,
            title_description='A description',
            default_grade=1,
        )
        assert template.chain.allow_custom_categories
        assert template.chain.allow_custom_title
        assert template.chain.title_description == 'A description'
        assert template.chain.default_grade == 1

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
        assert len(Template.objects.full_chain([template1_of_chain1, template1_of_chain2])) == 4, \
            'Full chain makes use of distinct to eliminate duplicate templates'

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

    def test_delete_or_archive_template(self):
        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])

        assert Template.objects.unused().filter(pk=template.pk).exists()
        assert template.can_be_deleted(), \
            'Without preset nodes or entries associated with the template, it can safely be deleted'

        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
        preset = factory.DeadlinePresetNode(forced_template=template, format=self.format)
        entry = factory.UnlimitedEntry(template=template, node__journal=self.journal)

        assert not template.can_be_deleted(), 'Cannot delete due to dependant preset and entry'
        update_params = TemplateSerializer(template).data
        update_params['name'] = 'New name, should archive'
        api.patch(self, 'templates', params={'pk': template.pk, **update_params}, user=self.assignment.author)
        template.refresh_from_db()
        assert template.archived, 'Template is archived since it could not be deleted,'
        template.archived = False
        template.save()

        preset.delete()
        update_params['name'] = 'New name2, should archive due to remaining entry'
        assert not Template.objects.unused().filter(pk=template.pk).exists()
        api.patch(self, 'templates', params={'pk': template.pk, **update_params}, user=self.assignment.author)
        template.refresh_from_db()
        assert template.archived, \
            'Template is archived since it could not be deleted as there is still an entry depending on it'
        template.archived = False
        template.save()

        entry.delete()
        update_params['name'] = 'New name3, should be deleted without any presets or entries'
        assert Template.objects.unused().filter(pk=template.pk).exists()
        api.patch(self, 'templates', params={'pk': template.pk, **update_params}, user=self.assignment.author)
        assert not Template.objects.filter(pk=template.pk).exists(), \
            'Template can be deleted without any attached entries or presets'

    def test_template_constraints(self):
        with self.assertRaises(IntegrityError):
            Template.objects.create(name='', format=self.format)

    def test_template_chain_constraints(self):
        TemplateChain.objects.create(default_grade=None, format=self.format)
        TemplateChain.objects.create(default_grade=0, format=self.format)
        TemplateChain.objects.create(default_grade=0.0, format=self.format)

        with transaction.atomic():
            self.assertRaises(IntegrityError, TemplateChain.objects.create, default_grade=-0.0001, format=self.format)

        with transaction.atomic():
            self.assertRaises(IntegrityError, TemplateChain.objects.create, default_grade=-1, format=self.format)

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

        def test_template_chain_fields_serialization():
            # Default to False and None
            template = factory.Template(format=self.format)
            data = TemplateSerializer(template).data
            assert data['allow_custom_categories'] is False
            assert data['allow_custom_title'] is True, 'By default a template allows for a custom title'
            assert data['title_description'] is None, 'By default a template title description is not set'
            assert data['default_grade'] is None, 'Float field can also serialize None value'

            # Custom values are correctly serialized
            template = factory.Template(
                format=self.format,
                allow_custom_categories=True,
                allow_custom_title=False,
                default_grade=1.0,
            )
            data = TemplateSerializer(template).data
            assert data['allow_custom_categories'] is True
            assert data['allow_custom_title'] is False
            assert data['default_grade'] == 1.0

            check_field_set_serialization_order(data)

        test_template_list_serializer()
        test_template_instance_serializer()
        test_template_chain_fields_serialization()

    def test_template_validate(self):
        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
        valid_data = TemplateSerializer(template).data
        valid_data['name'] = 'Unique name'

        def test_concrete_fields_validation():
            # White space in the name should be trimmmed
            name_with_white_space = deepcopy(valid_data)
            name = 'Name'
            name_with_white_space['name'] = name + '  '
            Template.validate(name_with_white_space, assignment=self.assignment)
            assert name_with_white_space['name'] == name, 'White space should be trimmed'

            # An empty template name is not allowed (used for identification in selects)
            empty_name = deepcopy(valid_data)
            empty_name['name'] = ''
            self.assertRaises(ValidationError, Template.validate, empty_name, self.assignment)

            # There should be no duplicate names among the active (non archived) templates
            duplicate_name = 'Duplicate'
            factory.Template(format=self.format, name=duplicate_name)
            non_unique_name = deepcopy(valid_data)
            non_unique_name['name'] = duplicate_name
            self.assertRaises(ValidationError, Template.validate, non_unique_name, self.assignment)

            # It should be possible for a duplicate name to exist, provided it belongs to an archived template
            archived_duplicate_name = 'Archived duplicate name'
            factory.Template(format=self.format, name=archived_duplicate_name, archived=True)
            archived_non_unique_name = deepcopy(valid_data)
            archived_non_unique_name['name'] = archived_duplicate_name
            Template.validate(archived_non_unique_name, assignment=self.assignment)

        def test_validate_chain_fields():
            no_default_grade = deepcopy(valid_data)
            no_default_grade['default_grade'] = None
            Template.validate(no_default_grade, assignment=self.assignment)

            zero_default_grade = deepcopy(valid_data)
            zero_default_grade['default_grade'] = 0
            Template.validate(zero_default_grade, assignment=self.assignment)

            positive_float_default_grade = deepcopy(valid_data)
            positive_float_default_grade['default_grade'] = 0.005
            Template.validate(positive_float_default_grade, assignment=self.assignment)

            negative_default_grade = deepcopy(valid_data)
            negative_default_grade['default_grade'] = -1
            self.assertRaises(ValidationError, Template.validate, negative_default_grade, self.assignment)

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

            no_fields = deepcopy(valid_data)
            no_fields['field_set'] = []
            self.assertRaises(ValidationError, Template.validate, no_fields, self.assignment)

        test_concrete_fields_validation()
        test_validate_chain_fields()
        test_category_validation()
        test_field_set_validation()

    def test_update_template_categories_of_template_chain(self):
        template1 = Template.objects.create(format=self.format, archived=True, name='A')
        template2 = Template.objects.create(format=self.format, chain=template1.chain, name='B')
        template_different_chain_with_category = factory.Template(format=self.format, categories=1)
        template_different_chain_without_category = factory.Template(format=self.format)

        category1 = factory.Category(assignment=self.assignment)
        category2 = factory.Category(assignment=self.assignment)
        categories = {category1, category2}

        template_utils.update_template_categories_of_template_chain(template2, {category1.pk, category2.pk}, set())

        for template in [template1, template2]:
            assert set(template.categories.all()) == categories, \
                'Categories are set correctly, for each template part of the chain'

        assert not template_different_chain_with_category.categories.filter(
            pk__in=[category1.pk, category2.pk]).exists(), 'Templates of a different chain are unaffected.'
        assert not template_different_chain_without_category.categories.filter(
            pk__in=[category1.pk, category2.pk]).exists(), 'Templates of a different chain are unaffected.'

    def test_template_list(self):
        factory.Template(format=self.format, archived=True)

        with mock.patch('VLE.models.User.can_view') as can_view_mock:
            resp = api.get(self, 'templates', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            can_view_mock.assert_called_with(self.assignment), 'Template list permission depends on can view assignment'
        api.get(self, 'templates', params={'assignment_id': self.assignment.pk}, user=self.unrelated_user, status=403)

        assignment_template_set = set(self.assignment.format.template_set.filter(
            archived=False).values_list('pk', flat=True))
        assert all(template['id'] in assignment_template_set for template in resp['templates']), \
            'All serialized templates belong to the provided assignment id and archived templates are not serialized'

    def test_template_create(self):
        category = factory.Category(assignment=self.assignment)
        template_title_description_temp_fc = factory.TempFileContext(author=self.assignment.author)
        template_title_description = '<p>A description</p><p><img src="{}"/></p>'.format(
            template_title_description_temp_fc.download_url(access_id=template_title_description_temp_fc.access_id)
        )

        params = factory.TemplateCreationParams(
            assignment_id=self.assignment.pk,
            n_fields_with_file_in_description=1,
            author=self.assignment.author,
            allow_custom_title=True,
            title_description=template_title_description,
            default_grade=2.0,
        )
        params['categories'] = [{'id': category.pk}]

        resp = api.create(self, 'templates', params=params, user=self.assignment.author)
        assert resp['template'], 'A created template is returned'
        assert self.assignment.format.template_set.filter(pk=resp['template']['id']).exists(), \
            'The created template is linked to the correct assignment'

        # Check if the template itself is created according to the provided data
        template = Template.objects.get(pk=resp['template']['id'])
        assert template.name == params['name']
        assert template.chain.allow_custom_categories == params['allow_custom_categories']
        assert template.chain.allow_custom_title == params['allow_custom_title']
        assert template.chain.title_description == params['title_description']
        assert template.preset_only == params['preset_only']
        assert template.chain.default_grade == params['default_grade']

        _validate_field_creation(template, params['field_set'])
        assert FileContext.objects.filter(
            in_rich_text=True,
            assignment=template.format.assignment,
            access_id=template_title_description_temp_fc.access_id,
            is_temp=False,
        ).exists(), '''The template's title description is correctly linked and no longer temporary'''
        assert set(template.categories.all()) == {category}, 'The category is correctly linked to the template'

        # When importing a template the author is required, as it is needed to set the author
        # on any field description files which are copied over.
        self.assertRaises(
            VLEProgrammingError,
            Template.objects.create_template_and_fields_from_data,
            params,
            self.assignment.format,
            template_import=True,
        )

        def test_creation_validation():
            with mock.patch('VLE.models.Template.validate', side_effect=ValidationError('msg')) as validate_mock:
                api.create(self, 'templates', params=params, user=self.assignment.author, status=400)
                validate_mock.assert_called

        def test_import_template_via_creation():
            '''
            Templates are imported into an assigment via creation based on the serialized template of another
            assignment.

            Any files need to be copied.
            '''
            other_assignment = factory.Assignment(author=self.assignment.author)

            other_template = factory.Template(
                format=other_assignment.format,
                name='To import',
                add_fields=[{'type': Field.TEXT}],
                allow_custom_categories=True,
                allow_custom_title=True,
                title_description='Some description',
            )
            other_template_title_description_fc = factory.RichTextTemplateTitleDescriptionFileContext(
                assignment=other_assignment,
                template=other_template,
            )
            other_template_field = other_template.field_set.first()
            other_template_field_fc = factory.RichTextFieldDescriptionFileContext(
                assignment=other_assignment, field=other_template_field)

            # We will import the template via the creation of the other templates serialized data
            import_params = TemplateSerializer(other_template).data
            import_params['assignment_id'] = self.assignment.pk
            import_params['template_import'] = True
            resp = api.create(self, 'templates', params=import_params, user=self.assignment.author)

            imported_template = Template.objects.get(pk=resp['template']['id'])

            # Check if the template itself is created according to the provided data
            assert imported_template.name == import_params['name']
            assert imported_template.chain.allow_custom_categories == import_params['allow_custom_categories']
            assert imported_template.chain.allow_custom_title == import_params['allow_custom_title']
            assert not imported_template.chain.title_description == import_params['title_description'], \
                'Title description should be updated to contain the copied file\'s access id'
            assert imported_template.preset_only == import_params['preset_only']
            _validate_field_creation(imported_template, import_params['field_set'], template_import=True)
            assert not imported_template.categories.all().exists(), \
                'Importing a template does not also import all of its categories'

            # Check if the RT field descriptions file copy was succesfull
            fc_ignore_keys = ['last_edited', 'creation_date', 'update_date', 'id', 'access_id', 'assignment']

            imported_template_field = imported_template.field_set.get(location=other_template_field.location)
            imported_template_field_fc = get_files_from_rich_text(imported_template_field.description).first()

            imported_template_title_description_fc = get_files_from_rich_text(
                imported_template.chain.title_description).first()

            # Files are copied succesfully
            check_equality_of_imported_file_context(other_template_field_fc, imported_template_field_fc, fc_ignore_keys)
            check_equality_of_imported_file_context(
                other_template_title_description_fc, imported_template_title_description_fc, fc_ignore_keys)

            # Remove the file from the other template's field description
            other_template_field.description = ''
            other_template_field.save()
            cleanup.remove_unused_files(datetime.datetime.now())
            assert not FileContext.objects.filter(pk=other_template_field_fc.pk).exists(), \
                'Source file in the template field description is succesfully deleted.'
            assert FileContext.objects.filter(pk=imported_template_field_fc.pk).exists(), \
                'Imported file in the template field description remains.'

            # Remove the file from the other template's title description
            other_template.chain.title_description = ''
            other_template.chain.save()
            cleanup.remove_unused_files(datetime.datetime.now())
            assert not FileContext.objects.filter(pk=other_template_title_description_fc.pk).exists(), \
                'Source file in the template title description is succesfully deleted.'
            assert FileContext.objects.filter(pk=imported_template_title_description_fc.pk).exists(), \
                'Imported file in the template title description remains.'

            other_assignment.delete()
            cleanup.remove_unused_files(datetime.datetime.now())
            assert FileContext.objects.filter(pk=imported_template_field_fc.pk).exists(), \
                'Deleting the source assignment should have no impact on the copied files.'
            assert FileContext.objects.filter(pk=imported_template_title_description_fc.pk).exists(), \
                'Deleting the source assignment should have no impact on the copied files.'

            # When no longer referenced the files SHOULD be removed by cleanup
            imported_template_field.description = ''
            imported_template_field.save()
            imported_template.chain.title_description = ''
            imported_template.chain.save()
            cleanup.remove_unused_files(datetime.datetime.now())
            assert not FileContext.objects.filter(pk=other_template_field_fc.pk).exists(), \
                'When a RT field description file is no longer referenced in the RT, cleanup should remove the file.'
            assert not FileContext.objects.filter(pk=imported_template_title_description_fc.pk).exists(), \
                'When a RT field description file is no longer referenced in the RT, cleanup should remove the file.'

        test_creation_validation()
        test_import_template_via_creation()

    def test_template_patch(self):
        def test_used_template_patch():
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            factory.UnlimitedEntry(node__journal=self.journal, template=template)
            temp_fc = factory.TempFileContext(author=self.assignment.author)
            field_description_with_temp_file = f'<img src="{temp_fc.download_url(access_id=temp_fc.access_id)}"/>'
            template_title_description_temp_fc = factory.TempFileContext(author=self.assignment.author)
            template_title_description = '<p>A description</p><p><img src="{}"/></p>'.format(
                template_title_description_temp_fc.download_url(access_id=template_title_description_temp_fc.access_id)
            )

            valid_patch_data = TemplateSerializer(template).data
            valid_patch_data['name'] = 'New'
            valid_patch_data['allow_custom_categories'] = True
            valid_patch_data['allow_custom_title'] = True
            valid_patch_data['title_description'] = template_title_description
            valid_patch_data['default_grade'] = 3.0
            valid_patch_data['archived'] = True
            valid_patch_data['pk'] = template.pk
            new_field_data = deepcopy(valid_patch_data['field_set'][0])
            new_field_data['location'] = valid_patch_data['field_set'][0]['location'] + 1
            new_field_data['description'] = field_description_with_temp_file
            valid_patch_data['field_set'].append(new_field_data)

            with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
                resp = api.patch(self, 'templates', params=valid_patch_data, user=self.assignment.author)
                check_permission_mock.assert_called_with('can_edit_assignment', template.format.assignment)

            archived_template = Template.objects.get(pk=template.pk)
            new_template = Template.objects.get(pk=resp['template']['id'])

            assert valid_patch_data['name'] == new_template.name
            assert valid_patch_data['allow_custom_categories'] == new_template.chain.allow_custom_categories
            assert valid_patch_data['allow_custom_title'] == new_template.chain.allow_custom_title
            assert valid_patch_data['title_description'] == new_template.chain.title_description
            assert valid_patch_data['default_grade'] == new_template.chain.default_grade
            assert not new_template.archived, 'Archived should be ignored as request data'
            _validate_field_creation(new_template, valid_patch_data['field_set'])
            assert FileContext.objects.filter(
                in_rich_text=True,
                assignment=template.format.assignment,
                access_id=template_title_description_temp_fc.access_id,
                is_temp=False,
            ).exists(), '''The template's title description is correctly linked and no longer temporary'''

            assert equal_models(template, archived_template, ignore_keys=['update_date', 'archived']), \
                'The archived template should not be modified'

            remove_default_grade = TemplateSerializer(template).data
            remove_default_grade['default_grade'] = ''
            remove_default_grade['pk'] = template.pk
            api.patch(self, 'templates', params=remove_default_grade, user=self.assignment.author)
            assert template.chain.default_grade is None, 'Default grade is succesfully removed'

        def test_unused_template_patch():
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])

            valid_patch_data = TemplateSerializer(template).data
            valid_patch_data['name'] = 'New 2'
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

        def test_should_be_archived():
            # Archive a template via updating a fields title
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}, {'type': Field.URL}])
            field_loc_0 = template.field_set.get(location=0)
            factory.UnlimitedEntry(node__journal=self.journal, template=template)
            field_name_modified = TemplateSerializer(template).data
            field_name_modified['pk'] = template.pk
            field_name_modified['field_set'][0]['title'] = 'New title'
            assert template_utils._field_concrete_fields_updated(field_loc_0, field_name_modified['field_set'][0]), \
                '''Updating a field's title should mark it as updated'''
            resp = api.patch(self, 'templates', params=field_name_modified, user=self.assignment.author)
            template.refresh_from_db()
            assert template.archived, 'Template is archived as its field set was updated'
            assert resp['template']['field_set'][0]['title'] == 'New title'

            # Archive a template via updating a fields location
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}, {'type': Field.URL}])
            field_loc_0 = template.field_set.get(location=0)
            factory.UnlimitedEntry(node__journal=self.journal, template=template)
            field_location_modified = TemplateSerializer(template).data
            field_location_modified['pk'] = template.pk
            assert field_location_modified['field_set'][0]['location'] != 1
            field_location_modified['field_set'][0]['location'] = 1
            field_location_modified['field_set'][1]['location'] = 0
            assert template_utils._field_concrete_fields_updated(field_loc_0, field_location_modified['field_set'][0]),\
                '''Updating a field's location should mark it as updated'''
            resp = api.patch(self, 'templates', params=field_location_modified, user=self.assignment.author)
            template.refresh_from_db()
            assert template.archived, 'Template is archived as its field set was updated'
            assert resp['template']['field_set'][0]['type'] == Field.URL, 'Field locations are correctly swapped'

            # Deleting a field from the field set should mark a template to be archived
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}, {'type': Field.URL}])
            factory.UnlimitedEntry(node__journal=self.journal, template=template)
            field_deleted = TemplateSerializer(template).data
            field_deleted['pk'] = template.pk
            del field_deleted['field_set'][1]
            assert template_utils._field_set_updated(template, field_deleted), \
                '''Removing a field from a templates field set should mark it as updated'''
            resp = api.patch(self, 'templates', params=field_deleted, user=self.assignment.author)
            template.refresh_from_db()
            assert template.archived, 'Template is archived as its field set was updated'
            assert Template.objects.get(pk=resp['template']['id']).field_set.count() == 1, \
                'Field set is indeed reduced by one'

            # Changing nothing should not archive the template
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            factory.UnlimitedEntry(node__journal=self.journal, template=template)
            unchanged = TemplateSerializer(template).data
            unchanged['pk'] = template.pk
            assert not template_utils._should_be_archived(template, unchanged)
            api.patch(self, 'templates', params=unchanged, user=self.assignment.author)
            template.refresh_from_db()
            assert not template.archived

        def test_update_allow_custom_categories_flag():
            template = factory.Template(
                format=self.format, add_fields=[{'type': Field.TEXT}], allow_custom_categories=True)
            # Ensure the template is not deleted, by linking it to an entry
            factory.UnlimitedEntry(node__journal__assignment=self.assignment, template=template)

            patch_data = TemplateSerializer(template).data
            patch_data['pk'] = template.pk
            patch_data['allow_custom_categories'] = False

            api.patch(self, 'templates', params=patch_data, user=self.assignment.author)

            template.refresh_from_db()
            assert not template.archived, 'Changing the allow_custom_categories flag does not archive the template.'
            assert not template.chain.allow_custom_categories, 'Custom categories flag is updated.'

        def test_update_template_categories_updates_entry_categories_using_template():
            template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
            entry_archived_template = factory.UnlimitedEntry(node__journal=self.journal, template=template)
            category_1 = factory.Category(assignment=self.assignment)

            # Set a new title so we archive the original template
            new_name = TemplateSerializer(template).data
            new_name['name'] = 'A new name, this should archive the template'
            new_name['pk'] = template.pk
            resp = api.patch(self, 'templates', params=new_name, user=self.assignment.author)
            assert resp['template']['id'] != template.pk
            archived_template = Template.objects.get(pk=template.pk, archived=True)
            new_template = Template.objects.get(pk=resp['template']['id'])
            assert archived_template.chain == new_template.chain, 'Templates should still be part of the same chain'

            # A user now creates another entry (now using the new template)
            entry_new_template = factory.UnlimitedEntry(node__journal=self.journal, template=new_template)

            # Adding a category should update all entries using said template, archived or not
            add_category = TemplateSerializer(new_template).data
            add_category['categories'] = [{'id': category_1.pk}]
            add_category['pk'] = new_template.pk
            resp = api.patch(self, 'templates', params=add_category, user=self.assignment.author)
            updated_template = Template.objects.get(pk=resp['template']['id'])
            assert updated_template == new_template, \
                '''Only updating a template's categories should not archive the template'''
            assert entry_new_template.categories.filter(pk=category_1.pk).exists(), \
                '''Updating a template's categories should update any entry categories using the template'''
            assert entry_archived_template.categories.filter(pk=category_1.pk).exists(), (
                '''Updating a template's categories should also update the categories of any entries using an'''
                'archived version of the template (sharing the same template chain).'
            )

            # Categories which are added manually to an entry should be unaffected by the template category update
            category_2 = factory.Category(assignment=self.assignment)
            EntryCategoryLink.objects.create(
                category=category_2, entry=entry_new_template, author=entry_new_template.author)
            remove_categories = deepcopy(add_category)
            remove_categories['categories'] = []

            api.patch(self, 'templates', params=remove_categories, user=self.assignment.author)
            assert not new_template.categories.exists(), 'All categories are removed from the Template'
            assert set(entry_new_template.categories.all()) == set([category_2]), \
                'Despite removing all categories from the template, an unrelated manual category addition is unaffected'

            # Unless manual edits conflict with the difference of the template category update, in this case
            # manual edits are overwritten (seen as an acceptible risk)
            new_template.categories.set([category_2])  # Category is introduced to the template by the educator
            api.patch(self, 'templates', params=remove_categories, user=self.assignment.author)
            assert not entry_new_template.categories.filter(pk=category_2.pk).exists(), (
                'The category which was introduced by a TA or Student earlier, is removed from the entry via an update '
                "to the TEMPLATE's default categories. This scenario should be rare and is therefore acceptable"
            )

        test_used_template_patch()
        test_unused_template_patch()
        test_patch_validation()
        test_should_be_archived()
        test_update_allow_custom_categories_flag()
        test_update_template_categories_updates_entry_categories_using_template()

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
            deadline = factory.DeadlinePresetNode(format=self.format, forced_template=template)
            resp = api.delete(self, 'templates', params={'pk': template.pk}, user=self.assignment.author, status=400)
            assert Template.objects.filter(pk=template.pk, archived=False).exists(), \
                '''A used template (a deadline exists which makes use of the template) cannot be deleted, the user is
                asked to changed the deadline first instead.'''
            assert deadline.display_name in resp['description'], \
                'The user is informed which deadlines depend on the template.'

        test_unused_template_delete()
        test_used_template_archive()
