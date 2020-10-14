"""
models.py.

Database file
"""
import os
import random
import string

from computedfields.models import ComputedFieldsModel, computed, update_dependent
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField, CIEmailField, CITextField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.deletion import CASCADE, SET_NULL
from django.dispatch import receiver
from django.utils import timezone
from django.utils.timezone import now

import VLE.permissions
import VLE.utils.file_handling as file_handling
from VLE.tasks.email import send_push_notification
from VLE.utils import sanitization
from VLE.utils.error_handling import (VLEBadRequest, VLEParticipationError, VLEPermissionError, VLEProgrammingError,
                                      VLEUnverifiedEmailError)


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
        raise VLEProgrammingError('(gen_url) no object was supplied')

    if journal is None and node is not None:
        journal = node.journal
    if assignment is None and journal is not None:
        assignment = journal.assignment
    if course is None and assignment is not None:
        if user is None:
            raise VLEProgrammingError('(gen_url) if course is not supplied, user needs to be supplied')
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
                raise VLEProgrammingError('FileContext author should be set on creation')

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


class User(AbstractUser):
    """User.

    User is an entity in the database with the following features:
    - full_name: full name of the user
    - email: email of the user.
    - verified_email: Boolean to indicate if the user has validated their email address.
    - password: the hash of the password of the user.
    - lti_id: the DLO id of the user.
    """

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

    def check_can_edit(self, obj):
        if not VLE.permissions.can_edit(self, obj):
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

    OWN_GROUP_TYPES = [NEW_ENTRY, NEW_COMMENT, NEW_JOURNAL_IMPORT_REQUEST]

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
        node_name = None
        if self.node:
            if self.node.type == Node.PROGRESS:
                node_name = f"{self.journal.grade}/{self.node.preset.target}"
            elif self.node.type == Node.ENTRYDEADLINE:
                node_name = self.node.preset.forced_template.name

        return text.format(
            comment=self.comment.author.full_name if self.comment else None,
            entry=self.entry.template.name if self.entry and self.entry.template else None,
            node=node_name,
            journal=self.journal.name if self.journal else None,
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

    def save(self, *args, **kwargs):
        self.description = sanitization.strip_script_tags(self.description)

        active_lti_id_modified = False
        type_changed = False

        # Instance is being created (not modified)
        if self._state.adding:
            active_lti_id_modified = self.active_lti_id is not None
        else:
            if self.pk:
                pre_save = Assignment.objects.get(pk=self.pk)
                active_lti_id_modified = pre_save.active_lti_id != self.active_lti_id

                if pre_save.is_published and not self.is_published and not pre_save.can_unpublish():
                    raise ValidationError(
                        'Cannot unpublish an assignment that has entries or outstanding journal import requests.')
                if pre_save.is_group_assignment != self.is_group_assignment:
                    if pre_save.has_entries():
                        raise ValidationError('Cannot change the type of an assignment that has entries.')
                    else:
                        type_changed = True
            # A copy is being made of the original instance
            else:
                self.active_lti_id = None
                self.lti_id_set = []

        if active_lti_id_modified:
            # Reset all sourcedid if the active lti id is updated.
            AssignmentParticipation.objects.filter(assignment=self).update(sourcedid=None, grade_url=None)
            update_dependent(AssignmentParticipation.objects.filter(assignment=self))

            if self.active_lti_id is not None and self.active_lti_id not in self.lti_id_set:
                self.lti_id_set.append(self.active_lti_id)

            other_assignments_with_lti_id_set = Assignment.objects.filter(
                lti_id_set__contains=[self.active_lti_id]).exclude(pk=self.pk)
            if other_assignments_with_lti_id_set.exists():
                raise ValidationError("An lti_id should be unique, and only part of a single assignment's lti_id_set.")

        is_new = self._state.adding
        if not self._state.adding and self.pk:
            was_published = Assignment.objects.get(pk=self.pk).is_published
        else:
            was_published = self.is_published

        super(Assignment, self).save(*args, **kwargs)

        if type_changed:
            # Delete all journals if assignment type changes
            Journal.objects.filter(assignment=self).delete()

        if type_changed or not was_published and self.is_published:
            # Create journals if it is changed to (or published as) a non group assignment
            if not self.is_group_assignment:
                users = self.courses.values('users').distinct()
                if is_new:
                    existing = []
                    for user in users:
                        AssignmentParticipation.objects.create(assignment=self, user=user['users'])
                else:
                    existing = Journal.objects.filter(assignment=self).values('authors__user')
                for user in users.exclude(pk__in=existing):
                    ap = AssignmentParticipation.objects.get_or_create(
                        assignment=self, user=User.objects.get(pk=user['users']))[0]
                    if not Journal.objects.filter(assignment=self, authors__in=[ap]).exists():
                        journal = Journal.objects.create(assignment=self)
                        journal.add_author(ap)

        # When an assignment is published, create a new assignment notification for each of the assignment's users
        if self.is_published and not was_published:
            for ap in self.assignmentparticipation_set.exclude(user=self.author):
                ap.create_new_assignment_notification()
        # When an assignment is unpublished, remove any respctive new assignment notifications
        elif not self.is_published and was_published:
            self.notification_set.filter(type=Notification.NEW_ASSIGNMENT).delete()

    def get_active_lti_course(self):
        """"Query for retrieving the course which matches the active lti id of the assignment."""
        courses = self.courses.filter(assignment_lti_id_set__contains=[self.active_lti_id])
        return courses.first()

    def get_active_course(self, user):
        """"Query for retrieving the course which is most relevant to the assignment."""
        # If there are no courses connected, return none
        if not self.courses:
            return None

        # Get matching LTI course if possible
        active_courses = self.courses.filter(assignment_lti_id_set__contains=[self.active_lti_id])
        for course in active_courses:
            if user.can_view(course):
                return course

        # Else get course that started the most recent
        most_recent_courses = self.courses.filter(startdate__lte=timezone.now()).order_by('-startdate')
        for course in most_recent_courses:
            if user.can_view(course):
                return course

        # Else get the course that starts the soonest
        starts_first_courses = self.courses.filter(startdate__gt=timezone.now()).order_by('startdate')
        for course in starts_first_courses:
            if user.can_view(course):
                return course

        # Else get the first course without start date
        for course in self.courses.filter(startdate__isnull=True).order_by('pk'):
            if user.can_view(course):
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

    def can_unpublish(self):
        return not (self.has_entries() or self.has_outstanding_jirs())

    def to_string(self, user=None):
        if user is None:
            return "Assignment"
        if not user.can_view(self):
            return "Assignment"

        return "{} ({})".format(self.name, self.pk)


class AssignmentParticipation(CreateUpdateModel):
    """AssignmentParticipation

    A user that is connected to an assignment
    this can then be used as a participation for a journal
    """

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


class JournalManager(models.Manager):
    def get_queryset(self):
        """Filter on only journals with can_have_journal and that are in the assigned to groups"""
        query = super(JournalManager, self).get_queryset()
        return query.annotate(
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


class Journal(CreateUpdateModel, ComputedFieldsModel):
    """Journal.

    A journal is a collection of Nodes that holds the student's
    entries, deadlines and more. It contains the following:
    - assignment: a foreign key linked to an assignment.
    - user: a foreign key linked to a user.
    """
    UNLIMITED = 0
    all_objects = models.Manager()
    objects = JournalManager()

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

    @computed(models.FloatField(null=True), depends=[
        ['node_set', ['entry']],
        ['node_set.entry', ['grade']],
    ])
    def grade(self):
        return round(self.bonus_points + (
            self.node_set.filter(entry__grade__published=True)
            .values('entry__grade__grade')
            .aggregate(Sum('entry__grade__grade'))['entry__grade__grade__sum'] or 0), 2)

    @computed(models.FloatField(null=True), depends=[
        ['node_set', ['entry']],
        ['node_set.entry', ['grade']],
    ])
    def unpublished(self):
        return self.node_set.filter(entry__grade__published=False).count()

    @computed(models.IntegerField(null=True), depends=[
        ['import_request_targets', ['target', 'state']],
    ])
    def import_requests(self):
        return self.import_request_targets.filter(state=JournalImportRequest.PENDING).count()

    @computed(models.FloatField(null=True), depends=[
        ['node_set', ['entry']],
        ['node_set.entry', ['grade']],
    ])
    def needs_marking(self):
        return self.node_set.filter(entry__isnull=False, entry__grade__isnull=True).count()

    @computed(ArrayField(models.TextField(), default=list), depends=[
        ['authors', ['journal', 'sourcedid']],
        ['authors.user', ['full_name']],
        ['assignment', ['active_lti_id']],
    ])
    def needs_lti_link(self):
        if not self.assignment.active_lti_id:
            return list()
        return list(self.authors.filter(sourcedid__isnull=True).values_list('user__full_name', flat=True))

    @computed(models.TextField(null=True), depends=[
        ['self', ['stored_name']],
        ['authors.user', ['full_name']],
    ])
    def name(self):
        if self.stored_name:
            return self.stored_name
        return ', '.join(self.authors.values_list('user__full_name', flat=True))

    @computed(models.TextField(null=True), depends=[
        ['self', ['stored_image']],
        ['authors.user', ['profile_picture']],
    ])
    def image(self):
        if self.stored_image:
            return self.stored_image

        user_with_pic = self.authors.all().exclude(user__profile_picture=settings.DEFAULT_PROFILE_PICTURE).first()
        if user_with_pic is not None:
            return user_with_pic.user.profile_picture

        return settings.DEFAULT_PROFILE_PICTURE

    @computed(models.TextField(null=True), depends=[
        ['authors.user', ['full_name']],
    ])
    def full_names(self):
        return ', '.join(self.authors.values_list('user__full_name', flat=True))

    @computed(models.TextField(null=True), depends=[
        ['authors.user', ['username']],
    ])
    def usernames(self):
        return ', '.join(self.authors.values_list('user__username', flat=True))

    @computed(ArrayField(models.IntegerField(), default=list), depends=[
        ['authors.user.participation_set', ['groups']],
    ])
    def groups(self):
        return list(Group.objects.filter(participation__user__in=self.authors.values('user'))
                    .values_list('pk', flat=True).distinct())

    def add_author(self, author):
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
            raise ValidationError('Journal author limit of a non group assignment exceeds 1')

        is_new = self._state.adding
        if self.stored_name is None:
            if self.assignment.is_group_assignment:
                self.stored_name = 'Journal {}'.format(Journal.objects.filter(assignment=self.assignment).count() + 1)

        super(Journal, self).save(*args, **kwargs)
        # On create add preset nodes
        if is_new:
            preset_nodes = self.assignment.format.presetnode_set.all()
            for preset_node in preset_nodes:
                if not self.node_set.filter(preset=preset_node).exists():
                    Node.objects.create(type=preset_node.type, journal=self, preset=preset_node)

    @property
    def published_nodes(self):
        return self.node_set.filter(entry__grade__published=True).order_by('entry__grade__creation_date')

    @property
    def unpublished_nodes(self):
        return self.node_set.filter(
            Q(entry__grade__isnull=True) | Q(entry__grade__published=False),
            entry__isnull=False).order_by('entry__last_edited')

    def to_string(self, user=None):
        if user is None or not user.can_view(self):
            return 'Journal'

        return self.get_name()


def CASCADE_IF_UNLIMITED_ENTRY_NODE_ELSE_SET_NULL(collector, field, sub_objs, using):
    # NOTE: Either the function is not yet defined or the node type is not defined.
    # Tag Node.FIELD, update hard coded if changed
    unlimited_entry_nodes = [n for n in sub_objs if n.type == 'e']
    other_nodes = [n for n in sub_objs if n.type != 'e']

    CASCADE(collector, field, unlimited_entry_nodes, using)
    SET_NULL(collector, field, other_nodes, using)


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
        related_name='attached_preset_nodes',
    )

    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )

    def is_locked(self):
        return self.unlock_date is not None and self.unlock_date > now() or self.lock_date and self.lock_date < now()

    def to_string(self, user=None):
        return "PresetNode"


