from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import (Case, CharField, Count, F, FloatField, IntegerField, OuterRef, Q, Subquery, Sum, Value,
                              When)
from django.db.models.functions import Coalesce

import VLE.models
from VLE.utils.error_handling import VLEProgrammingError
from VLE.utils.query_funcs import Round2

from .base import CreateUpdateModel


class JournalQuerySet(models.QuerySet):
    def bulk_create(self, journals, *args, **kwargs):
        with transaction.atomic():
            journals = super().bulk_create(journals, *args, **kwargs)

            # Bulk create nodes
            nodes = []
            for journal in journals:
                nodes += journal.generate_missing_nodes(create=False)
            # Notifications should not be send when the journal is new. A "new assignment" notification is good enough
            VLE.models.Node.objects.bulk_create(nodes, new_node_notifications=False)

            return journals

    def order_by_authors_first(self):
        """Order by journals with authors first, no authors last."""
        return self.order_by(F('authors__journal').asc(nulls_last=True)).distinct()

    def for_course(self, course):
        """Filter the journals from the perspective of a single course."""
        return self.filter(
            Q(authors__user__in=course.participation_set.values('user'))
            | Q(authors__isnull=True)  # Also include empty (group) journals
        )

    def require_teacher_action(self):
        """Returns journals which have an entry, and are awaiting grading or of which the grade needs publishing"""
        return self.filter(
            Q(node__entry__grade__isnull=True) | Q(node__entry__grade__published=False),
            node__entry__isnull=False
        )

    def allowed_journals(self):
        """Filter on only journals with can_have_journal and that are in the assigned to groups"""
        return self.annotate(
            p_user=F('assignment__courses__participation__user'),
            p_group=F('assignment__courses__participation__groups'),
            can_have_journal=F('assignment__courses__participation__role__can_have_journal')
        ).filter(
            # Filter on only can_have_journal
            Q(assignment__is_group_assignment=True) | Q(p_user__in=F('authors__user'), can_have_journal=True),
        ).filter(
            # Filter on only assigned groups
            Q(assignment__is_group_assignment=True) | Q(p_group__in=F('assignment__assigned_groups')) |
            Q(assignment__assigned_groups=None),
        ).annotate(
            # Reset group, as that could lead to distinct not working
            p_group=F('pk'), p_user=F('pk'), can_have_journal=F('pk'),
        ).distinct().order_by('pk')

    def annotate_fields(self):
        """Calls all individual annotations which were used as computed fields."""
        return (
            self
            .annotate_full_names()
            .annotate_usernames()
            .annotate_name()
            .annotate_import_requests()
            .annotate_image()
            .annotate_unpublished()
            .annotate_grade()
            .annotate_needs_marking()
            .annotate_needs_lti_link()
            .annotate_groups()
        )

    def annotate_grade(self):
        """"Annotates for each journal the rounded published grade sum of all entries as `grade`"""
        grade_qry = Subquery(
            VLE.models.Entry.objects.filter(
                node__journal=OuterRef('pk'),
                grade__published=True,
            ).values(
                'node__journal',  # NOTE: Could be replaced by Sum(distinct=True) in Django 3.0+
            ).annotate(
                entry_grade_sum=Sum('grade__grade'),
            ).values(
                'entry_grade_sum',
            ),
            output_field=FloatField(),
        )

        return self.annotate(grade=(Round2(F('bonus_points') + Coalesce(grade_qry, 0))))

    def annotate_unpublished(self):
        """"Annotates for each journal the count of entries which have an unpublished grade as `unpublished`"""
        unpublished_entries_qry = Subquery(
            VLE.models.Entry.objects.filter(
                grade__published=False,
                node__journal=OuterRef('pk'),
            ).values(
                'node__journal',
            ).annotate(
                unpublished_count=Count('pk')
            ).values(
                'unpublished_count',
            ),
            output_field=IntegerField(),
        )

        return self.annotate(unpublished=Coalesce(unpublished_entries_qry, 0))

    def annotate_needs_marking(self):
        """"Annotates for each journal the count of entries which are ungraded as `needs_marking`"""
        needs_marking_entries_qry = Subquery(
            VLE.models.Entry.objects.filter(
                grade__isnull=True,
                node__journal=OuterRef('pk'),
            ).values(
                'node__journal',
            ).annotate(
                needs_marking_count=Count('pk')
            ).values(
                'needs_marking_count',
            ),
            output_field=IntegerField(),
        )

        return self.annotate(needs_marking=Coalesce(needs_marking_entries_qry, 0))

    def annotate_import_requests(self):
        """"Annotates for each journal the number of pending JIRs with it as target as `import_requests`"""
        return self.annotate(
            import_requests=Count(
                'import_request_targets',
                filter=Q(import_request_targets__state=VLE.models.JournalImportRequest.PENDING),
                distinct=True,
            ),
        )

    def annotate_needs_lti_link(self):
        """
        Annotates for each journal linked to an lti assignment (active lti id is not None)
        the full name as array of the users who do not have a sourcedid set as `needs_lti_link`
        """
        return self.annotate(needs_lti_link=ArrayAgg(
            'authors__user__full_name',
            filter=Q(authors__sourcedid__isnull=True, assignment__active_lti_id__isnull=False),
            distinct=True,
        ))

    def annotate_name(self):
        """
        Annotates the journal name of each journal as `name`
        Uses the stored name if found, else defaults to a concat of all author names.

        NOTE: Makes use of `annotate_full_names` as a default, as such that annotation needs to happen first.
        """
        return (
            self
            .annotate_full_names()
            .annotate(name=Case(
                When(Q(stored_name__isnull=False), then=F('stored_name')),
                default=F('full_names'),
                output_field=CharField(),
            ))
        )

    def annotate_image(self):
        """
        Annotates for each journal the stored image or the first non default image for each journal as `image`
        """
        first_non_default_profile_pic_user_qry = Subquery(VLE.models.User.objects.filter(
            ~Q(profile_picture=settings.DEFAULT_PROFILE_PICTURE),
            assignmentparticipation__journal=OuterRef('pk'),
        ).values('profile_picture')[:1])

        return self.annotate(image=Case(
            When(Q(stored_image__isnull=False), then=F('stored_image')),
            default=Coalesce(first_non_default_profile_pic_user_qry, Value(settings.DEFAULT_PROFILE_PICTURE)),
            output_field=CharField(),
        ))

    def annotate_full_names(self):
        """Annotates for each journal all journal users full name as a string joined by ', ' as `full_names`"""
        return self.annotate(full_names=StringAgg(
            'authors__user__full_name',
            ', ',
            distinct=True,
        ))

    def annotate_usernames(self):
        """Annotates for each journal all journal users full name as a string joined by ', ' as `usernames`"""
        return self.annotate(usernames=StringAgg('authors__user__username', ', ', distinct=True))

    def annotate_groups(self):
        """Annotates for each journal all journal users their groups as an array of group pks `usernames`"""
        return self.annotate(groups=ArrayAgg(
            'authors__user__participation__groups',
            filter=Q(authors__user__participation__groups__isnull=False),
            distinct=True,
        ))


