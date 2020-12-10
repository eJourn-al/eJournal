import test.factory as factory

from django.test import TestCase


class FormatAPITest(TestCase):
    def setUp(self):
        self.assignment = factory.Assignment()

    def test_category_factory(self):
        category = factory.Category(assignment=self.assignment)

        assert category.name != ''
        assert category.description == ''
        assert self.assignment.format.template_set.filter(pk=category.templates.first().pk).exists(), \
            'By default a template is randomly selected from the corresponding category\'s assignment'
