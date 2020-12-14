from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Category
from VLE.serializers import CategorySerializer
from VLE.utils import file_handling


def _validate_templates(templates, assignment):
    """Ensures the templates are all part of the assignment."""
    templates = set(templates)
    assignment_template_ids = set(assignment.format.template_set.values_list('pk', flat=True))
    if not all(id in assignment_template_ids for id in templates):
        raise ValidationError('One or more templates are not part of the category\'s assignment.')

    return templates


class CategoryView(viewsets.ViewSet):
    def list(self, request):
        assignment_id, = utils.required_typed_params(request.query_params, (int, 'assignment_id'))

        assignment = Assignment.objects.get(pk=assignment_id)
        if not request.user.can_view(assignment):
            return response.forbidden('You are not allowed to view this assignment.')

        serializer = CategorySerializer(
            CategorySerializer.setup_eager_loading(
                assignment.categories.all()
            ),
            context={'user': request.user},
            many=True,
        )

        return response.success({'categories': serializer.data})

    def create(self, request):
        assignment_id, name, description, templates = utils.required_typed_params(
            request.data,
            (int, 'assignment_id'),
            (str, 'name'),
            (str, 'description'),
            (int, 'templates'),
        )

        assignment = Assignment.objects.filter(pk=assignment_id).select_related('format').get()
        request.user.check_permission('can_edit_assignment', assignment)

        templates = _validate_templates(templates, assignment)

        category = Category.objects.create(
            name=name,
            description=description,
            assignment=assignment,
            author=request.user,
            templates=templates,
        )

        serializer = CategorySerializer(
            CategorySerializer.setup_eager_loading(
                Category.objects.filter(pk=category.pk)
            ).get(),
            context={'user': request.user},
        )

        return response.created({'category': serializer.data})

    def partial_update(self, request, pk, *args, **kwargs):
        name, description, templates = utils.required_typed_params(
            request.data,
            (str, 'name'),
            (str, 'description'),
            (int, 'templates'),
        )

        category = Category.objects.filter(pk=pk).select_related('assignment').get()
        request.user.check_permission('can_edit_assignment', category.assignment)

        templates = _validate_templates(templates, category.assignment)

        with transaction.atomic():
            category.name = name
            category.description = description
            category.templates.set(templates)
            category.save()
            file_handling.establish_rich_text(author=request.user, rich_text=description, category=category)

        serializer = CategorySerializer(
            CategorySerializer.setup_eager_loading(
                Category.objects.filter(pk=category.pk)
            ).get(),
            context={'user': request.user},
        )

        return response.success({'category': serializer.data})

    def destroy(self, request, pk):
        category = Category.objects.filter(pk=pk).select_related('assignment').get()

        request.user.check_permission('can_edit_assignment', category.assignment)

        category.delete()

        return response.success(description=f'Successfully deleted {category.name}.')
