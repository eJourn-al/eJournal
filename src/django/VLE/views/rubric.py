# from django.core.exceptions import ValidationError
# from django.db import transaction
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Rubric
from VLE.serializers import RubricSerializer


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

    def destroy(self, request, pk):
        rubric = Rubric.objects.select_related('assignment').get(pk=pk)

        request.user.check_permission('can_edit_assignment', rubric.assignment)

        rubric.delete()

        return response.success(description=f'Successfully deleted {rubric.name}.')
