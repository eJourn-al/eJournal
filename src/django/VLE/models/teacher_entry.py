from django.core.exceptions import ValidationError
from django.db import models

from .entry import Entry


class TeacherEntry(Entry):
    """TeacherEntry.

    An entry posted by a teacher to multiple student journals.
    """
    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE,
    )
    show_title_in_timeline = models.BooleanField(
        default=True
    )

    # Teacher entries objects cannot directly contribute to journal grades. They should be added to each journal and
    # are individually graded / grades passed back to the LMS from there.
    # This allows editing and grade passback mechanics for students like usual.
    grade = None
    teacher_entry = None
    vle_coupling = None

    def save(self, *args, **kwargs):
        is_new = not self.pk
        self.grade = None
        self.teacher_entry = None
        self.vle_coupling = Entry.NO_LINK

        if not self.title:
            raise ValidationError('No valid title provided.')

        if is_new and not self.template:
            raise ValidationError('No valid template provided.')

        if is_new and not self.author:
            raise ValidationError('No author provided.')

        return super(TeacherEntry, self).save(*args, **kwargs)
