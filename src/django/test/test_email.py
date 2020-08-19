import datetime
import re
import test.factory as factory
from test.utils import api

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from VLE.models import Group, Node, Participation, PresetNode, Template, User
from VLE.tasks.beats import notifications


class EmailAPITest(TestCase):
    def setUp(self):
        self.student = factory.Student()
        self.not_verified = factory.Student(verified_email=False)
        self.is_test_student = factory.TestUser()
        self.valid_pass = 'New_v4lid_pass!'

    @override_settings(EMAIL_BACKEND='anymail.backends.test.EmailBackend', CELERY_TASK_ALWAYS_EAGER=True)
    def test_forgot_password(self):
        # Test if no/invalid params crashes
        api.post(self, 'forgot_password', status=400)
        api.post(self, 'forgot_password', params={'identifier': 'invalid_username'}, status=404)
        api.post(self, 'forgot_password', params={'identifier': 'invalid_email'}, status=404)

        # Test valid parameters
        resp = api.post(self, 'forgot_password', params={'identifier': self.student.username})
        assert 'An email was sent' in resp['description'], \
            'You should be able to get forgot password mail with only a username'
        assert len(mail.outbox) == 1, 'An actual mail should be sent'
        assert mail.outbox[0].to == [self.student.email], 'Email should be sent to the mail adress of the student'
        assert self.student.full_name in mail.outbox[0].body, 'Full name is expected to be used to increase delivery'
        assert '{}/PasswordRecovery/{}/'.format(settings.BASELINK, self.student.username) in \
            mail.outbox[0].alternatives[0][0], 'Recovery token link should be in email'

        token = re.search(r'PasswordRecovery\/(.*)\/([^"]*)', mail.outbox[0].alternatives[0][0]).group(0).split('/')[-1]
        assert PasswordResetTokenGenerator().check_token(self.student, token), 'Token should be valid'

        resp = api.post(self, 'forgot_password', params={'identifier': self.student.email})
        assert 'An email was sent' in resp['description'], \
            'You should be able to get forgot password mail with only an email'
        resp = api.post(self, 'forgot_password', params={'identifier': self.student.email}, user=self.student)
        assert 'An email was sent' in resp['description'], \
            'You should be able to get forgot password mail while logged in'
        resp = api.post(self, 'forgot_password', params={'identifier': self.is_test_student.username}, status=400)
        assert 'no known email address' in resp['description'], \
            'Test student without email address cannot retrieve their password via email.'

    def test_recover_password(self):
        api.post(self, 'recover_password', status=400)
        # Test invalid token
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'recovery_token': 'invalid_token',
                'new_password': self.valid_pass},
            status=400)
        # Test invalid password
        token = PasswordResetTokenGenerator().make_token(self.student)
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'recovery_token': token,
                'new_password': 'new_invalid_pass'},
            status=400)
        # Test invalid username
        api.post(
            self, 'recover_password',
            params={
                'username': factory.Student().username,
                'recovery_token': token,
                'new_password': self.valid_pass},
            status=400)

        # Test everything valid
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'recovery_token': token,
                'new_password': self.valid_pass})

    def test_verify_email(self):
        api.post(self, 'verify_email', status=400)
        token = PasswordResetTokenGenerator().make_token(self.not_verified)
        # Test invalid token
        api.post(self, 'verify_email',
                 params={'username': self.not_verified.username, 'token': 'invalid_token'}, status=400)
        # Test invalid username
        api.post(self, 'verify_email', params={'username': factory.Student().username, 'token': token}, status=400)

        # Test everything valid
        resp = api.post(self, 'verify_email', params={'username': self.not_verified.username, 'token': token})
        assert User.objects.get(pk=self.not_verified.pk).verified_email
        assert 'Success' in resp['description']
        # Test already verified
        token = PasswordResetTokenGenerator().make_token(self.student)
        resp = api.post(self, 'verify_email', params={'username': self.student.username, 'token': token})
        assert 'already verified' in resp['description']

    def test_request_email_verification(self):
        api.post(self, 'request_email_verification', status=401)

        resp = api.post(self, 'request_email_verification', user=self.student)
        assert 'already verified' in resp['description']

        resp = api.post(self, 'request_email_verification', user=self.not_verified)
        assert 'email was sent' in resp['description']

        # A test student without email address set can't request email verification
        api.post(self, 'request_email_verification', user=self.is_test_student, status=400)
        self.is_test_student.email = 'some_valid@email.com'
        self.is_test_student.save()
        resp = api.post(self, 'request_email_verification', user=self.is_test_student, status=200)
        assert 'email was sent' in resp['description']

    def test_send_feedback(self):
        # needs to be logged in
        api.post(self, 'send_feedback', status=401)
        # cannot send without valid email
        api.post(self, 'send_feedback', user=self.not_verified, status=403)
        # Require params
        api.post(self, 'send_feedback', user=self.student, status=400)
        api.post(self, 'send_feedback',
                 params={
                     'topic': 'topic',
                     'feedback': 'feedback',
                     'ftype': 'ftype',
                     'user_agent': 'user_agent',
                     'url': 'url'
                 }, user=self.student)

    def test_deadline_email(self):
        assignment = factory.Assignment()

        preset_entry_deadlines_in_notification_window = 1
        progress_goals_in_notification_window = 1
        deadlines_in_notification_window = \
            preset_entry_deadlines_in_notification_window + progress_goals_in_notification_window

        deadline_inside_notification_window = factory.DeadlinePresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=7, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=8),
            forced_template=assignment.format.template_set.first(),
            format=assignment.format,
        )
        # Progress goal, inside notification window
        factory.ProgressPresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=1, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=2),
            format=assignment.format,
        )

        # Deadline outside notification window
        factory.DeadlinePresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=14, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=15),
            forced_template=assignment.format.template_set.first(),
            format=assignment.format,
        )
        # Progress goal, outside notification window
        factory.ProgressPresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=14, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=15),
            format=assignment.format,
        )

        journal_empty = factory.Journal(assignment=assignment, entries__n=0)

        journal_filled = factory.Journal(assignment=assignment, entries__n=0)
        factory.PresetEntry(node__journal=journal_filled, node__preset=deadline_inside_notification_window)

        journal_filled_and_graded_2 = factory.Journal(assignment=assignment)
        factory.PresetEntry(node__journal=journal_filled_and_graded_2, grade__grade=2)

        journal_filled_and_graded_100 = factory.Journal(assignment=assignment)
        factory.PresetEntry(node__journal=journal_filled_and_graded_100, grade__grade=100)

        journal_empty_but_no_notifications = factory.Journal(
            assignment=assignment, ap__user__preferences__upcoming_deadline_notifications=False)

        mails = notifications.send_upcoming_deadlines()
        assert mails.count(journal_empty.authors.first().user.email) == deadlines_in_notification_window, \
            'Journal without entries should get an deadline email for both the progress and deadline presets'
        assert mails.count(journal_filled.authors.first().user.email) == progress_goals_in_notification_window, \
            '''Journal with preset deadline entry, but without any grade should get only notified of upcoming progress
            goal and not of the preset deadline entry, since it is filled.'''
        assert mails.count(journal_filled_and_graded_2.authors.first().user.email) == deadlines_in_notification_window,\
            'Journal without proper grade should get notified of upcoming preset node'
        assert mails.count(journal_filled_and_graded_100.authors.first().user.email) == 1, \
            'Journal with proper grade should only get notified of unfilled entries'
        assert mails.count(journal_empty_but_no_notifications.authors.first().user.email) == 0, \
            'Without email notifications, one should never get notified'
        assert mails.count(assignment.author.email) == 0, \
            'Teacher should not get any notifications'

        # Test assigned to
        group = Group.objects.create(course=assignment.courses.first(), name='test')
        assignment.assigned_groups.add(group)
        group.participation_set.add(Participation.objects.get(user=journal_empty.authors.first().user))

        mails = notifications.send_upcoming_deadlines()
        assert mails.count(journal_empty.authors.first().user.email) == 2, \
            'Authors in the assigned to groups, should get an email'
        assert (mails.count(journal_filled.authors.first().user.email) == 0 and
                mails.count(journal_filled_and_graded_2.authors.first().user.email) == 0 and
                mails.count(journal_filled_and_graded_100.authors.first().user.email) == 0 and
                mails.count(journal_empty_but_no_notifications.authors.first().user.email) == 0), \
            'Authors not in the assigned to groups, should not get an email'

        assignment = factory.Assignment()
        assignment.is_published = False
        assignment.save()
        # ENTRYDEADLINE inside deadline
        PresetNode.objects.create(
            description='Entrydeadline node description',
            due_date=timezone.now().date() + datetime.timedelta(days=7, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=8),
            type=Node.ENTRYDEADLINE,
            forced_template=Template.objects.filter(format__assignment=assignment).first(),
            format=assignment.format,
        )
        journal_unpublished_assignment = factory.Journal(assignment=assignment)
        mails = notifications.send_upcoming_deadlines()
        assert mails.count(journal_unpublished_assignment.authors.first().user.email) == 0, \
            'Unpublished assignment should get no emails'

    def test_deadline_email_groups(self):
        group_assignment = factory.Assignment(group_assignment=True)
        # ENTRYDEADLINE inside deadline
        PresetNode.objects.create(
            description='Entrydeadline node description',
            due_date=timezone.now().date() + datetime.timedelta(days=7, hours=5),
            lock_date=timezone.now().date() + datetime.timedelta(days=8),
            type=Node.ENTRYDEADLINE,
            forced_template=Template.objects.filter(format__assignment=group_assignment).first(),
            format=group_assignment.format,
        )
        # PROGRESS inside deadline
        PresetNode.objects.create(
            description='Progress node description',
            due_date=timezone.now().date() + datetime.timedelta(days=1, hours=5),
            lock_date=timezone.now().date() + datetime.timedelta(days=2),
            type=Node.PROGRESS,
            target=5,
            format=group_assignment.format,
        )
        group_journal = factory.GroupJournal(assignment=group_assignment)

        in_journal = factory.AssignmentParticipation(assignment=group_assignment)
        group_journal.add_author(in_journal)
        also_in_journal = factory.AssignmentParticipation(assignment=group_assignment)
        group_journal.add_author(also_in_journal)
        not_in_journal = factory.AssignmentParticipation(assignment=group_assignment)

        mails = notifications.send_upcoming_deadlines()
        assert mails.count(in_journal.user.email) == 2, \
            'All students in journal should get a mail'
        assert mails.count(also_in_journal.user.email) == 2, \
            'All students in journal should get a mail'
        assert mails.count(not_in_journal.user.email) == 0, \
            'If not in journal, one should also not get a mail'

        also_in_journal.user.verified_email = False
        also_in_journal.user.save()
        mails = notifications.send_upcoming_deadlines()
        assert mails.count(in_journal.user.email) == 2, \
            'Only student with verified mail should get an email'
        assert mails.count(also_in_journal.user.email) == 0, \
            'Only student with verified mail should get an email'

        also_in_journal.user.verified_email = True
        also_in_journal.user.preferences.upcoming_deadline_notifications = False
        also_in_journal.user.preferences.save()
        mails = notifications.send_upcoming_deadlines()
        assert mails.count(in_journal.user.email) == 2, \
            'Only student with verified mail should get an email'
        assert mails.count(also_in_journal.user.email) == 0, \
            'Only student with verified mail should get an email'
