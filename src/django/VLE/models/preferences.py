from django.db import models

from .base import CreateUpdateModel


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
        'User',
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

    hide_past_deadlines_of_assignments = models.ManyToManyField(
        'Assignment',
        related_name='+',
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
