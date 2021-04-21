from django.db import models

import VLE.models

from .assignment_participation import AssignmentParticipation
from .base import CreateUpdateModel
from .notification import Notification


class Participation(CreateUpdateModel):
    """Participation.

    A participation defines the way a user interacts within a certain course.
    The user is now linked to the course, and has a set of permissions
    associated with its role.
    """
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
    )
    role = models.ForeignKey(
        'Role',
        on_delete=models.CASCADE,
        related_name='role',
    )
    groups = models.ManyToManyField(
        'Group',
        default=None,
    )

    def set_groups(self, groups):
        self.groups.set(groups)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        notify_user = kwargs.pop('notify_user', True)
        super(Participation, self).save(*args, **kwargs)

        # Instance is being created (not modified)
        if is_new:
            existing = AssignmentParticipation.objects.filter(user=self.user).values('assignment')
            for assignment in VLE.models.Assignment.objects.filter(courses__in=[self.course]).exclude(pk__in=existing):
                AssignmentParticipation.objects.create(assignment=assignment, user=self.user)
            if notify_user and self.user != self.course.author:
                Notification.objects.create(
                    type=Notification.NEW_COURSE,
                    user=self.user,
                    course=self.course
                )

    class Meta:
        """Meta data for the model: unique_together."""

        unique_together = ('user', 'course',)

    def to_string(self, user=None):
        if user is None:
            return "Participation"
        if not user.can_view(self.course):
            return "Participation"

        return "user: {}, course: {}, role: {}".format(
            self.user.to_string(user=user), self.course.to_string(user=user), self.role.to_string(user=user))
