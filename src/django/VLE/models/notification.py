from django.conf import settings
from django.db import models

from VLE.tasks.email import send_push_notification
from VLE.utils.generic_utils import gen_url

from .base import CreateUpdateModel
from .journal import Journal
from .preferences import Preferences


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
        'User',
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
                send_push_notification.apply_async(args=[self.pk], countdown=settings.WEBSERVER_TIMEOUT)
