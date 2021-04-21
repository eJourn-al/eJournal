from django.contrib.postgres.fields import ArrayField
from django.db import models

from .base import CreateUpdateModel


class Course(CreateUpdateModel):
    """Course.

    A Course entity has the following features:
    - name: name of the course.
    - author: the creator of the course.
    - abbreviation: a max three letter abbreviation of the course name.
    - startdate: the date that the course starts.
    - active_lti_id: (optional) the active VLE id of the course linked through LTI which receives grade updates.
    - lti_id_set: (optional) the set of VLE lti_id_set which permit basic access.
    """

    name = models.TextField()
    abbreviation = models.TextField(
        max_length=10,
        default='XXXX',
    )

    author = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True
    )

    users = models.ManyToManyField(
        'User',
        related_name='participations',
        through='Participation',
        through_fields=('course', 'user'),
    )

    startdate = models.DateField(
        null=True,
    )
    enddate = models.DateField(
        null=True,
    )

    active_lti_id = models.TextField(
        null=True,
        unique=True,
        blank=True,
    )

    # These LTI assignments belong to this course.
    assignment_lti_id_set = ArrayField(
        models.TextField(),
        default=list,
    )

    def add_assignment_lti_id(self, lti_id):
        if lti_id not in self.assignment_lti_id_set:
            self.assignment_lti_id_set.append(lti_id)

    def has_lti_link(self):
        return self.active_lti_id is not None

    def to_string(self, user=None):
        if user is None:
            return "Course"
        if not user.can_view(self):
            return "Course"

        return self.name + " (" + str(self.pk) + ")"
