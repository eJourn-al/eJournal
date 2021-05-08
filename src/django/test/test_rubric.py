import json
import test.factory as factory
from copy import deepcopy
from test.utils import api
from test.utils.generic_utils import equal_models
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

        assert self.full_rubric.criteria.count() == 2, 'A full rubric is created with 2 criteria'
        assert list(self.full_rubric.criteria.all().annotate(
            level_count=Count('levels')).values_list('level_count', flat=True)) == [3, 2], (
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
                assert [criterion['location'] for criterion in rubric['criteria']] == [0, 1], \
                    "A rubric's criteria are ordered by location"
                assert [level['location'] for level in rubric['criteria'][0]['levels']] == [0, 1, 2], \
                    "A rubric's criterion's levels are ordered by location"

    def test_rubric_list(self):
        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.get(self, 'rubrics', params={'assignment_id': self.assignment.pk}, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)

        assert len(resp['rubrics']) == self.assignment.rubrics.count()

    def test_rubric_create(self):
        params = factory.RubricCreationParams(
            assignment_id=self.assignment.pk,
            name='New name',
        )

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.create(self, 'rubrics', params=params, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', self.assignment)

        assert resp['rubric'], 'A created rubric is returned'
        assert self.assignment.rubrics.filter(pk=resp['rubric']['id']).exists(), \
            'The created rubric is linked to the correct assignment'

    def test_rubric_partial_update(self):
        params = RubricSerializer(self.full_rubric).data
        params['pk'] = self.full_rubric.pk

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.patch(self, 'rubrics', params=params, user=self.full_rubric.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', self.full_rubric.assignment)

        params.pop('pk')
        # We have to wrangle the data a bit as the test use different type dicts (default vs DRF serializer)
        original = json.dumps(params)
        patched = json.dumps(resp['rubric'])
        assert equal_models(original, patched, ignore_keys=['update_date']), \
            'Updating a rubric without making changes to the data should yield the same rubric'

        params['pk'] = self.full_rubric.pk

        new_rubric_params = factory.RubricCreationParams(assignment_id=self.assignment.pk, n_criteria=3)

        updated_data = deepcopy(params)
        updated_data['name'] = 'Some new name'
        updated_data['criteria'][1]['name'] = 'Some new name'
        updated_data['criteria'][1]['levels'][1]['name'] = 'Some new name'
        updated_data['criteria'].append(new_rubric_params['criteria'][2])

        rubric = api.patch(self, 'rubrics', params=updated_data, user=self.full_rubric.assignment.author)['rubric']

        assert rubric['name'] == 'Some new name'
        assert rubric['criteria'][1]['name'] == 'Some new name'
        assert rubric['criteria'][1]['levels'][1]['name'] == 'Some new name'
        assert rubric['criteria'][2]['name'] == new_rubric_params['criteria'][2]['name']

    def test_rubric_destroy(self):
        rubric = factory.Rubric(assignment=self.assignment)

        with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
            resp = api.delete(self, 'rubrics', params={'pk': rubric.pk}, user=self.assignment.author)
            check_permission_mock.assert_called_with('can_edit_assignment', rubric.assignment)

        assert rubric.name in resp['description'], 'Rubric name is provided in the delete response'
        assert not Rubric.objects.filter(pk=rubric.pk).exists(), 'Rubric is succesfully removed from the DB'
