"""
models.py.

Database file
"""
import os
import random
import string

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
from django.contrib.postgres.fields import ArrayField, CIEmailField, CITextField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import (Case, CharField, CheckConstraint, Count, F, FloatField, IntegerField, Min, OuterRef,
                              Prefetch, Q, Subquery, Sum, TextField, Value, When)
from django.db.models.deletion import CASCADE, SET_NULL
from django.db.models.functions import Cast, Coalesce
from django.db.models.query import QuerySet
from django.dispatch import receiver
from django.utils import timezone
from django.utils.timezone import now

import VLE.permissions
import VLE.utils.file_handling as file_handling
from VLE.tasks.email import send_push_notification
from VLE.tasks.notifications import generate_new_assignment_notifications, generate_new_node_notifications
from VLE.utils import sanitization
from VLE.utils.error_handling import (VLEBadRequest, VLEParticipationError, VLEPermissionError, VLEProgrammingError,
                                      VLEUnverifiedEmailError)
from VLE.utils.query_funcs import Round2


class CreateUpdateModel(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)
    update_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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


def gen_url(node=None, journal=None, assignment=None, course=None, user=None):
    """Generate the corresponding frontend url to the supplied object.

    Works for: node, journal, assignment, and course
    User needs to be added if no course is supplied, this is to get the correct course.
    """
    if not (node or journal or assignment or course):
        raise VLEProgrammingError('(gen_url) no object was supplied.')

    if journal is None and node is not None:
        journal = node.journal
    if assignment is None and journal is not None:
        assignment = journal.assignment
    if course is None and assignment is not None:
        if user is None:
            raise VLEProgrammingError('(gen_url) if course is not supplied, user needs to be supplied.')
        course = assignment.get_active_course(user)
        if course is None:
            raise VLEParticipationError(assignment, user)

    url = '{}/Home/Course/{}'.format(settings.BASELINK, course.pk)
    if assignment:
        url += '/Assignment/{}'.format(assignment.pk)
        if journal:
            url += '/Journal/{}'.format(journal.pk)
            if node:
                url += '?nID={}'.format(node.pk)

    return url


# https://stackoverflow.com/a/2257449
def access_gen(size=128, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


class FileContextQuerySet(models.QuerySet):
    def unused_file_field_files(self, func='filter'):
        """Queries for files linked to a FILE field where the data no longer holds the FC's `pk`"""
        return getattr(self, func)(
            ~Q(content__data=Cast(F('pk'), TextField())),
            content__field__type=VLE.models.Field.FILE,
        )

    def unused_rich_text_field_files(self, func='filter'):
        """Queries for files linked to a FILE field where the data no longer holds the FC's `access_id`"""
        return getattr(self, func)(
            ~Q(content__data__contains=F('access_id')),
            content__field__type=VLE.models.Field.RICH_TEXT,
        )

    def unused_category_description_files(self, func='filter'):
        return getattr(self, func)(
            ~Q(category__description__contains=F('access_id')),
            category__isnull=False,
        )


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


class UserQuerySet(models.QuerySet):
    def bulk_create(self, users, *args, **kwargs):
        with transaction.atomic():
            users = super().bulk_create(users, *args, **kwargs)

            # Bulk create preferences.
            preferences = []
            for user in users:
                preferences.append(Preferences(user=user))
            Preferences.objects.bulk_create(preferences)

            return users

    def annotate_course_role(self, course):
        """
        Annotates a users course participation role as `role_name` for a specific course.
        Defaults to None if the user is not a participant of that course.
        """
        role_sub_qry = Participation.objects.filter(user=OuterRef('pk'), course=course).select_related('role')
        return self.annotate(role_name=Subquery(role_sub_qry.values('role__name')))

    def prefetch_course_groups(self, course):
        """Prefetches all groups for the users related to the provided course"""
        return self.prefetch_related(
            Prefetch(
                'participation_set',
                queryset=Participation.objects.filter(course=course).prefetch_related('groups')
            )
        )


class UserManagerExtended(UserManager):
    """Using from queryset not possible due to the extra functionality that comes with the UserManager"""
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)


