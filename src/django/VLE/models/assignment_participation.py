from django.conf import settings
from django.db import models, transaction

from VLE.tasks.notifications import generate_new_assignment_notifications

from .base import CreateUpdateModel
from .journal import Journal
from .notification import Notification


class AssignmentParticipationQuerySet(models.QuerySet):
    def bulk_create(self, aps, *args, create_missing_journals=True, new_assignment_notification=True, **kwargs):
        with transaction.atomic():
            # Create missing journals
            if create_missing_journals:
                journals = []
                aps_missing_journal = []
                for ap in aps:
                    if not ap.journal:
                        journals.append(Journal(assignment=ap.assignment))
                        aps_missing_journal.append(ap)

                journals = Journal.objects.bulk_create(journals)
                for ap, journal in zip(aps_missing_journal, journals):
                    ap.journal = journal

            aps = super().bulk_create(aps, *args, **kwargs)

            # Generate new assignment notifications
            if new_assignment_notification:
                generate_new_assignment_notifications.apply_async(
                    args=[[ap.pk for ap in aps if ap.user != ap.assignment.author]],
                    countdown=settings.WEBSERVER_TIMEOUT,
                )
            return aps


class AssignmentParticipation(CreateUpdateModel):
    """AssignmentParticipation

    A user that is connected to an assignment
    this can then be used as a participation for a journal
    """
    objects = models.Manager.from_queryset(AssignmentParticipationQuerySet)()

    journal = models.ForeignKey(
        'Journal',
        on_delete=models.SET_NULL,
        related_name='authors',
        null=True,
    )

    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
    )

    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE
    )

    sourcedid = models.TextField(null=True)
    grade_url = models.TextField(null=True)

    def needs_lti_link(self):
        return self.assignment.active_lti_id is not None and self.sourcedid is None

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super(AssignmentParticipation, self).save(*args, **kwargs)

        # Instance is being created (not modified)
        if is_new:
            if self.assignment.is_published and not self.assignment.is_group_assignment and not self.journal:
                journal = Journal.objects.create(assignment=self.assignment)
                journal.add_author(self)

            if self.assignment.is_published and self.user != self.assignment.author:
                self.create_new_assignment_notification()

    def create_new_assignment_notification(self):
        Notification.objects.create(
            type=Notification.NEW_ASSIGNMENT,
            user=self.user,
            assignment=self.assignment,
        )

    def to_string(self, user=None):
        if user is None or not (user == self.user or user.is_supervisor_of(self.user)):
            return "Participant"

        return "{} in {}".format(self.user.username, self.assignment.name)

    class Meta:
        """A class for meta data.

        - unique_together: assignment and author must be unique together.
        """
        unique_together = ('assignment', 'user',)
