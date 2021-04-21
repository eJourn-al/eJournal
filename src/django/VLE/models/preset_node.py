from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import CheckConstraint, Q
from django.utils.timezone import now

import VLE.utils.generic_utils as generic_utils

from .base import CreateUpdateModel
from .file_context import FileContext
from .node import Node


class PresetNodeQuerySet(models.QuerySet):
    def create(self, *args, **kwargs):
        """
        Create a preset node, and creates corresponding nodes for the journals of the assignment in the same
        transaction.
        """
        with transaction.atomic():
            preset = super().create(*args, **kwargs)

            Node.objects.bulk_create([Node(
                type=preset.type,
                entry=None,
                preset=preset,
                journal=journal
            ) for journal in preset.format.assignment.journal_set.all()])

            return preset


class PresetNode(CreateUpdateModel):
    """PresetNode.

    A preset node is a node that has been pre-defined by the teacher.
    It contains the following features:
    - description: user defined text description of the preset node.
    - type: the type of the preset node (progress or entrydeadline node).
    - unlock_date: the date from which the preset node can be filled in.
    - due_date: the due date for this preset node.
    - lock_date: the date after which the preset node can no longer be fulfilled.
    - forced_template: the template for this preset node - null if PROGRESS node.
    - format: a foreign key linked to a format.
    """

    class Meta:
        constraints = [
            CheckConstraint(check=~Q(display_name=''), name='non_empty_display_name'),
        ]

    objects = models.Manager.from_queryset(PresetNodeQuerySet)()

    TYPES = (
        (Node.PROGRESS, 'progress'),
        (Node.ENTRYDEADLINE, 'entrydeadline'),
    )

    display_name = models.TextField()

    description = models.TextField(
        blank=True,
    )

    type = models.TextField(
        max_length=4,
        choices=TYPES,
    )

    target = models.FloatField(
        null=True,
    )

    unlock_date = models.DateTimeField(
        null=True
    )

    due_date = models.DateTimeField()

    lock_date = models.DateTimeField(
        null=True
    )

    forced_template = models.ForeignKey(
        'Template',
        on_delete=models.PROTECT,
        null=True,
    )
    attached_files = models.ManyToManyField(
        'FileContext',
    )

    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )

    @staticmethod
    def validate_unlock_date(data, assignment):
        """Own field due_date is checked in full in `validate_due_date`"""
        unlock_date, lock_date = generic_utils.optional_typed_params(
            data,
            (datetime, 'unlock_date'),
            (datetime, 'lock_date'),
        )

        if unlock_date:
            if assignment.unlock_date and unlock_date < assignment.unlock_date:
                raise ValidationError('Deadline unlocks before assignment unlocks.')

            if assignment.due_date and unlock_date > assignment.due_date:
                raise ValidationError('Deadline unlocks after assignment is due.')

            if assignment.lock_date and unlock_date > assignment.lock_date:
                raise ValidationError('Deadline unlocks after assignment locks.')

            if lock_date:
                if unlock_date > lock_date:
                    raise ValidationError('Deadline unlocks after it locks.')

    @staticmethod
    def validate_due_date(data, assignment):
        type, = generic_utils.required_typed_params(data, (str, 'type'))
        due_date, = generic_utils.optional_typed_params(data, (datetime, 'due_date'))

        if not due_date:
            raise ValidationError('Due date is required, cannot be empty.')

        if assignment.unlock_date and due_date < assignment.unlock_date:
            raise ValidationError('Deadline is due before assignment unlocks.')

        if assignment.due_date and due_date > assignment.due_date:
            raise ValidationError('Deadline is due after the assignment is due.')

        if assignment.lock_date and due_date > assignment.lock_date:
            raise ValidationError('Deadline is due after the assignment locks.')

        if type == Node.ENTRYDEADLINE:
            unlock_date, lock_date = generic_utils.optional_typed_params(
                data,
                (datetime, 'unlock_date'),
                (datetime, 'lock_date'),
            )

            if unlock_date:
                if due_date < unlock_date:
                    raise ValidationError('Deadline is due before it unlocks.')

            if lock_date:
                if due_date > lock_date:
                    raise ValidationError('Deadline is due after it locks.')

    @staticmethod
    def validate_lock_date(data, assignment):
        """Own field due_date is checked in full in `validate_due_date`"""
        unlock_date, lock_date = generic_utils.optional_typed_params(
            data,
            (datetime, 'unlock_date'),
            (datetime, 'lock_date'),
        )

        if lock_date:
            if assignment.unlock_date and lock_date < assignment.unlock_date:
                raise ValidationError('Deadline locks before the assignment unlocks.')

            if assignment.lock_date and lock_date > assignment.lock_date:
                raise ValidationError('Deadline locks after the assignment locks.')

            if unlock_date:
                if lock_date < unlock_date:
                    raise ValidationError('Deadline locks before it unlocks.')

    @staticmethod
    def validate(data, assignment, user, old=None):
        display_name, type, description = generic_utils.required_typed_params(
            data,
            (str, 'display_name'),
            (str, 'type'),
            (str, 'description'),
        )
        attached_files, = generic_utils.required_params(data, 'attached_files')
        attached_file_ids = [file['id'] for file in attached_files]

        def validate_display_name():
            if display_name == '':
                raise ValidationError('Display name cannot be empty.')

        def validate_attached_files():
            if FileContext.objects.filter(pk__in=attached_file_ids).count() != len(attached_files):
                raise ValidationError('One or more attached files are not correctly uploaded, please try again.')

            if FileContext.objects.filter(
                pk__in=attached_file_ids
            ).exclude(
                is_temp=True,
            ).exclude(
                assignment=assignment,
            ).exists():
                raise ValidationError('One or more attached files are not part of the assignment.')

            if FileContext.objects.filter(
                pk__in=attached_file_ids,
                is_temp=True,
            ).exclude(author=user).exists():
                raise ValidationError('One or more files recently uploaded are not owned by you.')

        def validate_progress_specific_fields():
            target, due_date = generic_utils.required_typed_params(data, (int, 'target'), (datetime, 'due_date'))

            if target < 0:
                raise ValidationError('Number of points cannot be less than 0.')
            elif target > assignment.points_possible:
                raise ValidationError(
                    'Number of points exceed the maximum amount for the assignment ({}/{}).'.format(
                        target, assignment.points_possible
                    )
                )

            earlier_deadlines_with_higher_target = assignment.format.presetnode_set.filter(
                type=Node.PROGRESS,
                target__gt=target,
                due_date__lt=due_date,
            )
            if old:
                earlier_deadlines_with_higher_target = earlier_deadlines_with_higher_target.exclude(pk=old.pk)
            if earlier_deadlines_with_higher_target.exists():
                deadline_display = generic_utils.format_query_set_values_to_display(
                    earlier_deadlines_with_higher_target, 'display_name')
                raise ValidationError(
                    f'Deadlines {deadline_display} are due earlier, with a higher number of required points.')

            later_deadlines_with_lower_target = assignment.format.presetnode_set.filter(
                type=Node.PROGRESS,
                target__lt=target,
                due_date__gt=due_date,
            )
            if old:
                later_deadlines_with_lower_target = later_deadlines_with_lower_target.exclude(pk=old.pk)
            if later_deadlines_with_lower_target.exists():
                deadline_display = generic_utils.format_query_set_values_to_display(
                    later_deadlines_with_lower_target, 'display_name')
                raise ValidationError(
                    f'Deadlines {deadline_display} are due later, with a lower number of required points.')

        def validate_deadline_specific_fields():
            template, = generic_utils.required_params(data, 'template')

            if not assignment.format.template_set.filter(pk=template['id']).exists():
                raise ValidationError('The provided template is not part of the assignment.')

            PresetNode.validate_unlock_date(data, assignment)
            PresetNode.validate_lock_date(data, assignment)

        validate_display_name()
        validate_attached_files()
        PresetNode.validate_due_date(data, assignment)

        if type == Node.PROGRESS:
            validate_progress_specific_fields()
        elif type == Node.ENTRYDEADLINE:
            validate_deadline_specific_fields()
        else:
            raise ValidationError('Unknown preset node type.')

    @property
    def is_deadline(self):
        return self.type == Node.ENTRYDEADLINE

    @property
    def is_progress(self):
        return self.type == Node.PROGRESS

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            Node.objects.filter(preset=self, entry__isnull=True).delete()
            self.attached_files.all().delete()
            super().delete(*args, **kwargs)

    def is_locked(self):
        return self.unlock_date is not None and self.unlock_date > now() or self.lock_date and self.lock_date < now()

    def to_string(self, user=None):
        return "PresetNode"
