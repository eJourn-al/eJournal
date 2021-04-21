import os
import random
import string

from django.conf import settings
from django.db import models
from django.db.models import F, Q, TextField
from django.db.models.functions import Cast
from django.dispatch import receiver

import VLE.utils.file_handling as file_handling
from VLE.utils.error_handling import VLEProgrammingError

from .base import CreateUpdateModel
from .field import Field


class FileContextQuerySet(models.QuerySet):
    def unused_file_field_files(self, func='filter'):
        """Queries for files linked to a FILE field where the data no longer holds the FC's `pk`"""
        return getattr(self, func)(
            ~Q(content__data=Cast(F('pk'), TextField())),
            content__field__type=Field.FILE,
        )

    def unused_rich_text_field_files(self, func='filter'):
        """Queries for files linked to a FILE field where the data no longer holds the FC's `access_id`"""
        return getattr(self, func)(
            ~Q(content__data__contains=F('access_id')),
            content__field__type=Field.RICH_TEXT,
        )

    def unused_category_description_files(self, func='filter'):
        return getattr(self, func)(
            ~Q(category__description__contains=F('access_id')),
            category__isnull=False,
        )


# https://stackoverflow.com/a/2257449
def access_gen(size=128, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


class FileContext(CreateUpdateModel):
    """FileContext.

    FileContext is a file uploaded by the user stored in MEDIA_ROOT/uID/<category>/?[id/]<filename>
        Where category is selected from {course, assignment, journal}

    - file: the actual filefield contain a reference to the physical file.
    - file_name: The name of the file (not unique and no parts of the path to the file included).
    - author: The user who uploaded the file. Can be null so the File persist on user deletion.
    - assignment: The assignment that the File is linked to (e.g. assignment description).
    - content: The content that the File is linked to. Can be rich text or a dedicated file field.
    - course: The course that the File is linked to (e.g. course description).
    - journal: The journal that the File is linked to (e.g. comment).
    """
    objects = models.Manager.from_queryset(FileContextQuerySet)()

    file = models.FileField(
        null=False,
        upload_to=file_handling.get_file_path,
        max_length=255,
    )
    in_rich_text = models.BooleanField(
        default=False
    )
    access_id = models.CharField(
        null=False,
        default=access_gen,
        max_length=128,
        unique=True,
    )
    file_name = models.TextField(
        null=False
    )
    author = models.ForeignKey(
        'User',
        null=True,
        on_delete=models.SET_NULL
    )
    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE,
        null=True
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
        null=True
    )
    content = models.ForeignKey(
        'Content',
        on_delete=models.CASCADE,
        null=True
    )
    comment = models.ForeignKey(
        'Comment',
        on_delete=models.CASCADE,
        null=True
    )
    journal = models.ForeignKey(
        'Journal',
        on_delete=models.CASCADE,
        null=True
    )
    is_temp = models.BooleanField(
        default=True
    )

    def download_url(self, access_id=False):
        if access_id:
            return '{}/files/{}?access_id={}'.format(settings.API_URL, self.pk, self.access_id)
        return '/files/{}/'.format(self.pk)

    def cascade_from_user(self, user):
        return self.author is user and self.assignment is None and self.journal is None and self.content is None \
            and self.comment is None

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self.author:
                raise VLEProgrammingError('FileContext author should be set on creation.')

        return super(FileContext, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.file.delete()
        super(FileContext, self).delete(*args, **kwargs)

    def to_string(self, user=None):
        return "FileContext"


@receiver(models.signals.post_delete, sender=FileContext)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Deletes file from filesystem when corresponding `FileContext` object is deleted."""
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
