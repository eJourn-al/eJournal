import os

from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import CIEmailField, CITextField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import OuterRef, Prefetch, Subquery
from django.dispatch import receiver

import VLE.models
import VLE.permissions
import VLE.utils.file_handling as file_handling
from VLE.utils.error_handling import (VLEParticipationError, VLEPermissionError, VLEProgrammingError,
                                      VLEUnverifiedEmailError)

from .comment import Comment
from .course import Course
from .file_context import FileContext
from .journal import Journal
from .participation import Participation
from .preferences import Preferences


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
        role_sub_qry = Participation.objects.filter(
            user=OuterRef('pk'), course=course
        ).select_related('role')
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
        if isinstance(obj, VLE.models.Assignment):
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
        if isinstance(obj, VLE.models.Assignment):
            return VLE.models.Assignment.objects.filter(pk=obj.pk, courses__users=self).exists()
        raise VLEProgrammingError("Participant object must be of type Course or Assignment.")

    def check_can_view(self, obj):
        if not self.can_view(obj):
            raise VLEPermissionError(message='You are not allowed to view {}'.format(obj.to_string(user=self)))

    def can_view(self, obj):
        if self.is_superuser:
            return True

        if isinstance(obj, Course):
            return self.is_participant(obj)

        elif isinstance(obj, VLE.models.Assignment):
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
            if self.is_test_student and self.email:
                raise ValidationError('A test user is not expected to have an email adress.')
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
