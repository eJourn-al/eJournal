import test.factory as factory
from copy import deepcopy
from test.factory.file_context import _fc_to_rt_img_element
from test.utils import api
from unittest import mock

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from VLE.models import Assignment, Category, EntryCategoryLink, Field, TemplateCategoryLink
from VLE.serializers import CategoryConcreteFieldsSerializer, CategorySerializer


class CategoryAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assignment = factory.Assignment(format__templates=False)
        cls.format = cls.assignment.format
        cls.template = factory.Template(format=cls.format, add_fields=[{'type': Field.TEXT}])
        cls.assignment2 = factory.Assignment(format__templates=False)

        cls.category = factory.Category(assignment=cls.assignment, name='aaa', n_rt_files=1)

        cls.valid_creation_data = {
            'name': 'Non empty',
            'description': '',
            'color': '#FFFF',
            'assignment_id': cls.assignment.pk,
            'templates': list(cls.assignment.format.template_set.values_list('pk', flat=True))
        }

    def test_category_factory(self):
        fc = self.category.filecontext_set.first()

        assert self.category.name != ''
        assert fc.access_id in self.category.description
        assert not self.category.templates.exists(), 'By default a category is initialized without templates'
        assert fc.category == self.category
        assert not fc.is_temp
        assert fc.in_rich_text

    def test_category_constraints(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name='', assignment=self.assignment)

        with self.assertRaises(IntegrityError):
            Category.objects.create(name=self.category.name, assignment=self.assignment)

        with self.assertRaises(IntegrityError):
            Category.objects.create(color='#INVALID', name='new', assignment=self.assignment)

    def test_category_template_link_unique_contrain(self):
        TemplateCategoryLink.objects.create(
            category=self.category,
            template=self.template,
        )

        # Duplicate category template links should raise an integrity error
        with self.assertRaises(IntegrityError):
            TemplateCategoryLink.objects.create(
                category=self.category,
                template=self.template,
            )

    def test_category_serializer(self):
        factory.Category(assignment=self.assignment)

        # select all categories, prefetch templates
        with self.assertNumQueries(2):
            data = CategorySerializer(
                CategorySerializer.setup_eager_loading(
                    self.assignment.categories.all()
                ),
                many=True,
            ).data

        sample = data[0]
        assert sample['id'] == self.category.pk
        assert sample['name'] == self.category.name
        assert sample['description'] == self.category.description
        assert sample['color'] == self.category.color
        assert 'templates' in sample, 'Template serialization itself is tested elsewhere'

        # select all categories
        with self.assertNumQueries(1):
            data = CategoryConcreteFieldsSerializer(
                self.assignment.categories.all(),
                many=True,
            ).data

        sample = data[0]
        assert sample['id'] == self.category.pk
        assert sample['name'] == self.category.name
        assert sample['description'] == self.category.description
        assert sample['color'] == self.category.color
        assert 'templates' not in sample, 'Only concrete fields should be serialized'

    def test_category_list(self):
        ap = factory.AssignmentParticipation(assignment=self.assignment, user=factory.Student())

        # Categories are serialized for any participants of the provided assignment
        with mock.patch('VLE.models.User.can_view') as can_view_mock:
            api.get(self, 'categories', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            api.get(self, 'categories', params={'assignment_id': self.assignment.pk}, user=ap.user)
            can_view_mock.assert_called_with(self.assignment)

    def test_category_create(self):
        template2_of_chain = factory.Template(chain=self.template.chain, archived=True, format=self.format)

        creation_data = deepcopy(self.valid_creation_data)
        fc = factory.TempRichTextFileContext(author=self.assignment.author)
        creation_data['description'] = f"<p>TEXT</p><p>{_fc_to_rt_img_element(fc)}</p>"

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.create(
                self, 'categories', params=creation_data, user=self.assignment.author)['category']
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)

        assert resp['name'] == creation_data['name']
        assert resp['description'] == creation_data['description']
        assert resp['color'] == creation_data['color']
        assert len(resp['templates']) == len(creation_data['templates'])
        assert all(template['id'] in creation_data['templates'] for template in resp['templates']), \
            'All templates are correctly linked'
        assert template2_of_chain.categories.filter(pk=resp['id']).exists(), \
            'The category is set for all templates part of the chain by default'

        fc.refresh_from_db()
        assert not fc.is_temp
        assert fc.category.pk == resp['id']

        invalid_templates = deepcopy(self.valid_creation_data)
        invalid_templates['assignment_id'] = factory.Assignment(author=self.assignment.author).pk
        api.create(self, 'categories', params=invalid_templates, user=self.assignment.author, status=400)

    def test_category_patch(self):
        category = factory.Category(assignment=self.assignment)
        template2_of_chain = factory.Template(chain=self.template.chain, archived=True, format=self.format)

        valid_patch_data = {
            'name': 'Non empty',
            'pk': category.pk,
            'description': 'description',
            'color': '#FFFF',
            'templates': list(self.assignment.format.template_set.filter(archived=False).values_list('pk', flat=True))
        }

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock, mock.patch(
                'VLE.utils.file_handling.establish_rich_text') as establish_rich_text_mock:
            resp = api.patch(self, 'categories', params=valid_patch_data, user=self.assignment.author)['category']
            check_permission_mock.assert_called_with('can_edit_assignment', category.assignment)
            establish_rich_text_mock.assert_called_with(
                author=self.assignment.author, rich_text=valid_patch_data['description'], category=category)

        assert resp['name'] == valid_patch_data['name']
        assert resp['description'] == valid_patch_data['description']
        assert resp['color'] == valid_patch_data['color']
        assert len(resp['templates']) == len(valid_patch_data['templates'])
        assert all(template['id'] in valid_patch_data['templates'] for template in resp['templates']), \
            'All templates are correctly linked'
        assert template2_of_chain.categories.filter(pk=resp['id']).exists(), \
            'The category update affects all templates part of the chain by default'

    def test_category_delete(self):
        category = factory.Category(assignment=self.assignment)

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            api.delete(self, 'categories', params={'pk': category.pk}, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', category.assignment)

        assert not Category.objects.filter(pk=category.pk).exists()

    def test_category_edit_entry(self):
        entry = factory.UnlimitedEntry(node__journal__assignment=self.assignment)
        template = entry.template
        teacher = self.assignment.author
        student = entry.author
        params = {'pk': self.category.pk, 'entry_id': entry.pk, 'add': True}

        def test_as_student():
            assert template.fixed_categories
            for add in [True, False]:
                api.patch(self, 'categories/edit_entry', params={**params, 'add': add}, user=student, status=403)
                with mock.patch('VLE.models.User.has_permission') as has_permission_mock:
                    api.patch(self, 'categories/edit_entry', params={**params, 'add': add}, user=student, status=200)
                    has_permission_mock.assert_any_call('can_have_journal', self.assignment)
                    has_permission_mock.assert_any_call('can_grade', self.assignment)

            template.fixed_categories = False
            template.save()
            api.patch(self, 'categories/edit_entry', params={**params}, user=student)
            with mock.patch('VLE.models.User.can_edit') as can_edit_mock:
                api.patch(self, 'categories/edit_entry', params={**params}, user=student)
                can_edit_mock.assert_called_with(entry)
            assert EntryCategoryLink.objects.filter(entry=entry, category=self.category, author=student).exists(), \
                'The author is correctly set on the through M2M table.'

            assert entry.categories.filter(pk=self.category.pk).exists(), 'Category has been succesfully added'

            api.patch(self, 'categories/edit_entry', params={**params, 'add': False}, user=student)
            assert not entry.categories.filter(pk=self.category.pk).exists(), 'Category has been succesfully removed'

        def test_as_teacher():
            template.fixed_categories = True
            template.save()
            api.patch(self, 'categories/edit_entry', params={**params}, user=teacher)

            lock_date = self.assignment.lock_date
            Assignment.objects.filter(pk=self.assignment.pk).update(lock_date=timezone.now())
            api.patch(self, 'categories/edit_entry', params={**params}, user=teacher)
            Assignment.objects.filter(pk=self.assignment.pk).update(lock_date=lock_date)

        def test_as_admin():
            admin = factory.Admin()
            api.patch(self, 'categories/edit_entry', params={**params}, user=admin, status=200)

        def test_category_linked_to_entry_assignment():
            category_assignment2 = factory.Category(assignment=self.assignment2)
            api.patch(self, 'categories/edit_entry', params={**params, 'pk': category_assignment2.pk},
                      user=teacher, status=400)

        test_as_student()
        test_as_teacher()
        test_as_admin()
        test_category_linked_to_entry_assignment()

    def test_category_validate_category_data(self):
        # Name should be non empty
        self.assertRaises(ValidationError, Category.validate_category_data, name='', color='#NEW',
                          assignment=self.assignment)

        # Name and color should be unique
        self.assertRaises(ValidationError, Category.validate_category_data, name=self.category.name, color='#NEW',
                          assignment=self.assignment)
        self.assertRaises(ValidationError, Category.validate_category_data, name='NEW', color=self.category.color,
                          assignment=self.assignment)

        # Unless we update ourselves
        Category.validate_category_data(name='NEW', color=self.category.color, category=self.category,
                                        assignment=self.assignment)
        Category.validate_category_data(name=self.category.name, color='#NEW', category=self.category,
                                        assignment=self.assignment)

        # Except if another category holds those values
        cat2 = factory.Category(assignment=self.assignment)
        self.assertRaises(ValidationError, Category.validate_category_data, name=cat2.name,
                          color=self.category.color, category=self.category, assignment=self.assignment)
        self.assertRaises(ValidationError, Category.validate_category_data, name=self.category.name,
                          color=cat2.color, category=self.category, assignment=self.assignment)
