from django.db import transaction
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.utils.template as template_utils
from VLE.models import Assignment, Template
from VLE.serializers import TemplateSerializer


class TemplateView(viewsets.ViewSet):
    def list(self, request):
        assignment_id, = utils.required_typed_params(request.query_params, (int, 'assignment_id'))

        assignment = Assignment.objects.select_related('format').get(pk=assignment_id)

        if not request.user.can_view(assignment):
            return response.forbidden('You are not allowed to view this assignment.')

        serializer = TemplateSerializer(
            TemplateSerializer.setup_eager_loading(
                assignment.format.template_set.all()
            ),
            context={'user': request.user},
            many=True,
        )

        return response.success({'templates': serializer.data})

    def create(self, request):
        assignment_id, = utils.required_typed_params(request.data, (int, 'assignment_id'))

        assignment = Assignment.objects.select_related('format').get(pk=assignment_id)
        request.user.check_permission('can_edit_assignment', assignment)

        Template.validate(request.data, assignment=assignment)
        template = Template.objects.create_template_and_fields_from_data(request.data, assignment.format)

        return response.created({
            'template': TemplateSerializer(
                TemplateSerializer.setup_eager_loading(Template.objects.filter(pk=template.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def partial_update(self, request, pk):
        template = Template.objects.select_related('format', 'format__assignment').get(pk=pk)

        request.user.check_permission('can_edit_assignment', template.format.assignment)

        Template.validate(request.data, assignment=template.format.assignment, old=template)
        with transaction.atomic():
            template = template_utils.handle_template_update(request.data, template.format)

        return response.success({
            'template': TemplateSerializer(
                TemplateSerializer.setup_eager_loading(Template.objects.filter(pk=template.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def destroy(self, request, pk):
        template = Template.objects.select_related('format', 'format__assignment').get(pk=pk)

        request.user.check_permission('can_edit_assignment', template.format.assignment)

        if template.can_be_deleted():
            template.delete()
        else:
            template.archived = True
            template.save()

        return response.success(description=f'Successfully deleted {template.name}.')
