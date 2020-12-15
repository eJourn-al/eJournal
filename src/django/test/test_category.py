import test.factory as factory
from copy import deepcopy
from test.factory.file_context import _fc_to_rt_img_element
from test.utils import api
from unittest import mock

from django.db.utils import IntegrityError
from django.test import TestCase

from VLE.models import Category
from VLE.serializers import CategoryConcreteFieldsSerializer, CategorySerializer


class CategoryAPITest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment()
        self.category = factory.Category(assignment=self.assignment, name='aaa', n_rt_files=1)

        self.valid_creation_data = {
            'name': 'Non empty',
            'description': '',
            'assignment_id': self.assignment.pk,
            'templates': list(self.assignment.format.template_set.values_list('pk', flat=True))
        }

    def test_category_factory(self):
        fc = self.category.filecontext_set.first()

        assert self.category.name != ''
        assert fc.access_id in self.category.description
        assert self.assignment.format.template_set.filter(pk=self.category.templates.first().pk).exists(), \
            'By default a template is randomly selected from the corresponding category\'s assignment'
        assert fc.category == self.category
        assert not fc.is_temp
        assert fc.in_rich_text

    def test_category_constraints(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name='', assignment=self.assignment)

        with self.assertRaises(IntegrityError):
            Category.objects.create(name=self.category.name, assignment=self.assignment)

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
        assert 'templates' not in sample, 'Only concrete fields should be serialized'

    def test_category_list(self):
        ap = factory.AssignmentParticipation(assignment=self.assignment, user=factory.Student())

        # Categories are serialized for any participants of the provided assignment
        with mock.patch('VLE.models.User.can_view') as can_view_mock:
            api.get(self, 'categories', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            api.get(self, 'categories', params={'assignment_id': self.assignment.pk}, user=ap.user)
            can_view_mock.assert_called_with(self.assignment)

    def test_category_create(self):
        creation_data = deepcopy(self.valid_creation_data)
        fc = factory.TempRichTextFileContext(author=self.assignment.author)
        creation_data['description'] = f"<p>TEXT</p><p>{_fc_to_rt_img_element(fc)}</p>"

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.create(
                self, 'categories', params=creation_data, user=self.assignment.author)['category']
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)

        assert resp['name'] == creation_data['name']
        assert resp['description'] == creation_data['description']
        assert len(resp['templates']) == len(creation_data['templates'])
        assert all(template['id'] in creation_data['templates'] for template in resp['templates']), \
            'All templates are correctly linked'
        fc.refresh_from_db()
        assert not fc.is_temp
        assert fc.category.pk == resp['id']

        invalid_templates = deepcopy(self.valid_creation_data)
        invalid_templates['assignment_id'] = factory.Assignment(author=self.assignment.author).pk
        api.create(self, 'categories', params=invalid_templates, user=self.assignment.author, status=400)

    def test_category_patch(self):
        category = factory.Category(assignment=self.assignment)

        valid_patch_data = {
            'name': 'Non empty',
            'pk': category.pk,
            'description': 'description',
            'templates': list(self.assignment.format.template_set.values_list('pk', flat=True))
        }

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock, mock.patch(
                'VLE.utils.file_handling.establish_rich_text') as establish_rich_text_mock:
            resp = api.patch(self, 'categories', params=valid_patch_data, user=self.assignment.author)['category']
            check_permission_mock.assert_called_with('can_edit_assignment', category.assignment)
            establish_rich_text_mock.assert_called_with(
                author=self.assignment.author, rich_text=valid_patch_data['description'], category=category)

        assert resp['name'] == valid_patch_data['name']
        assert resp['description'] == valid_patch_data['description']
        assert len(resp['templates']) == len(valid_patch_data['templates'])
        assert all(template['id'] in valid_patch_data['templates'] for template in resp['templates']), \
            'All templates are correctly linked'

    def test_category_delete(self):
        category = factory.Category(assignment=self.assignment)

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            api.delete(self, 'categories', params={'pk': category.pk}, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', category.assignment)

        assert not Category.objects.filter(pk=category.pk).exists()
