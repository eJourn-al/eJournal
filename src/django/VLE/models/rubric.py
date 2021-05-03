from django.db import models
from django.db.models import CheckConstraint, Q

from .base import CreateUpdateModel


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


class Criterion(CreateUpdateModel):
    class Meta:
        constraints = [
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
        ]
        ordering = ['location']
        unique_together = (
            ('name', 'rubric'),
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

    long_description = models.TextField(
        blank=True,
    )

    score_as_range = models.BooleanField(
        default=False,
    )

    # Rows, ordered top to bottom
    location = models.PositiveIntegerField()


class Level(CreateUpdateModel):
    class Meta:
        constraints = [
            CheckConstraint(check=Q(points__gte=0.0), name='points_gte_0'),
        ]
        ordering = ['location']

    criterion = models.ForeignKey(
        'Criterion',
        on_delete=models.CASCADE,
        related_name='levels',
    )

    points = models.FloatField()

    initial_feedback = models.TextField(
        blank=True,
    )

    # Cells of a row, ordered left to right
    location = models.PositiveIntegerField()