class User(AbstractUser):
    """User.

    User is an entity in the database with the following features:
    - full_name: full name of the user
    - email: email of the user.
    - verified_email: Boolean to indicate if the user has validated their email address.
    - password: the hash of the password of the user.
    - lti_id: the DLO id of the user.
    """
    objects = UserManagerExtended()

    UNKNOWN_STR = 'Unknown or deleted account'

    full_name = models.CharField(
        null=False,
        max_length=200
    )
    username = CITextField(
        unique=True,
        max_length=150,
    )
    email = CIEmailField(
        blank=True,
        unique=True,
        null=True,
    )
    verified_email = models.BooleanField(
        default=False
    )
    lti_id = models.TextField(
        null=True,
        unique=True,
        blank=True,
    )
    profile_picture = models.TextField(
        null=True
    )
    is_teacher = models.BooleanField(
        default=False
    )
    feedback_file = models.FileField(
        null=True,
        blank=True,
        upload_to=file_handling.get_feedback_file_path,
        max_length=255,
    )
    is_test_student = models.BooleanField(
        default=False
    )

    def check_permission(self, permission, obj=None, message=None):
        """
        Throws a VLEPermissionError when the user does not have the specified permission, as defined by
        has_permission.
        """
        if not self.has_permission(permission, obj):
            raise VLEPermissionError(permission, message)

    def has_permission(self, permission, obj=None):
        """
        Returns whether the user has the given permission.
        If obj is None, it tests the general permissions.
        If obj is a Course, it tests the course permissions.
        If obj is an Assignment, it tests the assignment permissions.
        Raises a VLEProgramming error when misused.
        """
        if obj is None:
            return VLE.permissions.has_general_permission(self, permission)
        if isinstance(obj, Course):
            return VLE.permissions.has_course_permission(self, permission, obj)
        if isinstance(obj, Assignment):
            return VLE.permissions.has_assignment_permission(self, permission, obj)
        raise VLEProgrammingError("Permission object must be of type None, Course or Assignment.")

    def check_verified_email(self):
        if not self.verified_email:
            raise VLEUnverifiedEmailError()

    def check_participation(self, obj):
        if not self.is_participant(obj):
            raise VLEParticipationError(obj, self)

    def is_supervisor_of(self, user):
        if self.is_superuser:
            return True

        return VLE.permissions.is_user_supervisor_of(self, user)

    def is_participant(self, obj):
        if self.is_superuser:
            return True
        if isinstance(obj, Course):
            return Course.objects.filter(pk=obj.pk, users=self).exists()
        if isinstance(obj, Assignment):
            return Assignment.objects.filter(pk=obj.pk, courses__users=self).exists()
        raise VLEProgrammingError("Participant object must be of type Course or Assignment.")

    def check_can_view(self, obj):
        if not self.can_view(obj):
            raise VLEPermissionError(message='You are not allowed to view {}'.format(obj.to_string(user=self)))

    def can_view(self, obj):
        if self.is_superuser:
            return True

        if isinstance(obj, Course):
            return self.is_participant(obj)

        elif isinstance(obj, Assignment):
            if self.is_participant(obj):
                if self.has_permission('can_have_journal', obj) and obj.assigned_groups.exists() and \
                   not obj.assigned_groups.filter(participation__user=self).exists():
                    return False
                return obj.is_published or self.has_permission('can_view_unpublished_assignment', obj)
            return False
        elif isinstance(obj, Journal):
            if not obj.authors.filter(user=self).exists():
                return self.has_permission('can_view_all_journals', obj.assignment)
            else:
                return self.has_permission('can_have_journal', obj.assignment)

        elif isinstance(obj, Comment):
            if not self.can_view(obj.entry.node.journal):
                return False
            if obj.published:
                return True
            return self.has_permission('can_grade', obj.entry.node.journal.assignment)

        elif isinstance(obj, User):
            if self == obj:
                return True
            if VLE.permissions.is_user_supervisor_of(self, obj):
                return True
            if VLE.permissions.is_user_supervisor_of(obj, self):
                return True
            if Journal.objects.filter(authors__user__in=[self]).filter(authors__user__in=[obj]).exists():
                return True

        return False

    def can_edit(self, obj):
        return VLE.permissions.can_edit(self, obj)

    def check_can_edit(self, obj):
        if not self.can_edit(obj):
            raise VLEPermissionError(message='You are not allowed to edit {}'.format(str(obj)))

    def to_string(self, user=None):
        if user is None:
            return "User"
        if not user.can_view(self):
            return "User"

        return self.username + " (" + str(self.pk) + ")"

    def save(self, *args, **kwargs):
        if not self.email and not self.is_test_student:
            raise ValidationError('A legitimate user requires an email adress.')

        if self._state.adding:
            if self.is_test_student and settings.LTI_TEST_STUDENT_FULL_NAME not in self.full_name:
                raise ValidationError('Test user\'s full name deviates on creation.')
        else:
            pre_save = User.objects.get(pk=self.pk)
            if pre_save.is_test_student and not self.is_test_student:
                raise ValidationError('A test user is expected to remain a test user.')

        # Enforce unique constraint
        if self.email == '':
            self.email = None

        if isinstance(self.email, str):
            self.email = self.email.lower()
        if isinstance(self.username, str):
            self.username = self.username.lower()

        super(User, self).save(*args, **kwargs)


