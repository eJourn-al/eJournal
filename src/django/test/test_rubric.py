import test.factory as factory
from test.utils import api
from unittest import mock

from django.db.models import Count
from django.test import TestCase

from VLE.models import Rubric
from VLE.serializers import RubricSerializer


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
        # Fetch the Rubrics, prefetch the criteria and levels
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

    def test_rubric_list(self):
        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.get(self, 'rubrics', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)

        assert len(resp['rubrics']) == self.assignment.rubrics.count()

    def test_rubric_create(self):
        assert False, 'TODO'

    def test_rubric_partial_update(self):
        assert False, 'TODO'

    def test_rubric_destroy(self):
        rubric = factory.Rubric(assignment=self.assignment)

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.delete(self, 'rubrics', params={'pk': rubric.pk}, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', rubric.assignment)

        assert rubric.name in resp['description'], 'Rubric name is provided in the delete response'
        assert not Rubric.objects.filter(pk=rubric.pk).exists(), 'Rubric is succesfully removed from the DB'
