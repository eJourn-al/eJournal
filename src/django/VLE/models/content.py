from django.db import models

from VLE.utils import sanitization

from .base import CreateUpdateModel


class Content(CreateUpdateModel):
    """Content.

    Defines the content of an Entry
    """

    class Meta:
        unique_together = ('entry', 'field')

    entry = models.ForeignKey(
        'Entry',
        on_delete=models.CASCADE
    )
    field = models.ForeignKey(
        'Field',
        on_delete=models.CASCADE,
    )
    data = models.TextField(
        null=True
    )

    def save(self, *args, **kwargs):
        self.data = sanitization.strip_script_tags(self.data)

        return super(Content, self).save(*args, **kwargs)

    def to_string(self, user=None):
        return "Content"
