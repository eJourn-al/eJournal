# from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Criterion, Level, Rubric
from VLE.serializers import CriterionSerializer, LevelSerializer, RubricSerializer


def flatten_rubric_data(data):
    criteria = data.pop('criteria')

    levels = []
    for criterion in criteria:
        c_levels = criterion.pop('levels')
        for level in c_levels:
            levels.append(level)

    return data, criteria, levels


class RubricView(viewsets.ViewSet):
    def list(self, request):
        assignment_id, = utils.required_typed_params(request.query_params, (int, 'assignment_id'))

        assignment = Assignment.objects.get(pk=assignment_id)

        # TODO rubric: edit vs can grade, depends if list is ever used outside of creating a rubric
        request.user.check_permission('can_edit_assignment', assignment)

        serializer = RubricSerializer(
            RubricSerializer.setup_eager_loading(
                assignment.rubrics.all()
            ),
            context={'user': request.user},
            many=True,
        )

        return response.success({'rubrics': serializer.data})

    def create(self, request):
        assignment_id, = utils.required_typed_params(request.data, (int, 'assignment_id'))
        # rubric_import, = utils.optional_typed_params(request.data, (bool, 'rubric_import'))  # TODO RUBRIC IMPORT

        assignment = Assignment.objects.get(pk=assignment_id)
        request.user.check_permission('can_edit_assignment', assignment)

        request.data['assignment'] = assignment.pk
        Rubric.validate(request.data, assignment=assignment)

        with transaction.atomic():
            criteria_data = request.data.pop('criteria')
            serializer = RubricSerializer(data=request.data, context={'user': request.user})
            if not serializer.is_valid():
                return response.bad_request('One or more rubric fields contain invalid data.')
            rubric = serializer.save()

            for criterion_data in criteria_data:
                levels_data = criterion_data.pop('levels')
                criterion_data['rubric'] = rubric.pk

                serializer = CriterionSerializer(data=criterion_data, context={'user': request.user})
                if not serializer.is_valid():
                    return response.bad_request(f'Criterion {criterion_data["name"]} contains invalid data.')
                criterion = serializer.save()

                for level_data in levels_data:
                    level_data['criterion'] = criterion.pk
                serializer = LevelSerializer(data=levels_data, context={'user': request.user}, many=True)
                if not serializer.is_valid():
                    return response.bad_request(f'One or more levels contain invalid data.')
                serializer.save()

        return response.created({
            'rubric': RubricSerializer(
                RubricSerializer.setup_eager_loading(Rubric.objects.filter(pk=rubric.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def partial_update(self, request, pk):
        rubric = Rubric.objects.select_related('assignment').get(pk=pk)
        assignment = rubric.assignment

        request.user.check_permission('can_edit_assignment', assignment)

        Rubric.validate(request.data, assignment=assignment, old=rubric)

        existing_criterion_pks = set(rubric.criteria.values_list('pk', flat=True))
        existing_level_pks = set(Level.objects.filter(criterion__rubric=rubric).values_list('pk', flat=True))
        data_criterion_pks = set()
        data_level_pks = set()

        with transaction.atomic():
            criteria_data = request.data.pop('criteria')
            serializer = RubricSerializer(rubric, data=request.data, context={'user': request.user})
            if not serializer.is_valid():
                return response.bad_request('One or more rubric fields contain invalid data.')
            rubric = serializer.save()

            for criterion_data in criteria_data:
                pk, = utils.required_typed_params(criterion_data, (int, 'id'))
                data_criterion_pks.add(pk)
                levels_data = criterion_data.pop('levels')
                criterion_data['rubric'] = rubric.pk

                if pk >= 0:
                    criterion = rubric.criteria.get(pk=pk)
                    serializer = CriterionSerializer(criterion, data=criterion_data, context={'user': request.user})
                else:
                    serializer = CriterionSerializer(data=criterion_data, context={'user': request.user})

                if not serializer.is_valid():
                    return response.bad_request(f'Criterion {criterion_data.get("name")} contains invalid data.')
                criterion = serializer.save()

                for level_data in levels_data:
                    pk, = utils.required_typed_params(level_data, (int, 'id'))
                    data_level_pks.add(level_data['id'])
                    level_data['criterion'] = criterion.pk

                    if pk >= 0:
                        level = criterion.levels.get(pk=pk)
                        serializer = LevelSerializer(level, data=level_data, context={'user': request.user})
                    else:
                        serializer = LevelSerializer(data=level_data, context={'user': request.user})

                    if not serializer.is_valid():
                        return response.bad_request(f'Level {level_data.get("name")} contains invalid data.')
                    serializer.save()

            Criterion.objects.filter(pk__in=existing_criterion_pks - data_criterion_pks).delete()
            Level.objects.filter(pk__in=existing_level_pks - data_level_pks).delete()

        return response.success({
            'rubric': RubricSerializer(
                RubricSerializer.setup_eager_loading(Rubric.objects.filter(pk=rubric.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def destroy(self, request, pk):
        rubric = Rubric.objects.select_related('assignment').get(pk=pk)

        request.user.check_permission('can_edit_assignment', rubric.assignment)

        rubric.delete()

        return response.success(description=f'Successfully deleted {rubric.name}.')
