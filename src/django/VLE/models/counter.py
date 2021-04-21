from django.db import models

from .base import CreateUpdateModel


class Counter(CreateUpdateModel):
    """Counter.

    A single counter class which can be used to keep track of incremental values
    which do not belong to another object like the message ID for LTI messages.
    """

    name = models.TextField(
        null=False
    )
    count = models.IntegerField(
        default=0
    )

    def to_string(self, user=None):
        return self.name + " is on " + self.count
