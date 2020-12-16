from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Category, Entry
from VLE.serializers import CategoryConcreteFieldsSerializer, CategorySerializer
from VLE.utils import file_handling


def _validate_templates(templates, assignment):
    """Ensures the templates are all part of the assignment."""
    templates = set(templates)
    assignment_template_ids = set(assignment.format.template_set.values_list('pk', flat=True))
    if not all(id in assignment_template_ids for id in templates):
        raise ValidationError('One or more templates are not part of the category\'s assignment.')

    return templates


def _validate_category_data(name, color, assignment):
    if Category.objects.filter(name=name, assignment=assignment).exists():
        raise ValidationError('Please provide a unqiue category name.')

    if Category.objects.filter(color=color, assignment=assignment).exists():
        raise ValidationError('Please provide a unqiue category color.')


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
        assignment_id, name, description, color, templates = utils.required_typed_params(
            request.data,
            (int, 'assignment_id'),
            (str, 'name'),
            (str, 'description'),
            (str, 'color'),
            (int, 'templates'),
        )

        assignment = Assignment.objects.filter(pk=assignment_id).select_related('format').get()
        request.user.check_permission('can_edit_assignment', assignment)

        _validate_category_data(name, color, assignment)
        templates = _validate_templates(templates, assignment)

        category = Category.objects.create(
            name=name,
            description=description,
            assignment=assignment,
            author=request.user,
            color=color,
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
        name, description, color, templates = utils.required_typed_params(
            request.data,
            (str, 'name'),
            (str, 'description'),
            (str, 'color'),
            (int, 'templates'),
        )

        category = Category.objects.filter(pk=pk).select_related('assignment').get()
        request.user.check_permission('can_edit_assignment', category.assignment)

        _validate_category_data(name, color, category.assignment)
        templates = _validate_templates(templates, category.assignment)

        with transaction.atomic():
            category.name = name
            category.description = description
            category.color = color
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

    @action(methods=['patch'], detail=True)
    def edit_entry(self, request, pk):
        entry_id, add = utils.required_typed_params(request.data, (int, 'entry_id'), (bool, 'add'))

        category = Category.objects.get(pk=pk)
        entry = Entry.objects.select_related('node__journal__assignment', 'template').get(pk=entry_id)
        template = entry.template
        assignment = entry.node.journal.assignment

        if request.user.has_permission('can_grade', assignment):
            pass
        elif request.user.has_permission('can_have_journal', assignment):
            if template.fixed_categories:
                return response.forbidden('This entry\'s template\'s categories are fixed.')
            if not request.user.can_edit(entry):
                return response.forbidden('You can no longer edit the entry\'s categories.')
        else:
            return response.forbidden('You are not allowed to edit the entry\'s categories.')

        if add:
            if not Category.objects.filter(assignment=assignment, pk=category.pk).exists():
                raise ValidationError('Categories can only be linked to entries which are part of the same assignment.')

        if add:
            entry.add_category(category=category, author=request.user)
        else:
            entry.categories.remove(category)

        return response.success(CategoryConcreteFieldsSerializer(category).data)
