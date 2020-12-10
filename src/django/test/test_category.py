import test.factory as factory
from copy import deepcopy
from test.utils import api
from unittest import mock

from django.db.utils import IntegrityError
from django.test import TestCase

from VLE.models import Category
from VLE.serializers import CategorySerializer


class FormatAPITest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment()
        self.category = factory.Category(assignment=self.assignment, name='aaa')

        self.valid_creation_data = {
            'name': 'Non empty',
            'description': '',
            'assignment_id': self.assignment.pk,
            'templates': list(self.assignment.format.template_set.values_list('pk', flat=True))
        }

    def test_category_factory(self):
        assert self.category.name != ''
        assert self.category.description == ''
        assert self.assignment.format.template_set.filter(pk=self.category.templates.first().pk).exists(), \
            'By default a template is randomly selected from the corresponding category\'s assignment'

    def test_category_constraints(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name='', assignment=self.assignment)

    def test_category_serializer(self):
        factory.Category(assignment=self.assignment)

        # select all categories, prefetch templates, prefetch fields
        with self.assertNumQueries(3):
            data = CategorySerializer(
                CategorySerializer.setup_eager_loading(
                    self.assignment.category_set.all()
                ),
                many=True,
            ).data

        sample = data[0]
        assert sample['id'] == self.category.pk
        assert sample['name'] == self.category.name
        assert sample['description'] == self.category.description
        assert 'templates' in sample, 'Template serialization itself is tested elsewhere'

    def test_category_list(self):
        ap = factory.AssignmentParticipation(assignment=self.assignment, user=factory.Student())

        # Categories are serialized for any participants of the provided assignment
        with mock.patch('VLE.models.User.can_view') as can_view_mock:
            api.get(self, 'categories', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            api.get(self, 'categories', params={'assignment_id': self.assignment.pk}, user=ap.user)
            can_view_mock.assert_called_with(self.assignment)

    def test_category_create(self):
        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.create(
                self, 'categories', params=self.valid_creation_data, user=self.assignment.author)['category']
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)

        assert resp['name'] == self.valid_creation_data['name']
        assert resp['description'] == self.valid_creation_data['description']
        for template in resp['templates']:
            assert template['id'] in self.valid_creation_data['templates'], 'All templates are correctly linked'

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

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.patch(self, 'categories', params=valid_patch_data, user=self.assignment.author)['category']
            check_permission_mock.assert_called_with('can_edit_assignment', category.assignment)

        assert resp['name'] == valid_patch_data['name']
        assert resp['description'] == valid_patch_data['description']
        for template in resp['templates']:
            assert template['id'] in valid_patch_data['templates'], 'All templates are correctly linked'
