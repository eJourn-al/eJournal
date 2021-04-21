from django.db import models

from .base import CreateUpdateModel


class Group(CreateUpdateModel):
    """Group.

    A Group entity has the following features:
    - name: the name of the group
    - course: the course where the group belongs to
    """
    name = models.TextField()

    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE
    )

    lti_id = models.TextField(
        null=True,
    )

    class Meta:
        """Meta data for the model: unique_together."""
        unique_together = ('lti_id', 'course')

    def to_string(self, user=None):
        if user is None:
            return "Group"
        if not user.can_view(self.course):
            return "Group"
        return "{} ({})".format(self.name, self.pk)
