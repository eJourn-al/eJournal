from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Min, Q
from django.utils import timezone
from django.utils.timezone import now

from VLE.tasks.notifications import generate_new_assignment_notifications
from VLE.utils import sanitization
from VLE.utils.error_handling import VLEBadRequest, VLEProgrammingError

from .assignment_participation import AssignmentParticipation
from .base import CreateUpdateModel
from .course import Course
from .entry import Entry
from .journal import Journal
from .journal_import_request import JournalImportRequest
from .notification import Notification
from .user import User


class Assignment(CreateUpdateModel):
    """Assignment.

    An Assignment entity has the following features:
    - name: name of the assignment.
    - description: description for the assignment.
    - courses: a foreign key linked to the courses this assignment
    is part of.
    - format: a one-to-one key linked to the format this assignment
    holds. The format determines how a students' journal is structured.
    - active_lti_id: (optional) the active VLE id of the assignment linked through LTI which receives grade updates.
    - lti_id_set: (optional) the set of VLE assignment lti_id_set which permit basic access.
    """
    class Meta:
        constraints = [
            CheckConstraint(check=Q(points_possible__gte=0.0), name='points_possible_gte_0'),
        ]

    name = models.TextField()
    description = models.TextField(
        blank=True,
    )
    author = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True
    )
    is_published = models.BooleanField(default=False)
    points_possible = models.FloatField(
        'points_possible',
        default=10,
    )
    unlock_date = models.DateTimeField(
        'unlock_date',
        null=True,
        blank=True
    )
    due_date = models.DateTimeField(
        'due_date',
        null=True,
        blank=True
    )
    lock_date = models.DateTimeField(
        'lock_date',
        null=True,
        blank=True
    )
    courses = models.ManyToManyField(
        'Course',
    )
    assigned_groups = models.ManyToManyField(
        'Group',
    )

    format = models.OneToOneField(
        'Format',
        on_delete=models.CASCADE
    )

    active_lti_id = models.TextField(
        null=True,
        unique=True,
        blank=True,
    )
    lti_id_set = ArrayField(
        models.TextField(),
        default=list,
    )

    is_group_assignment = models.BooleanField(default=False)
    remove_grade_upon_leaving_group = models.BooleanField(default=False)
    can_set_journal_name = models.BooleanField(default=False)
    can_set_journal_image = models.BooleanField(default=False)
    can_lock_journal = models.BooleanField(default=False)

    def get_all_users(self, user=None, courses=None, journals_only=True):
        """Get all users in an assignment

        if user is set, only get the users that are in the courses that user is connected to as well
        if courses is set, only get the users that are in the given courses
        if journals_only is true, only get users that also have a journal (default: true)
        """
        if courses is None:
            courses = self.courses.all()
        if user is not None:
            courses = courses.filter(users=user)
        if journals_only:
            users = Journal.objects.filter(assignment=self).values('authors__user')
        else:
            users = self.assignmentparticipation_set.values('user')
        return User.objects.filter(participations__in=courses, pk__in=users).distinct()

    def get_users_in_own_groups(self, user, courses=None, **kwargs):
        if courses is None:
            courses = self.courses.all()
        groups = user.participation_set.filter(course__in=courses).values('groups')
        return self.get_all_users(
            user=user, courses=courses, **kwargs).filter(participation__groups__in=groups).distinct()

    def has_users_in_own_groups(self, *args, **kwargs):
        return self.get_users_in_own_groups(*args, **kwargs).exists()

    def has_lti_link(self):
        return self.active_lti_id is not None

    def is_locked(self):
        return self.unlock_date and self.unlock_date > now() or self.lock_date and self.lock_date < now()

    def add_course(self, course):
        if not self.courses.filter(pk=course.pk).exists():
            self.courses.add(course)
            existing = AssignmentParticipation.objects.filter(assignment=self).values('user')
            for user in course.users.exclude(pk__in=existing):
                AssignmentParticipation.objects.create(assignment=self, user=user)

    @classmethod
    def state_actions(cls, new, old=None):
        """
        Returns a dictionary containing multiple actionable booleans. Used
        either for validation, or for further processing of the assignment.

        Args:
            new (:model:`VLE.assignment` or dict): new contains the data to update.
            old (:model:`VLE.assignment`): assignment instance as currently in the DB.

        Returns:
            (dict)
                published (bool): assignment is published and create or was unpublished
                unpublished (bool): assignment was published.
                type_changed (bool): assignment group_assignment field changed.
                active_lti_id_modified (bool): lti_id set and new or lti_id changed.
        """
        if isinstance(new, dict):
            new = cls(**new)

        is_new = not new.pk

        if not is_new and not old:
            raise VLEProgrammingError('Old assignment state is required to check for state actions.')

        if is_new:
            published = new.is_published
            unpublished = False
            type_changed = False
            active_lti_id_modified = new.active_lti_id is not None
        else:
            published = not old.is_published and new.is_published
            unpublished = old.is_published and not new.is_published
            type_changed = old.is_group_assignment != new.is_group_assignment
            active_lti_id_modified = old.active_lti_id != new.active_lti_id

        return {
            'published': published,
            'unpublished': unpublished,
            'type_changed': type_changed,
            'active_lti_id_modified': active_lti_id_modified
        }

    def validate_unlock_date(self):
        if self.due_date and self.unlock_date > self.due_date:
            raise ValidationError('Unlocks after due date.')

        if self.lock_date and self.unlock_date > self.lock_date:
            raise ValidationError('Unlocks after lock date.')

        if self.format.presetnode_set.filter(unlock_date__lt=self.unlock_date).exists():
            raise ValidationError('One or more deadlines unlock before the assignment unlocks.')

        if self.format.presetnode_set.filter(due_date__lt=self.unlock_date).exists():
            raise ValidationError('One or more deadlines are due before the assignment unlocks.')

        if self.format.presetnode_set.filter(lock_date__lt=self.unlock_date).exists():
            raise ValidationError('One or more deadlines are locked before the assignment unlocks.')

    def validate_due_date(self):
        if self.unlock_date and self.due_date < self.unlock_date:
            raise ValidationError('Due before unlock date.')

        if self.lock_date and self.due_date > self.lock_date:
            raise ValidationError('Due after lock date.')

        if self.format.presetnode_set.filter(unlock_date__gt=self.due_date).exists():
            raise ValidationError('One or more deadlines unlock after the assignment is due.')

        if self.format.presetnode_set.filter(due_date__gt=self.due_date).exists():
            raise ValidationError('One or more deadlines are due after the assignment is due.')

    def validate_lock_date(self):
        if self.unlock_date and self.lock_date < self.unlock_date:
            raise ValidationError('Locks before unlock date.')

        if self.due_date and self.lock_date < self.due_date:
            raise ValidationError('Locks before due date.')

        if self.format.presetnode_set.filter(unlock_date__gt=self.lock_date).exists():
            raise ValidationError('One or more deadlines unlock after the assignment locks.')

        if self.format.presetnode_set.filter(due_date__gt=self.lock_date).exists():
            raise ValidationError('One or more deadlines are due after the assignment locks.')

        if self.format.presetnode_set.filter(lock_date__gt=self.lock_date).exists():
            raise ValidationError('One or more deadlines are locked after the assignment locks.')

    @staticmethod
    def validate(new, unpublished, type_changed, active_lti_id_modified, old=None):
        """
        Args:
            new (:model:`VLE.assignment`): new contains the data to update.
            unpublished (bool): assignment was published.
            type_changed (bool): assignment group_assignment field changed.
            active_lti_id_modified (bool): lti_id set and new or lti_id changed.
            old (:model:`VLE.assignment`): assignment instance as currently in the DB.
        """
        if unpublished and not old.can_unpublish():
            raise ValidationError(
                'Cannot unpublish an assignment that has entries or outstanding journal import requests.')

        if type_changed and old.has_entries():
            raise ValidationError('Cannot change the type of an assignment that has entries.')

        if active_lti_id_modified and new.conflicting_lti_link():
            raise ValidationError("An lti_id should be unique, and only part of a single assignment's lti_id_set.")

        if new.unlock_date:
            new.validate_unlock_date()

        if new.due_date:
            new.validate_due_date()

        if new.lock_date:
            new.validate_lock_date()

    def save(self, *args, **kwargs):
        is_new = not self.pk  # self._state.adding is false when copying an instance as, inst.pk = None, inst.save()

        if not is_new:
            old = Assignment.objects.get(pk=self.pk)

        state_actions = Assignment.state_actions(new=self, old=None if is_new else old)

        Assignment.validate(
            new=self,
            old=None if is_new else old,
            unpublished=state_actions['unpublished'],
            type_changed=state_actions['type_changed'],
            active_lti_id_modified=state_actions['active_lti_id_modified']
        )

        self.description = sanitization.strip_script_tags(self.description)
        if self.active_lti_id is not None and self.active_lti_id not in self.lti_id_set:
            self.lti_id_set.append(self.active_lti_id)

        super(Assignment, self).save(*args, **kwargs)

        if state_actions['active_lti_id_modified']:
            self.handle_active_lti_id_modified()

        if state_actions['type_changed']:
            self.handle_type_change()

        if state_actions['published']:
            self.handle_publish()
        elif state_actions['unpublished']:
            self.handle_unpublish()

    def setup_journals(self, new_assignment_notification=False):
        """
        Creates missing journals and assigment participations for all the assignment's users.

        When {new_assignment_notification} it will also create a new assignment notification for all provided users
        """
        if self.is_group_assignment:
            return

        users = User.objects.filter(participations__in=self.courses.all()).distinct()
        users_missing_aps = users.exclude(assignmentparticipation__assignment=self)
        aps_without_journal = AssignmentParticipation.objects.filter(
            assignment=self,
            journal__isnull=True,
            user__in=users,
        )

        # Bulk update existing assignment participations
        self.connect_assignment_participations_to_journals(aps_without_journal)

        # Generate new assignment notification for all users already in course
        generate_new_assignment_notifications.apply_async(
            args=[list(AssignmentParticipation.objects.filter(
                assignment=self,
            ).exclude(user=self.author).values_list('pk', flat=True))],
            countdown=settings.WEBSERVER_TIMEOUT,
        )

        # Bulk create missing assignment participations, automatically generates journals & nodes
        AssignmentParticipation.objects.bulk_create(
            [
                AssignmentParticipation(assignment=self, user=user)
                for user in users_missing_aps
            ],
            new_assignment_notification=new_assignment_notification
        )

    def connect_assignment_participations_to_journals(self, aps):
        """Connect the {aps} to a newly created journal"""
        # Bulk create journals for users that have an AP already
        journals = Journal.objects.bulk_create(
            [Journal(assignment=self) for _ in range(len(aps))]
        )
        for ap, journal in zip(aps, journals):
            ap.journal = journal
        return AssignmentParticipation.objects.bulk_update(aps, ['journal'])

    def handle_active_lti_id_modified(self):
        """
        Reset all the Journals (APs) sourcedids and grade_urls.

        On on each LTI launch, these values are once again set if present.
        """
        AssignmentParticipation.objects.filter(assignment=self).update(sourcedid=None, grade_url=None)

    def handle_type_change(self):
        """
        When the assignments type is changed from group journal to individual journals or vice versa,
        delete all journals.

        A group assignment requires no initial journals (these are setup at a later stage)
        For an individual assignment `setup_journals` will recreate all missing journals as individual ones.
        """
        Journal.objects.filter(assignment=self).delete()

        if not self.is_group_assignment:
            self.setup_journals()

    def handle_publish(self):
        """
        Should be called when an assignment is published.
        Either created as published, or released as such (going from unpublished to published)
        """
        if not self.is_group_assignment:
            self.setup_journals(new_assignment_notification=True)

    def handle_unpublish(self):
        """
        Should be called when an assignment is unpublished. Publish state is changed from True to False.
        """
        self.notification_set.filter(type=Notification.NEW_ASSIGNMENT).delete()

    def get_active_lti_course(self):
        """"Query for retrieving the course which matches the active lti id of the assignment."""
        courses = self.courses.filter(assignment_lti_id_set__contains=[self.active_lti_id])
        return courses.first()

    def get_active_course(self, user):
        """"
        Query for retrieving the course which is most relevant to the assignment.

        Compatible with prefetched courses.
        Will trigger N permission queries for N courses.
        """
        # If there are no courses connected, return none
        courses = self.courses.all()
        if not self.courses:
            return None

        can_view_course_map = {}

        def cached_can_view_courses(course):
            if course not in can_view_course_map:
                can_view_course_map[course] = user.can_view(course)
            return can_view_course_map[course]

        # Get matching LTI course if possible
        for course in courses:
            if self.active_lti_id in course.assignment_lti_id_set:
                if cached_can_view_courses(course):
                    return course

        courses_with_startdate = [course for course in courses if course.startdate]
        now = timezone.now().date()

        # Else get course that started the most recent
        comparison = [course for course in courses_with_startdate if course.startdate <= now]
        comparison.sort(key=lambda x: x.startdate, reverse=True)
        for course in comparison:
            if cached_can_view_courses(course):
                return course

        # Else get the course that starts the soonest
        comparison = [course for course in courses_with_startdate if course.startdate > now]
        comparison.sort(key=lambda x: x.startdate)
        for course in comparison:
            if cached_can_view_courses(course):
                return course

        # Else get the first course without start date
        comparison = [course for course in courses if course.startdate is None]
        comparison.sort(key=lambda x: x.pk)
        for course in comparison:
            if cached_can_view_courses(course):
                return course

        return None

    def get_lti_id_from_course(self, course):
        """Gets the assignment lti_id that belongs to the course assignment pair if it exists."""
        if not isinstance(course, Course):
            raise VLEProgrammingError("Expected instance of type Course.")

        intersection = list(set(self.lti_id_set).intersection(course.assignment_lti_id_set))
        return intersection[0] if intersection else None

    def set_active_lti_course(self, course):
        active_lti_id = self.get_lti_id_from_course(course)
        if active_lti_id:
            self.active_lti_id = active_lti_id
            self.save()
        else:
            raise VLEBadRequest("This course is not connected to the assignment")

    def add_lti_id(self, lti_id, course):
        if self.get_lti_id_from_course(course) is not None:
            raise VLEBadRequest('Assignment already used in course.')
        # Update assignment
        self.active_lti_id = lti_id
        if not self.courses.filter(pk=course.pk).exists():
            self.courses.add(course)
        self.save()
        # Update course
        course.add_assignment_lti_id(lti_id)
        course.save()

    def has_entries(self):
        return Entry.objects.filter(node__journal__assignment=self).exists()

    def has_outstanding_jirs(self):
        return JournalImportRequest.objects.filter(target__assignment=self, state=JournalImportRequest.PENDING).exists()

    def conflicting_lti_link(self):
        """
        Checks if other assignments exist which are or were at one point linked to its active lti id.
        """
        return Assignment.objects.filter(lti_id_set__contains=[self.active_lti_id]).exclude(pk=self.pk).exists()

    def can_unpublish(self):
        return not (self.has_entries() or self.has_outstanding_jirs())

    def get_teacher_deadline(self):
        """
        Return the earliest date that an entry has been submitted and is not yet graded or has an unpublished grade
        """
        return Journal.objects.filter(assignment=self).require_teacher_action().values(
            'node__entry__last_edited'
        ).aggregate(
            Min('node__entry__last_edited')
        )['node__entry__last_edited__min']

    def get_student_deadline(self, journal):
        """
        Get student deadline.

        This function gets the first upcoming deadline.
        It checks for the first entrydeadline that still need to submitted and still can be, or for the first
        progressnode that is not yet fullfilled.
        """
        grade_sum = journal.bonus_points if journal else 0
        deadline_due_date = None
        deadline_label = None

        if journal is not None:
            for node in journal.get_sorted_nodes().prefetch_related('entry__grade'):
                # Sum published grades to check if PROGRESS node is fullfiled
                if node.holds_published_grade:
                    grade_sum += node.entry.grade.grade
                elif node.is_deadline and node.open_deadline():
                    deadline_due_date = node.preset.due_date
                    deadline_label = node.preset.forced_template.name
                    break
                elif node.is_progress and node.open_deadline(grade=grade_sum):
                    deadline_due_date = node.preset.due_date
                    deadline_label = "{:g}/{:g} points".format(grade_sum, node.preset.target)
                    break

        # If no deadline is found, but the points possible has not been reached,
        # use the assignment due date as the deadline
        if deadline_due_date is None and grade_sum < self.points_possible:
            if self.due_date or self.lock_date and self.lock_date < timezone.now():
                deadline_due_date = self.due_date
                deadline_label = 'End of assignment'

        return deadline_due_date, deadline_label

    def to_string(self, user=None):
        if user is None:
            return "Assignment"
        if not user.can_view(self):
            return "Assignment"

        return "{} ({})".format(self.name, self.pk)
