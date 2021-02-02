from datetime import datetime

from django.db import transaction
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, FileContext, Node, PresetNode
from VLE.serializers import PresetNodeSerializer
from VLE.utils import file_handling


def _update_attached_files(preset, author, new_ids):
    """Safely updates the attached files of the provided preset node based on the list of new fc ids"""
    new_ids = set(new_ids)
    current_ids = set(preset.attached_files.values_list('pk', flat=True))

    ids_to_add = new_ids - current_ids
    ids_to_remove = current_ids - new_ids

    preset.attached_files.filter(pk__in=ids_to_remove).delete()

    for fc in FileContext.objects.filter(pk__in=ids_to_add, is_temp=True, author=author):
        file_handling.establish_file(author=author, identifier=fc.access_id, assignment=preset.format.assignment)
    preset.attached_files.add(*ids_to_add)


class PresetNodeView(viewsets.ViewSet):
    def list(self, request):
        assignment_id, = utils.required_typed_params(request.query_params, (int, 'assignment_id'))

        assignment = Assignment.objects.select_related('format').get(pk=assignment_id)

        if not request.user.can_view(assignment):
            return response.forbidden('You are not allowed to view this assignment.')

        serializer = PresetNodeSerializer(
            PresetNodeSerializer.setup_eager_loading(
                assignment.format.presetnode_set.all()
            ),
            context={'user': request.user},
            many=True,
        )

        return response.success({'presets': serializer.data})

    def create(self, request):
        assignment_id, display_name, type, description, due_date = utils.required_typed_params(
            request.data,
            (int, 'assignment_id'),
            (str, 'display_name'),
            (str, 'type'),
            (str, 'description'),
            (datetime, 'due_date'),
        )
        attached_files, = utils.required_params(request.data, 'attached_files')
        attached_file_ids = [file['id'] for file in attached_files]

        target = None
        template = None
        unlock_date = None
        lock_date = None
        if type == Node.PROGRESS:
            target, = utils.required_typed_params(request.data, (int, 'target'))
        elif type == Node.ENTRYDEADLINE:
            template, = utils.required_params(request.data, 'template')
            template = template['id']
            unlock_date, lock_date = utils.optional_typed_params(
                request.data,
                (datetime, 'unlock_date'),
                (datetime, 'lock_date'),
            )

        assignment = Assignment.objects.select_related('format').get(pk=assignment_id)

        request.user.check_permission('can_edit_assignment', assignment)

        PresetNode.validate(request.data, assignment=assignment, user=request.user)

        with transaction.atomic():
            preset = PresetNode.objects.create(
                # Always set
                format=assignment.format,
                display_name=display_name,
                type=type,
                description=description,
                due_date=due_date,

                # Only set for a progress goal
                target=target,

                # Only set for an entry deadline
                forced_template_id=template,
                unlock_date=unlock_date,
                lock_date=lock_date,
            )
            _update_attached_files(preset, request.user, attached_file_ids)
            file_handling.establish_rich_text(author=request.user, rich_text=preset.description, assignment=assignment)

        return response.created({
            'preset': PresetNodeSerializer(
                PresetNodeSerializer.setup_eager_loading(PresetNode.objects.filter(pk=preset.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def partial_update(self, request, pk):
        display_name, type, description, due_date = utils.required_typed_params(
            request.data,
            (str, 'display_name'),
            (str, 'type'),
            (str, 'description'),
            (datetime, 'due_date'),
        )
        attached_files, = utils.required_params(request.data, 'attached_files')
        attached_file_ids = [file['id'] for file in attached_files]
        preset = PresetNode.objects.select_related('format__assignment').get(pk=pk)
        assignment = preset.format.assignment

        request.user.check_permission('can_edit_assignment', assignment)

        PresetNode.validate(request.data, assignment=assignment, user=request.user, old=preset)

        preset.display_name = display_name
        preset.description = description
        preset.due_date = due_date

        if type == Node.PROGRESS:
            target, = utils.required_typed_params(request.data, (int, 'target'))

            preset.target = target
        elif type == Node.ENTRYDEADLINE:
            template, = utils.required_params(request.data, 'template')
            unlock_date, lock_date = utils.optional_typed_params(
                request.data,
                (str, 'unlock_date'),
                (str, 'lock_date'),
            )

            preset.forced_template_id = template['id']
            preset.unlock_date = unlock_date
            preset.lock_date = lock_date

        with transaction.atomic():
            preset.save()
            _update_attached_files(preset, request.user, attached_file_ids)
            file_handling.establish_rich_text(author=request.user, rich_text=preset.description, assignment=assignment)

        return response.success({
            'preset': PresetNodeSerializer(
                PresetNodeSerializer.setup_eager_loading(PresetNode.objects.filter(pk=preset.pk)).get(),
                context={'user': request.user},
            ).data
        })

    def destroy(self, request, pk):
        preset = PresetNode.objects.select_related('format', 'format__assignment').get(pk=pk)

        request.user.check_permission('can_edit_assignment', preset.format.assignment)

        preset.delete()

        return response.success(description=f'Successfully deleted {preset.display_name}.')
