import test.factory as factory
from pprint import pprint

from django.db.utils import IntegrityError
from django.test import TestCase

from VLE.models import Category
from VLE.serializers import CategorySerializer


class FormatAPITest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment()
        self.category = factory.Category(assignment=self.assignment, name='aaa')

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