@receiver(models.signals.post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create matching preferences whenever a user object is created."""
    if created:
        Preferences.objects.create(user=instance)


@receiver(models.signals.post_delete, sender=User)
def auto_delete_feedback_file_on_user_delete(sender, instance, **kwargs):
    """Deletes feedback file from filesystem when corresponding `User` object is deleted."""
    if instance.feedback_file:
        if os.path.isfile(instance.feedback_file.path):
            os.remove(instance.feedback_file.path)


@receiver(models.signals.post_delete, sender=User)
def delete_dangling_files(sender, instance, **kwargs):
    """Deletes FileContext instances which are only of interest to the deleted user."""
    for f in FileContext.objects.filter(author=instance):
        if f.cascade_from_user(instance):
            f.delete()


class Preferences(CreateUpdateModel):
    """Preferences.

    Describes the preferences of a user:
    - show_format_tutorial: whether or not to show the assignment format tutorial.
    - ..._reminder: when a user wants to be reminded of an event that will happen in the future
    - ..._notifications: when a user wants to receive this notification, either immidiatly, daily, weekly, or never
    - hide_version_alert: latest version number for which a version alert has been dismissed.
    """
    DAILY = 'd'
    WEEKLY = 'w'
    PUSH = 'p'
    OFF = 'o'
    DAY_AND_WEEK = 'p'
    WEEK = 'w'
    DAY = 'd'
    FREQUENCIES = (
        (DAILY, 'd'),
        (WEEKLY, 'w'),
        (PUSH, 'p'),
        (OFF, 'o'),
    )
    REMINDER = (
        (DAY, 'd'),
        (WEEK, 'w'),
        (DAY_AND_WEEK, 'p'),
        (OFF, 'o'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True
    )

    new_grade_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=PUSH,
    )
    new_comment_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=DAILY,
    )
    new_assignment_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=WEEKLY,
    )
    new_course_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=WEEKLY,
    )
    new_entry_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=WEEKLY,
    )
    new_node_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=WEEKLY,
    )
    new_journal_import_request_notifications = models.TextField(
        max_length=1,
        choices=FREQUENCIES,
        default=WEEKLY,
    )

    # Only get notifications of people that are in your group
    group_only_notifications = models.BooleanField(
        default=True,
    )

    upcoming_deadline_reminder = models.TextField(
        max_length=1,
        choices=REMINDER,
        default=DAY_AND_WEEK,
    )

    show_format_tutorial = models.BooleanField(
        default=True
    )
    auto_select_ungraded_entry = models.BooleanField(
        default=True
    )
    auto_proceed_next_journal = models.BooleanField(
        default=False
    )
    hide_version_alert = models.TextField(
        max_length=20,
        null=True,
    )
    SAVE = 's'
    PUBLISH = 'p'
    GRADE_BUTTON_OPTIONS = (
        (SAVE, 's'),
        (PUBLISH, 'p'),
    )
    grade_button_setting = models.TextField(
        max_length=1,
        choices=GRADE_BUTTON_OPTIONS,
        default=PUBLISH,
    )
    PUBLISH_AND_PUBLISH_GRADE = 'g'
    COMMENT_SEND_BUTTON_OPTIONS = (
        (SAVE, 's'),
        (PUBLISH, 'p'),
        (PUBLISH_AND_PUBLISH_GRADE, 'g'),
    )
    comment_button_setting = models.TextField(
        max_length=2,
        choices=COMMENT_SEND_BUTTON_OPTIONS,
        default=SAVE,
    )

    def to_string(self, user=None):
        return "Preferences"


class Notification(CreateUpdateModel):
    NEW_COURSE = 'COURSE'
    NEW_ASSIGNMENT = 'ASSIGNMENT'
    NEW_NODE = 'NODE'
    NEW_ENTRY = 'ENTRY'
    NEW_GRADE = 'GRADE'
    NEW_COMMENT = 'COMMENT'
    NEW_JOURNAL_IMPORT_REQUEST = 'JIR'
    UPCOMING_DEADLINE = 'DEADLINE'
    TYPES = {
        NEW_COURSE: {
            'name': 'new_course_notifications',
            'content': {
                'title': 'New course membership',
                'content': 'You are now a member of {course}.',
                'button_text': 'View Course',
            },
        },
        NEW_ASSIGNMENT: {
            'name': 'new_assignment_notifications',
            'content': {
                'title': 'New assignment',
                'content': 'The assignment {assignment} is now available.',
                'button_text': 'View Assignment',
            },
        },
        NEW_NODE: {
            'name': 'new_node_notifications',
            'content': {
                'title': 'New deadline',
                'content': 'A new deadline has been added to your journal.',
                'button_text': 'View Deadline',
            },
        },
        NEW_ENTRY: {
            'name': 'new_entry_notifications',
            'content': {
                'title': 'New entry',
                'content': '{entry} was posted in the journal of {journal}.',
                'batch_content': '{n} new entries were posted in  the journal of {journal}.',
                'button_text': 'View Entry',
            },
        },
        NEW_GRADE: {
            'name': 'new_grade_notifications',
            'content': {
                'title': 'New grade',
                'content': '{entry} has been graded.',
                'batch_content': '{entry} has been graded.',
                'button_text': 'View Grade',
            },
        },
        NEW_COMMENT: {
            'name': 'new_comment_notifications',
            'content': {
                'title': 'New comment',
                'content': '{comment} commented on {entry}.',
                'batch_content': '{n} new comments on {entry} in the journal of {journal}.',
                'button_text': 'View Comment',
            },
        },
        NEW_JOURNAL_IMPORT_REQUEST: {
            'name': 'new_journal_import_request_notifications',
            'content': {
                'title': 'New journal import request',
                'content': '{journal} requested to import another journal.',
                'batch_content': '{journal} requested to import {n} other journals.',
                'button_text': 'View Request',
            },
        },
        UPCOMING_DEADLINE: {
            'name': 'None',
            'content': {
                'title': 'Upcoming deadline',
                'content': 'You have an unfinished deadline ({node}) that is due on {deadline}',
                'button_text': 'View Deadline',
            },
        },
    }
    # Specify which notifications can be batched in the email, and on what model field they need to be batched to
    BATCHED_TYPES = {
        NEW_ENTRY: 'journal',
        NEW_GRADE: 'entry',
        NEW_COMMENT: 'entry',
        NEW_JOURNAL_IMPORT_REQUEST: 'journal',
    }

    OWN_GROUP_TYPES = {NEW_ENTRY, NEW_COMMENT, NEW_JOURNAL_IMPORT_REQUEST}

    type = models.CharField(
        max_length=10,
        choices=((type, dic['name']) for type, dic in TYPES.items()),
        null=False,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    message = models.TextField()
    sent = models.BooleanField(
        default=False
    )

    course = models.ForeignKey(
        'course',
        on_delete=models.CASCADE,
        null=True,
    )
    assignment = models.ForeignKey(
        'assignment',
        on_delete=models.CASCADE,
        null=True,
    )
    journal = models.ForeignKey(
        'journal',
        on_delete=models.CASCADE,
        null=True,
    )
    node = models.ForeignKey(
        'node',
        on_delete=models.CASCADE,
        null=True,
    )
    entry = models.ForeignKey(
        'entry',
        on_delete=models.CASCADE,
        null=True,
    )
    grade = models.ForeignKey(
        'grade',
        on_delete=models.CASCADE,
        null=True,
    )
    comment = models.ForeignKey(
        'comment',
        on_delete=models.CASCADE,
        null=True,
    )
    jir = models.ForeignKey(
        'journalimportrequest',
        on_delete=models.CASCADE,
        null=True,
    )

    def _fill_text(self, text, n=None):
        if self.journal:
            journal = Journal.objects.get(pk=self.journal.pk)

        node_name = None
        if self.node:
            if self.node.is_progress:
                node_name = f"{journal.grade}/{self.node.preset.target}"
            elif self.node.is_deadline:
                node_name = self.node.preset.forced_template.name

        return text.format(
            comment=self.comment.author.full_name if self.comment else None,
            entry=self.entry.template.name if self.entry and self.entry.template else None,
            node=node_name,
            journal=journal.name if self.journal else None,
            assignment=self.assignment.name if self.assignment else None,
            course=self.course.name if self.course else None,
            deadline=self.node.preset.due_date.strftime("%B %-d at %H:%M") if self.node and self.node.preset else None,
            n=n,
        )

    @property
    def title(self):
        return self._fill_text(self.TYPES[self.type]['content']['title'])

    @property
    def content(self):
        return self._fill_text(self.TYPES[self.type]['content']['content'])

    @property
    def button_text(self):
        return Notification.TYPES[self.type]['content']['button_text']

    def batch_content(self, n=None):
        return self._fill_text(self.TYPES[self.type]['content']['batch_content'], n=n)

    @property
    def url(self):
        return gen_url(
            node=self.node, journal=self.journal, assignment=self.assignment, course=self.course, user=self.user)

    def has_journal_in_own_groups(self):
        """Checks if a notification is from a user that is connected to the notification user via a group"""
        return self.assignment.get_users_in_own_groups(self.user).filter(
            pk__in=self.journal.authors.values('user')).exists()

    @property
    def email_preference(self):
        return getattr(self.user.preferences, self.TYPES[self.type]['name'], None)

    def save(self, *args, **kwargs):
        # Should not create a notification if notifications are off for this type
        if self.email_preference == Preferences.OFF:
            return

        is_new = self._state.adding
        if is_new:
            if self.comment:
                self.entry = self.comment.entry
            elif self.grade:
                self.entry = self.grade.entry
            if self.entry:
                self.node = self.entry.node
            if self.node:
                self.journal = self.node.journal
            if self.jir:
                self.journal = self.jir.target
            if self.journal:
                self.assignment = self.journal.assignment
            if self.assignment:
                # Should get the active lti course if there is an active LTI link, else the normal procedure
                if self.assignment.active_lti_id:
                    self.course = self.assignment.get_active_lti_course()
                else:
                    self.course = self.assignment.get_active_course(self.user)

        # Should not create notifications for courses that the user cannot see
        if not self.user.can_view(self.course):
            return
        # Should not create a notification as user only wants notification from within their group
        # NOTE: it still sends notifications if there are no users in any groups
        if self.type in self.OWN_GROUP_TYPES and self.user.preferences.group_only_notifications \
           and self.assignment.has_users_in_own_groups(self.user) and not self.has_journal_in_own_groups():
            return

        super(Notification, self).save(*args, **kwargs)

        if is_new:
            # Send notification on creation if user preference is set to push, default (for reminders) is daily
            if self.email_preference == Preferences.PUSH:
                send_push_notification.delay(self.pk)


class Course(CreateUpdateModel):
    """Course.

    A Course entity has the following features:
    - name: name of the course.
    - author: the creator of the course.
    - abbreviation: a max three letter abbreviation of the course name.
    - startdate: the date that the course starts.
    - active_lti_id: (optional) the active VLE id of the course linked through LTI which receives grade updates.
    - lti_id_set: (optional) the set of VLE lti_id_set which permit basic access.
    """

    name = models.TextField()
    abbreviation = models.TextField(
        max_length=10,
        default='XXXX',
    )

    author = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True
    )

    users = models.ManyToManyField(
        'User',
        related_name='participations',
        through='Participation',
        through_fields=('course', 'user'),
    )

    startdate = models.DateField(
        null=True,
    )
    enddate = models.DateField(
        null=True,
    )

    active_lti_id = models.TextField(
        null=True,
        unique=True,
        blank=True,
    )

    # These LTI assignments belong to this course.
    assignment_lti_id_set = ArrayField(
        models.TextField(),
        default=list,
    )

    def add_assignment_lti_id(self, lti_id):
        if lti_id not in self.assignment_lti_id_set:
            self.assignment_lti_id_set.append(lti_id)

    def has_lti_link(self):
        return self.active_lti_id is not None

    def to_string(self, user=None):
        if user is None:
            return "Course"
        if not user.can_view(self):
            return "Course"

        return self.name + " (" + str(self.pk) + ")"


class Group(CreateUpdateModel):
    """Group.

    A Group entity has the following features:
    - name: the name of the group
    - course: the course where the group belongs to
    """
    name = models.TextField()

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    lti_id = models.TextField(
        null=True,
    )

    class Meta:
        """Meta data for the model: unique_together."""
        unique_together = ('lti_id', 'course')

    def to_string(self, user=None):
        if user is None:
            return "Group"
        if not user.can_view(self.course):
            return "Group"
        return "{} ({})".format(self.name, self.pk)


class Role(CreateUpdateModel):
    """Role.

    A complete overview of the role requirements can be found here:
    https://docs.google.com/spreadsheets/d/1M7KnEKL3cG9PMWfQi9HIpRJ5xUMou4Y2plnRgke--Tk

    A role defines the permissions of a user group within a course.
    - name: name of the role
    - list of permissions (can_...)
    """
    GENERAL_PERMISSIONS = [
        'can_edit_institute_details',
        'can_add_course'
    ]
    COURSE_PERMISSIONS = [
        'can_edit_course_details',
        'can_delete_course',

        'can_edit_course_roles',
        'can_view_course_users',
        'can_add_course_users',
        'can_delete_course_users',

        'can_add_course_user_group',
        'can_delete_course_user_group',
        'can_edit_course_user_group',

        'can_add_assignment',
        'can_delete_assignment',
    ]
    ASSIGNMENT_PERMISSIONS = [
        'can_edit_assignment',
        'can_grade',
        'can_publish_grades',

        'can_view_all_journals',
        'can_view_unpublished_assignment',
        'can_view_grade_history',

        'can_manage_journals',
        'can_have_journal',

        'can_comment',
        'can_edit_staff_comment',

        'can_post_teacher_entries',
        'can_manage_journal_import_requests',
    ]
    PERMISSIONS = COURSE_PERMISSIONS + ASSIGNMENT_PERMISSIONS

    name = models.TextField()

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    can_edit_course_details = models.BooleanField(default=False)
    can_delete_course = models.BooleanField(default=False)
    can_edit_course_roles = models.BooleanField(default=False)
    can_view_course_users = models.BooleanField(default=False)
    can_add_course_users = models.BooleanField(default=False)
    can_delete_course_users = models.BooleanField(default=False)
    can_add_course_user_group = models.BooleanField(default=False)
    can_delete_course_user_group = models.BooleanField(default=False)
    can_edit_course_user_group = models.BooleanField(default=False)
    can_add_assignment = models.BooleanField(default=False)
    can_delete_assignment = models.BooleanField(default=False)

    can_edit_assignment = models.BooleanField(default=False)
    can_manage_journals = models.BooleanField(default=False)
    can_view_all_journals = models.BooleanField(default=False)
    can_grade = models.BooleanField(default=False)
    can_publish_grades = models.BooleanField(default=False)
    can_view_grade_history = models.BooleanField(default=False)
    can_have_journal = models.BooleanField(default=False)
    can_comment = models.BooleanField(default=False)
    can_post_teacher_entries = models.BooleanField(default=False)
    can_edit_staff_comment = models.BooleanField(default=False)
    can_view_unpublished_assignment = models.BooleanField(default=False)
    can_manage_journal_import_requests = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.can_add_course_users and not self.can_view_course_users:
            raise ValidationError('A user needs to be able to view course users in order to add them.')

        if self.can_delete_course_users and not self.can_view_course_users:
            raise ValidationError('A user needs to be able to view course users in order to remove them.')

        if self.can_edit_course_user_group and not self.can_view_course_users:
            raise ValidationError('A user needs to be able to view course users in order to manage user groups.')

        if self.can_view_all_journals and self.can_have_journal:
            raise ValidationError('Teaching staff is not allowed to have a journal in their own course.')

        if self.can_grade and not self.can_view_all_journals:
            raise ValidationError('A user needs to be able to view journals in order to grade them.')

        if self.can_publish_grades and not (self.can_view_all_journals and self.can_grade):
            raise ValidationError('A user needs to be able to view and grade journals in order to publish grades.')

        if self.can_view_grade_history and not (self.can_view_all_journals and self.can_grade):
            raise ValidationError('A user needs to be able to view and grade journals in order to see a history\
                                   of grades.')

        if self.can_post_teacher_entries and not (self.can_publish_grades and self.can_grade):
            raise ValidationError('A user must be able to view and publish grades in order to post teacher entries.')

        if self.can_comment and not (self.can_view_all_journals or self.can_have_journal):
            raise ValidationError('A user requires a journal to comment on.')

        if self.can_edit_staff_comment and self.can_have_journal:
            raise ValidationError('Users who can edit staff comments are not allowed to have a journal themselves.')

        if self.can_edit_staff_comment and not self.can_comment:
            raise ValidationError('A user needs to be able to comment in order to edit other comments.')

        if self.can_manage_journal_import_requests and not self.can_grade:
            raise ValidationError('A user needs the permission to grade in order to manage import requests.')

        super(Role, self).save(*args, **kwargs)

    def to_string(self, user=None):
        if user is None:
            return "Role"
        if not user.can_view(self.course):
            return "Role"

        return "{} ({})".format(self.name, self.pk)

    class Meta:
        """Meta data for the model: unique_together."""

        unique_together = ('name', 'course',)


class Participation(CreateUpdateModel):
    """Participation.

    A participation defines the way a user interacts within a certain course.
    The user is now linked to the course, and has a set of permissions
    associated with its role.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role',
    )
    groups = models.ManyToManyField(
        Group,
        default=None,
    )

    def set_groups(self, groups):
        self.groups.set(groups)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        notify_user = kwargs.pop('notify_user', True)
        super(Participation, self).save(*args, **kwargs)

        # Instance is being created (not modified)
        if is_new:
            existing = AssignmentParticipation.objects.filter(user=self.user).values('assignment')
            for assignment in Assignment.objects.filter(courses__in=[self.course]).exclude(pk__in=existing):
                AssignmentParticipation.objects.create(assignment=assignment, user=self.user)
            if notify_user and self.user != self.course.author:
                Notification.objects.create(
                    type=Notification.NEW_COURSE,
                    user=self.user,
                    course=self.course
                )

    class Meta:
        """Meta data for the model: unique_together."""

        unique_together = ('user', 'course',)

    def to_string(self, user=None):
        if user is None:
            return "Participation"
        if not user.can_view(self.course):
            return "Participation"

        return "user: {}, course: {}, role: {}".format(
            self.user.to_string(user=user), self.course.to_string(user=user), self.role.to_string(user=user))


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

    name = models.TextField()
    description = models.TextField(
        null=True,
    )
    author = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True
    )
    is_published = models.BooleanField(default=False)
    points_possible = models.IntegerField(
        'points_possible',
        default=10
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
    courses = models.ManyToManyField(Course)
    assigned_groups = models.ManyToManyField(Group)

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
        generate_new_assignment_notifications.delay([
            ap.pk for ap in AssignmentParticipation.objects.filter(assignment=self).exclude(user=self.author)
        ])

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
        return VLE.models.Journal.objects.filter(assignment=self).require_teacher_action().values(
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
            for node in VLE.utils.generic_utils.get_sorted_nodes(journal).prefetch_related('entry__grade'):
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


class AssignmentParticipationQuerySet(models.QuerySet):
    def bulk_create(self, aps, *args, create_missing_journals=True, new_assignment_notification=True, **kwargs):
        with transaction.atomic():
            # Create missing journals
            if create_missing_journals:
                journals = []
                aps_missing_journal = []
                for ap in aps:
                    if not ap.journal:
                        journals.append(Journal(assignment=ap.assignment))
                        aps_missing_journal.append(ap)

                journals = Journal.objects.bulk_create(journals)
                for ap, journal in zip(aps_missing_journal, journals):
                    ap.journal = journal

            aps = super().bulk_create(aps, *args, **kwargs)

            # Generate new assignment notifications
            if new_assignment_notification:
                generate_new_assignment_notifications.delay([
                    ap.pk
                    for ap in aps if ap.user != ap.assignment.author
                ])
            return aps


class AssignmentParticipation(CreateUpdateModel):
    """AssignmentParticipation

    A user that is connected to an assignment
    this can then be used as a participation for a journal
    """
    objects = models.Manager.from_queryset(AssignmentParticipationQuerySet)()

    journal = models.ForeignKey(
        'Journal',
        on_delete=models.SET_NULL,
        related_name='authors',
        null=True,
    )

    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
    )

    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE
    )

    sourcedid = models.TextField(null=True)
    grade_url = models.TextField(null=True)

    def needs_lti_link(self):
        return self.assignment.active_lti_id is not None and self.sourcedid is None

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super(AssignmentParticipation, self).save(*args, **kwargs)

        # Instance is being created (not modified)
        if is_new:
            if self.assignment.is_published and not self.assignment.is_group_assignment and not self.journal:
                journal = Journal.objects.create(assignment=self.assignment)
                journal.add_author(self)

            if self.assignment.is_published and self.user != self.assignment.author:
                self.create_new_assignment_notification()

    def create_new_assignment_notification(self):
        Notification.objects.create(
            type=Notification.NEW_ASSIGNMENT,
            user=self.user,
            assignment=self.assignment,
        )

    def to_string(self, user=None):
        if user is None or not (user == self.user or user.is_supervisor_of(self.user)):
            return "Participant"

        return "{} in {}".format(self.user.username, self.assignment.name)

    class Meta:
        """A class for meta data.

        - unique_together: assignment and author must be unique together.
        """
        unique_together = ('assignment', 'user',)