class JournalManager(models.Manager):
    def get_queryset(self):
        return (
            JournalQuerySet(self.model, using=self._db)
            .allowed_journals()
            .annotate_fields()
        )


class Journal(CreateUpdateModel):
    """Journal.

    A journal is a collection of Nodes that holds the student's
    entries, deadlines and more. It contains the following:
    - assignment: a foreign key linked to an assignment.
    - user: a foreign key linked to a user.
    """
    UNLIMITED = 0
    all_objects = models.Manager.from_queryset(JournalQuerySet)()
    objects = JournalManager()

    ANNOTATED_FIELDS = [
        'full_names',
        'grade',
        'unpublished',
        'needs_marking',
        'import_requests',
        'name',
        'image',
        'usernames',
        'needs_lti_link',
        'groups',
    ]

    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE,
    )

    bonus_points = models.FloatField(
        default=0,
    )

    author_limit = models.IntegerField(
        default=1
    )

    stored_name = models.TextField(
        null=True,
    )

    stored_image = models.TextField(
        null=True,
    )

    locked = models.BooleanField(
        default=False,
    )

    LMS_grade = models.IntegerField(
        default=0,
    )

    # NOTE: Any suggestions for a clear warning msg for all cases?
    outdated_link_warning_msg = 'This journal has an outdated LMS uplink and can no longer be edited. Visit  ' \
        + 'eJournal from an updated LMS connection.'

    def add_author(self, author):
        # NOTE: This approach sucks, author is now first added (SQL operation), then validation is run in the
        # save of the journal. This should obviously be validation first then change DB state.
        self.authors.add(author)
        self.save()

    def remove_author(self, author):
        self.authors.remove(author)
        self.remove_jirs_on_user_remove_from_jounal(author.user)

        if self.authors.count() == 0:
            self.reset()

    def reset(self):
        VLE.models.Entry.objects.filter(node__journal=self).delete()
        self.import_request_targets.all().delete()
        self.import_request_sources.filter(state=VLE.models.JournalImportRequest.PENDING).delete()

    def get_sorted_nodes(self):
        """
        Get all the nodes of a journal in sorted order.

        Sorts first by preset due date, defaulting to entry creation date when dealing with an unlimited entry.
        """
        return self.node_set.select_related(
            'entry',
            'preset'
        ).annotate(sort_due_date=Case(
            When(preset__isnull=False, then='preset__due_date'),
            default='entry__creation_date')
        ).order_by('sort_due_date')

    def remove_jirs_on_user_remove_from_jounal(self, user):
        """
        Removes any pending JIRs if none of the other journal's authors are also author in the JIR source.

        Args:
            self (:model:`VLE.journal`): Journal where the user is being removed from.
            user (:model:`VLE.user`): User removed from the journal.
        """
        journal_authors_except_user = self.authors.all().exclude(user=user)
        pending_journal_jirs_authored_by_user = self.import_request_targets.filter(
            author=user, state=VLE.models.JournalImportRequest.PENDING)

        jirs_with_no_shared_source_authors = pending_journal_jirs_authored_by_user.exclude(
            source__authors__user__in=journal_authors_except_user.values('user'))

        jirs_with_no_shared_source_authors.delete()

    def save(self, *args, **kwargs):
        if not self.author_limit == self.UNLIMITED and self.authors.count() > self.author_limit:
            raise ValidationError('Journal users exceed author limit.')
        if not self.assignment.is_group_assignment and self.author_limit > 1:
            raise ValidationError('Journal author limit of a non group assignment exceeds 1.')

        is_new = self._state.adding
        if self.stored_name is None:
            if self.assignment.is_group_assignment:
                self.stored_name = 'Journal {}'.format(Journal.objects.filter(assignment=self.assignment).count() + 1)

        super(Journal, self).save(*args, **kwargs)
        # On create add preset nodes
        if is_new:
            self.generate_missing_nodes()

    @property
    def published_nodes(self):
        return self.node_set.filter(entry__grade__published=True).order_by('entry__grade__creation_date')

    @property
    def unpublished_nodes(self):
        return self.node_set.filter(
            Q(entry__grade__isnull=True) | Q(entry__grade__published=False),
            entry__isnull=False).order_by('entry__last_edited')

    @property
    def author(self):
        if self.author_limit > 1:
            raise VLEProgrammingError('Unsafe use of journal author property')
        return VLE.models.User.objects.filter(assignmentparticipation__journal=self).first()

    @property
    def missing_annotated_field(self):
        return any(not hasattr(self, field) for field in self.ANNOTATED_FIELDS)

    def can_add(self, user):
        """
        Checks wether the provided user can add an entry to the journal

        Used to help determine if the add node appears in the timeline.
        """
        return user \
            and self.authors.filter(user=user).exists() \
            and user.has_permission('can_have_journal', self.assignment) \
            and not len(self.needs_lti_link) > 0 \
            and self.assignment.format.template_set.filter(archived=False, preset_only=False).exists()

    def generate_missing_nodes(self, create=True):
        nodes = [VLE.models.Node(
            type=preset_node.type,
            entry=None,
            preset=preset_node,
            journal=self,
        ) for preset_node in self.assignment.format.presetnode_set.all()]

        if create:
            nodes = VLE.models.Node.objects.bulk_create(nodes)

        return nodes

    def to_string(self, user=None):
        if user is None or not user.can_view(self):
            return 'Journal'

        return self.name
