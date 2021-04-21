from django.db import models

from .base import CreateUpdateModel
from .notification import Notification


class Grade(CreateUpdateModel):
    """Grade.

    Used to keep a history of grades.
    """
    entry = models.ForeignKey(
        'Entry',
        related_name='grade_set',
        on_delete=models.CASCADE,
    )
    grade = models.FloatField(
        editable=False,
    )
    published = models.BooleanField(
        default=False,
        editable=False
    )
    author = models.ForeignKey(
        'User',
        null=True,
        editable=False,
        on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super(Grade, self).save(*args, **kwargs)
        if self.published:
            for author in self.entry.node.journal.authors.all():
                Notification.objects.create(
                    type=Notification.NEW_GRADE,
                    user=author.user,
                    grade=self
                )
        # Save entry to set this grade as the new entry grade
        if is_new:
            self.entry.save()

    def to_string(self, user=None):
        return "Grade"