class Entry(CreateUpdateModel):
    """Entry.

    An Entry has the following features:
    - last_edited: the date and time when the etry was last edited by an author. This also changes the last_edited_by
    """
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

    def is_locked(self):
        return (self.node.preset and self.node.preset.is_locked()) or self.node.journal.assignment.is_locked()

    def is_editable(self):
        return not self.is_graded() and not self.is_locked()

    def is_graded(self):
        return not (self.grade is None or self.grade.grade is None)

    def save(self, *args, **kwargs):
        is_new = not self.pk
        author_id = self.__dict__.get('author_id', None)
        node_id = self.__dict__.get('node_id', None)
        author = self.author if self.author else User.objects.get(pk=author_id) if author_id else None

        if author and not self.last_edited_by:
            self.last_edited_by = author

        if not isinstance(self, TeacherEntry):
            try:
                node = Node.objects.get(pk=node_id) if node_id else self.node
            except Node.DoesNotExist:
                raise ValidationError('Saving entry without corresponding node')

            if (author and not node.journal.authors.filter(user=author).exists() and not self.teacher_entry and
                    not self.jir):
                raise ValidationError('Saving non-teacher entry created by user not part of journal')

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
        editable=False,
        related_name='+',
        on_delete=models.CASCADE
    )
    grade = models.FloatField(
        null=True,
        editable=False
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
        super(Grade, self).save(*args, **kwargs)

        if self.published:
            for author in self.entry.node.journal.authors.all():
                Notification.objects.create(
                    type=Notification.NEW_GRADE,
                    user=author.user,
                    grade=self
                )

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


class Template(CreateUpdateModel):
    """Template.

    A template for an Entry.
    """

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

    def to_string(self, user=None):
        return "Template"


@receiver(models.signals.pre_delete, sender=Template)
def delete_pending_jirs_on_source_deletion(sender, instance, **kwargs):
    if Content.objects.filter(field__template=instance).exists():
        raise VLEProgrammingError('Content still exists which depends on a template being deleted')


class Field(CreateUpdateModel):
    """Field.

    Defines the fields of an Template
    """
    ALLOWED_URL_SCHEMES = ('http', 'https', 'ftp', 'ftps')
    ALLOWED_DATE_FORMAT = '%Y-%m-%d'
    ALLOWED_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

    TEXT = 't'
    RICH_TEXT = 'rt'
    FILE = 'f'
    VIDEO = 'v'
    URL = 'u'
    DATE = 'd'
    DATETIME = 'dt'
    SELECTION = 's'
    NO_SUBMISSION = 'n'
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
    attached_files = models.ManyToManyField(
        'FileContext',
        related_name='attached_comments',
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
    APPROVED_STATES = [APPROVED_INC_GRADES, APPROVED_EXC_GRADES, APPROVED_WITH_GRADES_ZEROED]
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
