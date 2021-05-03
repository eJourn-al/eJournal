import test.factory as factory

from django.db.models import Count
from django.test import TestCase

from VLE.models import Rubric
from VLE.serializers import RubricSerializer

# from test.utils import api


class RoleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.assignment = factory.Assignment()
        cls.rubric = factory.Rubric(assignment=cls.assignment)
        cls.full_rubric = factory.Rubric(full=True, assignment=cls.assignment)

    def test_rubric_factory(self):
        assert self.rubric.criteria.count() == 0, 'By default a rubric is created without criteria'

        assert self.full_rubric.criteria.count() == 3, 'A full rubric is created with 3 criteria'
        assert list(self.full_rubric.criteria.all().annotate(
            level_count=Count('levels')).values_list('level_count', flat=True)) == [2, 1, 0], (
            'A full rubric is created with a varied number of criterion levels. '
            'And are ordered by location'
        )

    def test_rubric_serializer(self):
        full_rubric2 = factory.Rubric(full=True, assignment=self.assignment)

        # Serializing a rubric and it's corresponding criteria and levels is done efficiently
        # Fetch the Rubric, prefetch the criteria and levels
        with self.assertNumQueries(3):
            data = RubricSerializer(
                RubricSerializer.setup_eager_loading(
                    Rubric.objects.filter(pk__in=[self.full_rubric.pk, full_rubric2.pk])
                ),
                many=True,
            ).data

        for rubric in data:
            if rubric['id'] == self.full_rubric.pk:
                assert rubric['name'] == self.full_rubric.name
                assert [criterion['location'] for criterion in rubric['criteria']] == [0, 1, 2], \
                    "A rubric's criteria are ordered by location"
                assert [level['location'] for level in rubric['criteria'][0]['levels']] == [0, 1], \
                    "A rubric's criterion's levels are ordered by location"
