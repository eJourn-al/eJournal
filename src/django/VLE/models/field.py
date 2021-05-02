from django.db import models

from .base import CreateUpdateModel


class Field(CreateUpdateModel):
    """Field.

    Defines the fields of an Template
    """
    class Meta:
        ordering = ['location']
        unique_together = (
            ('location', 'template'),
        )

    ALLOWED_URL_SCHEMES = ('http', 'https', 'ftp', 'ftps')

    TEXT = 't'
    RICH_TEXT = 'rt'
    FILE = 'f'
    VIDEO = 'v'
    URL = 'u'
    DATE = 'd'
    DATETIME = 'dt'
    SELECTION = 's'
    NO_SUBMISSION = 'n'

    TYPES_WITHOUT_FILE_CONTEXT = {TEXT, VIDEO, URL, DATE, DATETIME, SELECTION, NO_SUBMISSION}

    KALTURA = 'k'
    YOUTUBE = 'y'
    VIDEO_OPTIONS = {KALTURA, YOUTUBE}

    TYPES = (
        (TEXT, 'text'),
        (RICH_TEXT, 'rich text'),
        (FILE, 'file'),
        (VIDEO, 'vid'),
        (URL, 'url'),
        (DATE, 'date'),
        (DATETIME, 'datetime'),
        (SELECTION, 'selection'),
        (NO_SUBMISSION, 'no submission')
    )
    type = models.TextField(
        max_length=4,
        choices=TYPES,
        default=TEXT,
    )
    title = models.TextField()
    description = models.TextField(
        blank=True
    )
    options = models.TextField(
        null=True
    )
    location = models.PositiveIntegerField()
    template = models.ForeignKey(
        'Template',
        on_delete=models.CASCADE
    )
    required = models.BooleanField()

    @property
    def kaltura_allowed(self):
        return self.type == Field.VIDEO and Field.KALTURA in self.options.split(',')

    @property
    def youtube_allowed(self):
        return self.type == Field.VIDEO and Field.YOUTUBE in self.options.split(',')

    def to_string(self, user=None):
        return "{} ({})".format(self.title, self.id)

    def save(self, *args, **kwargs):
        if self.type == Field.FILE and self.options:
            self.options = ', '.join(f.strip().lower() for f in self.options.split(','))
        return super(Field, self).save(*args, **kwargs)
