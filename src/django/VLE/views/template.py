from django.db import transaction
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.utils.template as template_utils
from VLE.models import Assignment, Template
from VLE.serializers import TemplateSerializer
from VLE.utils import file_handling


class TemplateView(viewsets.ViewSet):
    def list(self, request):
        assignment_id, = utils.required_typed_params(request.query_params, (int, 'assignment_id'))

        assignment = Assignment.objects.select_related('format').get(pk=assignment_id)

        if not request.user.can_view(assignment):
            return response.forbidden('You are not allowed to view this assignment.')

        serializer = TemplateSerializer(
            TemplateSerializer.setup_eager_loading(
                assignment.format.template_set.filter(archived=False)
            ),
            context={'user': request.user},
            many=True,
        )

        return response.success({'templates': serializer.data})

    def create(self, request):
        assignment_id, = utils.required_typed_params(request.data, (int, 'assignment_id'))
        template_import, = utils.optional_typed_params(request.data, (bool, 'template_import'))

        assignment = Assignment.objects.select_related('format').get(pk=assignment_id)
        request.user.check_permission('can_edit_assignment', assignment)

        Template.validate(request.data, assignment=assignment)

        with transaction.atomic():
            template = Template.objects.create_template_and_fields_from_data(
                request.data,
                assignment.format,
                template_import=template_import,
                author=request.user,
            )

            if not template_import:
                for field in template.field_set.all():
                    file_handling.establish_rich_text(
                        author=request.user,
                        rich_text=field.description,
                        assignment=assignment,
                    )

        return response.created({
            'template': TemplateSerializer(
                TemplateSerializer.setup_eager_loading(Template.objects.filter(pk=template.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def partial_update(self, request, pk):
        template = Template.objects.select_related('format', 'format__assignment', 'chain').get(pk=pk)
        assignment = template.format.assignment

        request.user.check_permission('can_edit_assignment', assignment)

        Template.validate(request.data, assignment=assignment, old=template)

        with transaction.atomic():
            template = template_utils.handle_template_update(request.data, template)

            for field in template.field_set.all():
                file_handling.establish_rich_text(
                    author=request.user,
                    rich_text=field.description,
                    assignment=assignment,
                )

        return response.success({
            'template': TemplateSerializer(
                TemplateSerializer.setup_eager_loading(Template.objects.filter(pk=template.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def destroy(self, request, pk):
        template = Template.objects.select_related('format', 'format__assignment').get(pk=pk)

        request.user.check_permission('can_edit_assignment', template.format.assignment)

        deadlines_with_forced_template = template.presetnode_set.all()
        if deadlines_with_forced_template.exists():
            return response.bad_request(
                'Deadlines {} make use of template {}. Please change the deadlines first.'.format(
                    utils.format_query_set_values_to_display(deadlines_with_forced_template, 'display_name'),
                    template.name,
                )
            )

        if template.can_be_deleted():
            template.delete()
        else:
            template.archived = True
            template.save()

        return response.success(description=f'Successfully deleted {template.name}.')
