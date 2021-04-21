from django.conf import settings
from django.db import models

from VLE.tasks.notifications import generate_new_comment_notifications
from VLE.utils import sanitization

from .base import CreateUpdateModel


class Comment(CreateUpdateModel):
    """Comment.

    Comments contain the comments given to the entries.
    It is linked to a single entry with a single author and the comment text.
    """

    entry = models.ForeignKey(
        'Entry',
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True
    )
    text = models.TextField()
    published = models.BooleanField(
        default=True
    )
    files = models.ManyToManyField(
        'FileContext',
        related_name='comment_files',
    )
    last_edited = models.DateTimeField(auto_now_add=True)
    last_edited_by = models.ForeignKey(
        'User',
        related_name='last_edited_by',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    def can_edit(self, user):
        """
        Returns whether the given user is allowed to edit the comment:
            - Has to be the author or super_user
            - Otheriwse has to have the permission 'can_edit_staff_comment' and edit a non journal author comment.
              Because staff members can't have a journal themselves, checking if the author is not the owner of the
              journal the comment is posted to suffices.
        Raises a VLEProgramming error when misused.
        """
        if user == self.author or user.is_superuser:
            return True

        return user.has_permission('can_edit_staff_comment', self.entry.node.journal.assignment) and \
            not self.entry.node.journal.authors.filter(user=self.author).exists()

    def save(self, *args, **kwargs):
        is_new = not self.pk
        self.text = sanitization.strip_script_tags(self.text)
        super(Comment, self).save(*args, **kwargs)

        if is_new and self.published:
            generate_new_comment_notifications.apply_async(args=[self.pk], countdown=settings.WEBSERVER_TIMEOUT)

    def to_string(self, user=None):
        return "Comment"
