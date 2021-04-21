from django.core.exceptions import ValidationError
from django.db import models

from .base import CreateUpdateModel


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
        'Course',
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
