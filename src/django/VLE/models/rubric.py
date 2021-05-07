from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q

import VLE.utils.generic_utils as generic_utils

from .base import CreateUpdateModel


def validate_locations(data, instance_label):
    locations = set()

    for instance_data in data:
        location, = generic_utils.required_typed_params(instance_data, (int, 'location'))

        if location in locations:
            raise ValidationError(f'Duplicate {instance_label} location provided.')
        if location < 0 or location >= len(data):
            raise ValidationError(f'{instance_label} location is out of bounds.')

        locations.add(location)


def validate_unique_names(data, instance_label):
    names = set()

    for instance_data in data:
        name, = generic_utils.required_typed_params(instance_data, (str, 'name'))

        if name in names:
            raise ValidationError(f'{instance_label} name: {name} is not unique.')

        names.add(name)


def validate_fks(data, attr, expected_fk, instance_label):
    for instance_data in data:
        actual_fk = instance_data[attr]
        if actual_fk > 0 and actual_fk != expected_fk:
            raise ValidationError(
                f'{instance_label} is unexpectedly linked to a different {attr}. `{actual_fk}` iso `{expected_fk}`.')


class Rubric(CreateUpdateModel):
    class Meta:
        constraints = [
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
        ]
        unique_together = (
            ('name', 'assignment'),
        )

    HIDDEN = 'h'
    VISIBLE = 'v'
    HIDDEN_UNTILL_FEEDBACK = 'huv'

    VISIBILITY_OPTIONS = (
        (HIDDEN, 'Hidden from students'),
        (VISIBLE, 'Visible to students'),
        (HIDDEN_UNTILL_FEEDBACK, 'Hidden from students untill overall feedback is provided'),
    )

    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE,
        related_name='rubrics',
    )

    name = models.TextField()

    description = models.TextField(
        blank=True,
    )

    visibility = models.CharField(
        max_length=3,
        choices=VISIBILITY_OPTIONS,
        default=VISIBLE,
    )

    hide_score_from_students = models.BooleanField(
        default=False,
    )

    # We only allow for points atm anyway
    # scoring_type = [
    # no score
    # points
    # pass fail etc
    # ]

    @staticmethod
    def validate(data, assignment, old=None):
        def validate_concrete_fields():
            name, visibility = generic_utils.required_typed_params(data, (str, 'name'), (str, 'visibility'))

            if (
                data.get('assignment') != assignment.pk
                or old and old.assignment is not assignment
            ):
                raise ValidationError('Cannot change the assignment of a rubric.')

            if (
                not old and assignment.rubrics.filter(name=name).exists()
                or old and assignment.rubrics.filter(name=name).exclude(pk=old.pk).exists()
            ):
                raise ValidationError('Please provide a unique rubric name.')

            if visibility not in [option[0] for option in Rubric.VISIBILITY_OPTIONS]:
                raise ValidationError(f'Unknown rubric visibility option `{visibility}`.')

        def validate_criteria_and_levels():
            criteria_data, = generic_utils.required_params(data, 'criteria')

            validate_locations(criteria_data, 'Criterion')
            validate_unique_names(criteria_data, 'Criterion')
            if old:
                validate_fks(criteria_data, 'assignment', assignment.pk, 'Criterion')

            if len(criteria_data) == 0:
                raise ValidationError('A valid rubric consists of one or more criteria.')

            existing_level_data_criterion_pks = {}
            for criterion_data in criteria_data:
                levels_data, = generic_utils.required_params(criterion_data, 'levels')

                validate_locations(levels_data, 'Level')
                validate_unique_names(levels_data, 'Level')
                if old:
                    existing_level_data_criterion_pks.union({
                        level_data.get('criterion')
                        for level_data in levels_data
                        if level_data.get('criterion') > 0
                    })

                if len(levels_data) < 2:
                    raise ValidationError('A valid criterion consist of two or more levels.')

            if old and not existing_level_data_criterion_pks.issubset(set(old.criteria.values_list('pk', flat=True))):
                raise ValidationError('One or more levels are linked to criteria not part of the rubric.')

        validate_concrete_fields()
        validate_criteria_and_levels()


# TODO Rubric: Validation, should consist of atleast two levels
# QUESTION: Should we enforce max to min (left to right) on the levels of one criterion? So each sequential
# level would be lte to previous?
class Criterion(CreateUpdateModel):
    class Meta:
        constraints = [
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
        ]
        ordering = ['location']
        unique_together = (
            ('name', 'rubric'),
            ('location', 'rubric'),
        )

    rubric = models.ForeignKey(
        'Rubric',
        on_delete=models.CASCADE,
        related_name='criteria',
    )

    name = models.TextField()

    description = models.TextField(
        blank=True,
    )

    # Rows, ordered top to bottom
    location = models.PositiveIntegerField()


class Level(CreateUpdateModel):
    class Meta:
        constraints = [
            CheckConstraint(check=Q(points__gte=0.0), name='points_gte_0'),
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
        ]
        ordering = ['location']
        unique_together = (
            ('name', 'criterion'),
            ('location', 'criterion'),
        )

    criterion = models.ForeignKey(
        'Criterion',
        on_delete=models.CASCADE,
        related_name='levels',
    )

    name = models.TextField()

    description = models.TextField(
        blank=True,
    )

    points = models.FloatField()

    initial_feedback = models.TextField(
        blank=True,
    )

    # Cells of a row, ordered left to right
    location = models.PositiveIntegerField()
