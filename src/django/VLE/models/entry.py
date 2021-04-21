from django.conf import settings
from django.contrib.postgres.aggregates import StringAgg
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, CharField, F, Q, When

import VLE.models
from VLE.tasks.notifications import generate_new_entry_notifications

from .base import CreateUpdateModel
from .category import EntryCategoryLink
from .node import Node
from .user import User


class EntryQuerySet(models.QuerySet):
    def annotate_teacher_entry_grade_serializer_fields(self):
        return (
            self
            .annotate_full_names()
            .annotate_usernames()
            .annotate_name()
        )

    def annotate_full_names(self):
        """
        Annotates for each entry all journal users full name as a string joined by ', ' as `full_names`

        NOTE: Not compatible with exact matches of full names, but acceptable (same group and full name)
        """
        return self.annotate(full_names=StringAgg(
            'node__journal__authors__user__full_name',
            ', ',
            distinct=True,
        ))

    def annotate_usernames(self):
        return self.annotate(usernames=StringAgg('node__journal__authors__user__username', ', ', distinct=True))

    def annotate_name(self):
        """
        Annotates for each entry the journal name as `name`
        Uses the stored name if found, else defaults to a concat of all author names.

        NOTE: Makes use of `full_names` annotation as a default, as such that annotation needs to happen first.
        """
        return (
            self
            .annotate_full_names()
            .annotate(name=Case(
                When(Q(node__journal__stored_name__isnull=False), then=F('node__journal__stored_name')),
                default=F('full_names'),
                output_field=CharField(),
            ))
        )


class Entry(CreateUpdateModel):
    """Entry.

    An Entry has the following features:
    - last_edited: the date and time when the etry was last edited by an author. This also changes the last_edited_by
    """
    objects = models.Manager.from_queryset(EntryQuerySet)()

    NEEDS_SUBMISSION = 'Submission needs to be sent to VLE'
    SENT_SUBMISSION = 'Submission is successfully received by VLE'
    NEEDS_GRADE_PASSBACK = 'Grade needs to be sent to VLE'
    LINK_COMPLETE = 'Everything is sent to VLE'
    NO_LINK = 'Ignore VLE coupling (e.g. for teacher entries)'
    TYPES = (
        (NEEDS_SUBMISSION, 'entry_submission'),
        (SENT_SUBMISSION, 'entry_submitted'),
        (NEEDS_GRADE_PASSBACK, 'grade_submission'),
        (LINK_COMPLETE, 'done'),
        (NO_LINK, 'no_link'),
    )

    # TODO Should not be nullable
    template = models.ForeignKey(
        'Template',
        on_delete=models.SET_NULL,
        null=True,
    )
    grade = models.ForeignKey(
        'Grade',
        on_delete=models.SET_NULL,
        related_name='+',
        null=True,
    )
    teacher_entry = models.ForeignKey(
        'TeacherEntry',
        on_delete=models.CASCADE,
        null=True,
    )

    author = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        related_name='entries',
        null=True,
    )

    last_edited = models.DateTimeField(auto_now_add=True)
    last_edited_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        related_name='last_edited_entries',
        null=True,
    )

    vle_coupling = models.TextField(
        default=NEEDS_SUBMISSION,
        choices=TYPES,
    )

    jir = models.ForeignKey(
        'JournalImportRequest',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    categories = models.ManyToManyField(
        'Category',
        related_name='entries',
        through='EntryCategoryLink',
        through_fields=('entry', 'category'),
    )

    title = models.TextField(
        null=True,
        blank=True,
    )

    @staticmethod
    def validate_categories(category_ids, assignment, template=None):
        """
        Checks whether the provided categories belong to the assignment.

        If a template is provided and has locked categories, checks if the provided categories exactly match the
        template's assigned categories.
        """

        if not category_ids:
            return {}

        category_ids = set(category_ids)
        assignment_category_ids = set(assignment.categories.values_list('pk', flat=True))

        if not category_ids.issubset(assignment_category_ids):
            raise ValidationError('Entry can only be linked to categories which are part of the assignment.')

        if template and not template.chain.allow_custom_categories:
            template_category_ids = set(template.categories.values_list('pk', flat=True))
            if category_ids != template_category_ids:
                raise ValidationError('An entry of this type does not allow for custom categories.')

        return category_ids

    def is_locked(self):
        return (self.node.preset and self.node.preset.is_locked()) or self.node.journal.assignment.is_locked()

    def is_editable(self):
        return not self.is_graded() and not self.is_locked()

    def is_graded(self):
        return not (self.grade is None or self.grade.grade is None)

    def add_category(self, category, author):
        """Should be used over entry.categories.add() so the author is set and the link can be reused."""
        EntryCategoryLink.objects.get_or_create(
            entry=self,
            category=category,
            defaults={
                'entry': self,
                'category': category,
                'author': author,
            },
        )

    def set_categories(self, new_category_ids, author):
        """Should be used over entry.categories.set() so the author is set for all links"""
        existing_category_ids = set(self.categories.values_list('pk', flat=True))
        new_category_ids = set(new_category_ids)
        category_ids_to_delete = existing_category_ids - new_category_ids
        category_ids_to_create = new_category_ids - existing_category_ids

        EntryCategoryLink.objects.filter(entry=self, category__pk__in=category_ids_to_delete).delete()
        links = [EntryCategoryLink(entry=self, category_id=id, author=author) for id in category_ids_to_create]
        EntryCategoryLink.objects.bulk_create(links)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        author_id = self.__dict__.get('author_id', None)
        node_id = self.__dict__.get('node_id', None)
        author = self.author if self.author else User.objects.get(pk=author_id) if author_id else None
        self.grade = self.grade_set.order_by('creation_date').last()

        if author and not self.last_edited_by:
            self.last_edited_by = author

        if not isinstance(self, VLE.models.TeacherEntry):
            try:
                node = Node.objects.get(pk=node_id) if node_id else self.node
            except Node.DoesNotExist:
                raise ValidationError('Saving entry without corresponding node.')

            if (author and not node.journal.authors.filter(user=author).exists() and not self.teacher_entry and
                    not self.jir):
                raise ValidationError('Saving non-teacher entry created by user not part of journal.')

        super().save(*args, **kwargs)

        if is_new and not isinstance(self, VLE.models.TeacherEntry):
            generate_new_entry_notifications.apply_async(
                args=[self.pk, self.node.pk], countdown=settings.WEBSERVER_TIMEOUT)

    def to_string(self, user=None):
        return "Entry"