class JournalQuerySet(models.QuerySet):
    def bulk_create(self, journals, *args, **kwargs):
        with transaction.atomic():
            journals = super().bulk_create(journals, *args, **kwargs)

            # Bulk create nodes
            nodes = []
            for journal in journals:
                nodes += journal.generate_missing_nodes(create=False)
            # Notifications should not be send when the journal is new. A "new assignment" notification is good enough
            Node.objects.bulk_create(nodes, new_node_notifications=False)

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
            Entry.objects.filter(
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
            Entry.objects.filter(
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
            Entry.objects.filter(
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
                filter=Q(import_request_targets__state=JournalImportRequest.PENDING),
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
        first_non_default_profile_pic_user_qry = Subquery(User.objects.filter(
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
        self.save()

    def reset(self):
        Entry.objects.filter(node__journal=self).delete()
        self.import_request_targets.all().delete()
        self.import_request_sources.filter(state=JournalImportRequest.PENDING).delete()

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
        return User.objects.filter(assignmentparticipation__journal=self).first()

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
        nodes = [Node(
            type=preset_node.type,
            entry=None,
            preset=preset_node,
            journal=self,
        ) for preset_node in self.assignment.format.presetnode_set.all()]

        if create:
            nodes = Node.objects.bulk_create(nodes)

        return nodes

    def to_string(self, user=None):
        if user is None or not user.can_view(self):
            return 'Journal'

        return self.name


def CASCADE_IF_UNLIMITED_ENTRY_NODE_ELSE_SET_NULL(collector, field, sub_objs, using):
    # NOTE: Either the function is not yet defined or the node type is not defined.
    # Tag Node.FIELD, update hard coded if changed
    unlimited_entry_nodes = [n for n in sub_objs if n.type == 'e']
    other_nodes = [n for n in sub_objs if n.type != 'e']

    CASCADE(collector, field, unlimited_entry_nodes, using)
    SET_NULL(collector, field, other_nodes, using)


class NodeQuerySet(models.QuerySet):
    def bulk_create(self, nodes, *args, new_node_notifications=True, **kwargs):
        nodes = super().bulk_create(nodes, *args, **kwargs)
        if new_node_notifications:
            generate_new_node_notifications.delay([node.pk for node in nodes])

        return nodes


class Node(CreateUpdateModel):
    """Node.

    The Node is an Timeline component.
    It can represent many things.
    There are three types of nodes:
    -Progress
        A node that merely is a deadline,
        and contains no entry. This deadline
        contains a 'target point amount'
        which should be reached before the
        due date has passed.
        This type of node has to be predefined in
        the Format. In the Format it is assigned a
        due date and a 'target point amount'.
    -Entry
        A node that is merely an entry,
        and contains no deadline. The entry
        can count toward a total
        'received point amount' which is deadlined
        by one or more Progress nodes.
        This type node can be created by the student
        an unlimited amount of times. It holds one
        of the by format predefined 'global templates'.
    -Entrydeadline
        A node that is both an entry and a deadline.
        This node is entirely separate from the
        Progress and Entry node.
        This type of node has to be predefined in
        the Format. In the Format it is assigned an
        unlock/lock date, a due date and a 'forced template'.
    """
    objects = models.Manager.from_queryset(NodeQuerySet)()

    PROGRESS = 'p'
    ENTRY = 'e'
    ENTRYDEADLINE = 'd'
    ADDNODE = 'a'
    TYPES = (
        (PROGRESS, 'progress'),
        (ENTRY, 'entry'),
        (ENTRYDEADLINE, 'entrydeadline'),
    )

    type = models.TextField(
        max_length=4,
        choices=TYPES,
    )

    entry = models.OneToOneField(
        'Entry',
        null=True,
        on_delete=CASCADE_IF_UNLIMITED_ENTRY_NODE_ELSE_SET_NULL,
    )

    journal = models.ForeignKey(
        'Journal',
        on_delete=models.CASCADE,
    )

    preset = models.ForeignKey(
        'PresetNode',
        null=True,
        on_delete=models.SET_NULL,
    )

    @property
    def is_deadline(self):
        return self.type == self.ENTRYDEADLINE

    @property
    def is_progress(self):
        return self.type == self.PROGRESS

    @property
    def is_entry(self):
        return self.type == self.ENTRY

    @property
    def holds_published_grade(self):
        return self.entry and self.entry.grade and self.entry.grade.grade and self.entry.grade.published

    def open_deadline(self, grade=None):
        """
        Checks if the deadline can be fulfilled

        The due date has not passed and no entry has been submissed or the progress goal has not yet been met.
        """
        if self.is_deadline:
            return not self.entry and self.preset.due_date > timezone.now()

        if self.is_progress:
            if not grade and not hasattr(self.journal, 'grade'):
                raise VLEProgrammingError('Expired deadline check requires a journal grade')

            if grade is None:
                grade = self.journal.grade
            return self.preset.target > grade and self.preset.due_date > timezone.now()

        if self.is_entry:
            return False  # An unlimited entry has no deadline to begin with

        raise VLEProgrammingError('Expired deadline check called on an unsupported node type')

    def to_string(self, user=None):
        return "Node"

    class Meta:
        unique_together = ('preset', 'journal')

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        super(Node, self).save(*args, **kwargs)

        # Create a notification for deadline PresetNodes
        if is_new and self.type in [self.ENTRYDEADLINE, self.PROGRESS]:
            for author in self.journal.authors.all():
                if author.user.can_view(self.journal):
                    Notification.objects.create(
                        type=Notification.NEW_NODE,
                        user=author.user,
                        node=self,
                    )


class Format(CreateUpdateModel):
    """Format.

    Format of a journal.
    The format determines how a students' journal is structured.
    See PresetNodes for attached 'default' nodes.
    """

    def to_string(self, user=None):
        return "Format"


class PresetNode(CreateUpdateModel):
    """PresetNode.

    A preset node is a node that has been pre-defined by the teacher.
    It contains the following features:
    - description: user defined text description of the preset node.
    - type: the type of the preset node (progress or entrydeadline node).
    - unlock_date: the date from which the preset node can be filled in.
    - due_date: the due date for this preset node.
    - lock_date: the date after which the preset node can no longer be fulfilled.
    - forced_template: the template for this preset node - null if PROGRESS node.
    - format: a foreign key linked to a format.
    """

    TYPES = (
        (Node.PROGRESS, 'progress'),
        (Node.ENTRYDEADLINE, 'entrydeadline'),
    )

    description = models.TextField(
        null=True,
    )

    type = models.TextField(
        max_length=4,
        choices=TYPES,
    )

    target = models.FloatField(
        null=True,
    )

    unlock_date = models.DateTimeField(
        null=True
    )

    due_date = models.DateTimeField()

    lock_date = models.DateTimeField(
        null=True
    )

    forced_template = models.ForeignKey(
        'Template',
        on_delete=models.SET_NULL,
        null=True,
    )
    attached_files = models.ManyToManyField(
        'FileContext',
    )

    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )

    @property
    def is_deadline(self):
        return self.type == Node.ENTRYDEADLINE

    @property
    def is_progress(self):
        return self.type == Node.PROGRESS

    def is_locked(self):
        return self.unlock_date is not None and self.unlock_date > now() or self.lock_date and self.lock_date < now()

    def to_string(self, user=None):
        return "PresetNode"


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

        if template and template.fixed_categories:
            template_category_ids = set(template.categories.values_list('pk', flat=True))
            if category_ids != template_category_ids:
                raise ValidationError('An entry of this type has fixed categories.')

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
        if not EntryCategoryLink.objects.filter(entry=self, category=category).exists():
            EntryCategoryLink.objects.create(entry=self, category=category, author=author)

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

        if not isinstance(self, TeacherEntry):
            try:
                node = Node.objects.get(pk=node_id) if node_id else self.node
            except Node.DoesNotExist:
                raise ValidationError('Saving entry without corresponding node.')

            if (author and not node.journal.authors.filter(user=author).exists() and not self.teacher_entry and
                    not self.jir):
                raise ValidationError('Saving non-teacher entry created by user not part of journal.')

        super(Entry, self).save(*args, **kwargs)

        if is_new and not isinstance(self, TeacherEntry):
            for user in VLE.permissions.get_supervisors_of(self.node.journal):
                Notification.objects.create(
                    type=Notification.NEW_ENTRY,
                    user=user,
                    entry=self,
                )

    def to_string(self, user=None):
        return "Entry"


class TeacherEntry(Entry):
    """TeacherEntry.

    An entry posted by a teacher to multiple student journals.
    """
    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE,
    )
    title = models.TextField(
        null=False,
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


class Grade(CreateUpdateModel):
    """Grade.

    Used to keep a history of grades.
    """
    entry = models.ForeignKey(
        'Entry',
        related_name='grade_set',
        on_delete=models.CASCADE,
    )
    grade = models.FloatField(
        editable=False,
    )
    published = models.BooleanField(
        default=False,
        editable=False
    )
    author = models.ForeignKey(
        'User',
        null=True,
        editable=False,
        on_delete=models.SET_NULL
    )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super(Grade, self).save(*args, **kwargs)
        if self.published:
            for author in self.entry.node.journal.authors.all():
                Notification.objects.create(
                    type=Notification.NEW_GRADE,
                    user=author.user,
                    grade=self
                )
        # Save entry to set this grade as the new entry grade
        if is_new:
            self.entry.save()

    def to_string(self, user=None):
        return "Grade"


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


class TemplateChain(CreateUpdateModel):
    """Identifies multiple templates which were updated as belonging to the same template"""
    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )


class TemplateQuerySet(models.QuerySet):
    def create(self, format, *args, **kwargs):
        """Creates a template and starts a new chain if not provided in the same transaction."""
        with transaction.atomic():
            if not kwargs.get('chain', False):
                kwargs['chain'] = TemplateChain.objects.create(format=format)
            return super().create(*args, **kwargs, format=format)

    def create_template_and_fields_from_data(self, data, format, archived_template=None):
        with transaction.atomic():
            template = Template.objects.create(
                name=data['name'],
                format=format,
                preset_only=data['preset_only'],
                fixed_categories=data['fixed_categories'],
                chain=archived_template.chain if archived_template else False,
            )

            fields = [
                Field(
                    template=template,
                    type=field['type'],
                    title=field['title'],
                    location=field['location'],
                    required=field['required'],
                    description=field['description'],
                    options=field['options'],
                )
                for field in data['field_set']
            ]
            Field.objects.bulk_create(fields)

            if archived_template:
                template.categories.set(archived_template.categories.all())

        return template

    def unused(self):
        return self.filter(
            presetnode__isnull=True,
            entry__isnull=True,
        ).distinct()

    def full_chain(self, templates):
        if isinstance(templates, list) or isinstance(templates, QuerySet) or isinstance(templates, set):
            return self.filter(chain__template__in=templates)
        return self.filter(chain__template=templates)


class Template(CreateUpdateModel):
    """Template.

    A template for an Entry.
    """
    objects = models.Manager.from_queryset(TemplateQuerySet)()

    name = models.TextField()

    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )

    preset_only = models.BooleanField(
        default=False
    )

    archived = models.BooleanField(
        default=False
    )

    fixed_categories = models.BooleanField(
        default=True,
    )

    chain = models.ForeignKey(
        'TemplateChain',
        on_delete=models.CASCADE,
        # TODO: Remove blank and null after manually fixing all archived templates (after deploy?)
        blank=True,
        null=True,
    )

    def can_be_deleted(self):
        return not (
            self.presetnode_set.exists()
            or self.entry_set.exists()
        )

    def to_string(self, user=None):
        return "Template"


@receiver(models.signals.pre_delete, sender=Template)
def delete_pending_jirs_on_source_deletion(sender, instance, **kwargs):
    if Content.objects.filter(field__template=instance).exists():
        raise VLEProgrammingError('Content still exists which depends on a template being deleted.')


@receiver(models.signals.post_delete, sender=Template)
def delete_floating_empty_template_chain(sender, instance, **kwargs):
    """Deletes the template's chain if no templates are left."""
    if not instance.chain.template_set.exists():
        instance.chain.delete()


class Field(CreateUpdateModel):
    """Field.

    Defines the fields of an Template
    """
    class Meta:
        ordering = ['location']

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
        null=True
    )
    options = models.TextField(
        null=True
    )
    location = models.IntegerField()
    template = models.ForeignKey(
        'Template',
        on_delete=models.CASCADE
    )
    required = models.BooleanField()

    def to_string(self, user=None):
        return "{} ({})".format(self.title, self.id)

    def save(self, *args, **kwargs):
        if self.type == Field.FILE and self.options:
            self.options = ', '.join(f.strip().lower() for f in self.options.split(','))
        return super(Field, self).save(*args, **kwargs)


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
        if not isinstance(user, User):
            raise VLEProgrammingError("Expected instance of type User.")

        if user == self.author or user.is_superuser:
            return True

        return user.has_permission('can_edit_staff_comment', self.entry.node.journal.assignment) and \
            not self.entry.node.journal.authors.filter(user=self.author).exists()

    def save(self, *args, **kwargs):
        is_new = not self.pk
        self.text = sanitization.strip_script_tags(self.text)
        super(Comment, self).save(*args, **kwargs)

        if is_new:
            if self.published:
                for user in VLE.permissions.get_supervisors_of(self.entry.node.journal).exclude(pk=self.author.pk):
                    Notification.objects.create(
                        type=Notification.NEW_COMMENT,
                        user=user,
                        comment=self,
                    )
                for author in self.entry.node.journal.authors.all().exclude(user=self.author):
                    Notification.objects.create(
                        type=Notification.NEW_COMMENT,
                        user=author.user,
                        comment=self,
                    )

    def to_string(self, user=None):
        return "Comment"


class JournalImportRequest(CreateUpdateModel):
    """
    Journal Import Request (JIR).
    Stores a single request to import all entries of a journal (source) into another journal (target).

    Attributes:
        source (:model:`VLE.journal`): The journal from which entries will be copied
        target (:model:`VLE.journal`): The journal into which entries will be copied
        author (:model:`VLE.user`): The user who created the journal import request
        state: State of the JIR
        processor (:model:`VLE.user`): The user who updated the JIR state
    """

    PENDING = 'PEN'
    DECLINED = 'DEC'
    APPROVED_INC_GRADES = 'AIG'
    APPROVED_EXC_GRADES = 'AEG'
    APPROVED_WITH_GRADES_ZEROED = 'AWGZ'
    EMPTY_WHEN_PROCESSED = 'EWP'
    APPROVED_STATES = {APPROVED_INC_GRADES, APPROVED_EXC_GRADES, APPROVED_WITH_GRADES_ZEROED}
    STATES = (
        (PENDING, 'Pending'),
        (DECLINED, 'Declined'),
        (APPROVED_INC_GRADES, 'Approved including grades'),
        (APPROVED_EXC_GRADES, 'Approved excluding grades'),
        (APPROVED_WITH_GRADES_ZEROED, 'Approved with all grades set to zero'),
        (EMPTY_WHEN_PROCESSED, 'Empty when processed')
    )

    state = models.CharField(
        max_length=4,
        choices=STATES,
        default=PENDING,
    )
    source = models.ForeignKey(
        'journal',
        related_name='import_request_sources',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    target = models.ForeignKey(
        'journal',
        related_name='import_request_targets',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        'user',
        related_name='jir_author',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    processor = models.ForeignKey(
        'user',
        related_name='jir_processor',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    def get_update_response(self):
        responses = {
            self.DECLINED: 'The journal import request has been successfully declined.',
            self.APPROVED_INC_GRADES:
                'The journal import request has been successfully approved including all previous grades.',
            self.APPROVED_EXC_GRADES:
                'The journal import request has been successfully approved excluding all previous grades.',
            self.APPROVED_WITH_GRADES_ZEROED:
                """The journal import request has been successfully approved,
                and all of the imported entries have been locked (by setting their respective grades to zero).""",
            self.EMPTY_WHEN_PROCESSED:
                'The source journal no longer has entries to import, the request has been archived.',
        }

        return responses[self.state]

    def target_url(self):
        return gen_url(journal=self.target)

    def source_url(self):
        return gen_url(journal=self.source)

    @receiver(models.signals.pre_delete, sender=Journal)
    def delete_pending_jirs_on_source_deletion(sender, instance, **kwargs):
        JournalImportRequest.objects.filter(source=instance, state=JournalImportRequest.PENDING).delete()

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        super().save(*args, **kwargs)

        if is_new:
            if self.target and self.source and self.state == self.PENDING:
                for user in VLE.permissions.get_supervisors_of(
                        self.target, with_permissions=['can_manage_journal_import_requests']):
                    Notification.objects.create(
                        user=user,
                        type=Notification.NEW_JOURNAL_IMPORT_REQUEST,
                        jir=self,
                    )
        if self.state != self.PENDING:
            Notification.objects.filter(jir=self, sent=False).delete()


@receiver(models.signals.pre_save, sender=JournalImportRequest)
def validate_jir_before_save(sender, instance, **kwargs):
    if instance.target:
        if instance.target.assignment.lock_date and instance.target.assignment.lock_date < timezone.now():
            raise ValidationError('You are not allowed to create an import request for a locked assignment.')
        if instance.state == JournalImportRequest.PENDING and not instance.target.assignment.is_published:
            raise ValidationError('You are not allowed to create an import request for an unpublished assignment.')

    if instance.source:
        if not Entry.objects.filter(node__journal=instance.source).exists():
            raise ValidationError('You cannot create an import request from a journal with no entries.')

    if instance.target and instance.source:
        if instance.source.assignment.pk == instance.target.assignment.pk:
            raise ValidationError('You cannot import a journal into itself.')

        existing_import_qry = instance.target.import_request_targets.filter(
            state__in=JournalImportRequest.APPROVED_STATES, source=instance.source)
        if instance.pk:
            existing_import_qry = existing_import_qry.exclude(pk=instance.pk)
        if existing_import_qry.exists():
            raise ValidationError('You cannot import the same journal multiple times.')


class CategoryQuerySet(models.QuerySet):
    def create(self, templates=None, update_template_chain=True, *args, **kwargs):
        """
        Creates a category, setting templates in the same transaction

        If `update_template_chain`, the category will be linked to all templates part of the chain
        """
        with transaction.atomic():
            category = super().create(*args, **kwargs)

            if templates is not None:
                if update_template_chain:
                    category.templates.set(Template.objects.full_chain(templates))
                else:
                    category.templates.set(templates)

            file_handling.establish_rich_text(author=category.author, rich_text=category.description, category=category)

            return category


class Category(CreateUpdateModel):
    """
    Grouping of multiple templates contributing to a specific category / skill
    """
    class Meta:
        ordering = ['name']
        constraints = [
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
            CheckConstraint(check=Q(color__regex=r'^#(?:[0-9a-fA-F]{1,2}){3}$'), name='non_valid_rgb_color_code'),
        ]
        unique_together = (
            ('name', 'assignment'),
            ('color', 'assignment'),
        )

    objects = models.Manager.from_queryset(CategoryQuerySet)()

    name = models.TextField()
    description = models.TextField(
        null=True,
    )
    color = models.CharField(
        max_length=9
    )
    author = models.ForeignKey(
        'User',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    assignment = models.ForeignKey(
        'assignment',
        related_name='categories',
        on_delete=models.CASCADE,
    )
    templates = models.ManyToManyField(
        'Template',
        related_name='categories',
        through='TemplateCategoryLink',
        through_fields=('category', 'template'),
    )

    @staticmethod
    def validate_category_data(name, color, assignment, category=None):
        equal_name = Category.objects.filter(name=name, assignment=assignment)
        equal_color = Category.objects.filter(color=color, assignment=assignment)

        if category:
            equal_name = equal_name.exclude(pk=category.pk)
            equal_color = equal_color.exclude(pk=category.pk)

        if equal_name.exists():
            raise ValidationError('Please provide a unqiue category name.')
        if equal_color.exists():
            raise ValidationError('Please provide a unqiue category color.')


class TemplateCategoryLink(CreateUpdateModel):
    """
    Explicit M2M table, linking Templates to Categories.
    """
    class Meta:
        unique_together = ('template', 'category')  # TODO: Is this required? How are duplicate M2M handled?

    template = models.ForeignKey(
        'template',
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        'category',
        on_delete=models.CASCADE,
    )


class EntryCategoryLink(CreateUpdateModel):
    """Explicit M2M table, linking Entries to Categories."""
    class Meta:
        unique_together = ('entry', 'category')

    entry = models.ForeignKey(
        'entry',
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        'category',
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        'user',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
