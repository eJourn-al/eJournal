from django.conf import settings
from django.db import models

from .base import CreateUpdateModel


class Instance(CreateUpdateModel):
    """Global settings for the running instance."""
    allow_standalone_registration = models.BooleanField(
        default=True
    )
    name = models.TextField(
        default='eJournal'
    )
    default_lms_profile_picture = models.TextField(
        default=settings.DEFAULT_LMS_PROFILE_PICTURE
    )

    def to_string(self, user=None):
        return self.name
