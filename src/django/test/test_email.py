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

from VLE.models import Group, Node, Notification, Participation, Preferences, PresetNode, Template, User
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
        assert '{}/SetPassword/{}/'.format(settings.BASELINK, self.student.username) in \
            mail.outbox[0].alternatives[0][0], 'Recovery token link should be in email'

        token = re.search(r'SetPassword\/(.*)\/([^"]*)', mail.outbox[0].alternatives[0][0]).group(0).split('/')[-1]
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
                'token': 'invalid_token',
                'new_password': self.valid_pass},
            status=400)
        # Test invalid password
        token = PasswordResetTokenGenerator().make_token(self.student)
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'token': token,
                'new_password': 'new_invalid_pass'},
            status=400)
        # Test invalid username
        api.post(
            self, 'recover_password',
            params={
                'username': factory.Student().username,
                'token': token,
                'new_password': self.valid_pass},
            status=400)

        # Test everything valid
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'token': token,
                'new_password': self.valid_pass})

        student.is_active = False
        student.save()

        # Test whether password recovery makes user active (for invitations).
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'token': token,
                'new_password': self.valid_pass})

        assert student.is_active
        assert student.check_password(self.valid_pass)
        assert student.verified_email

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

    @override_settings(EMAIL_BACKEND='anymail.backends.test.EmailBackend', CELERY_TASK_ALWAYS_EAGER=True)
    def test_verify_email_from_create_user(self):
        user_params = {
            'username': 'test',
            'password': 'TestPass!123',
            'email': 'test@ejournal.app',
            'full_name': 'Test User'
        }
        api.post(self, 'users', params=user_params, status=201)

        assert len(mail.outbox) == 1, 'An actual mail should be sent'
        assert mail.outbox[0].to == [user_params['email']], 'Email should be sent to the mail adress of the user'
        assert '{}/EmailVerification/{}/'.format(settings.BASELINK, user_params['username']) in \
            mail.outbox[0].alternatives[0][0], 'Recovery token link should be in email'

        _, username, token = re.search(
            r'EmailVerification\/(.*)\/([^"]*)', mail.outbox[0].alternatives[0][0]).group(0).split('/')
        print(username, token)
        resp = api.post(self, 'verify_email', params={'username': username, 'token': token})
        assert 'Success' in resp['description']

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

    def test_deadline_email_standalone(self):
        assignment = factory.Assignment()

        deadline_inside_notification_window = factory.DeadlinePresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=7, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=8),
            forced_template=assignment.format.template_set.first(),
            format=assignment.format,
        )
        progres_inside_notifcation_window = factory.ProgressPresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=1, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=2),
            format=assignment.format,
            target=5,
        )
        progres_inside_notifcation_window2 = factory.ProgressPresetNode(
            due_date=timezone.now().date() + datetime.timedelta(days=1, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=2),
            format=assignment.format,
            target=6,
        )
        deadlines_inside_notifaction_window = [
            deadline_inside_notification_window,
            progres_inside_notifcation_window,
            progres_inside_notifcation_window2
        ]
        n_deadlines_in_notification_window = len(deadlines_inside_notifaction_window)
        n_deadlines_in_day_window = 2
        n_deadlines_in_week_window = 1

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
            target=5,
        )

        # An empty journal should only receive notifcations within the notication window: (1 < x < 2 || 7 < x < 8 days)
        journal_empty = factory.Journal(assignment=assignment, entries__n=0)
        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)

        # No additional notifactions are generated besides those generated by: generate_upcoming_deadline_notifications
        assert all(gen in after_ns for gen in generated_ns)
        assert all(gen in generated_ns for gen in after_ns)

        # A notification is generated for each of the deadlines in side the window
        assert after_ns.count() == n_deadlines_in_notification_window
        assert after_ns.filter(node__preset=deadline_inside_notification_window).exists()
        assert after_ns.filter(node__preset=progres_inside_notifcation_window).exists()
        assert after_ns.filter(node__preset=progres_inside_notifcation_window2).exists()

        # A notification is generated for each of the deadlines within the day preferences window
        factory.Journal(
            assignment=assignment, entries__n=0, ap__user__preferences__upcoming_deadline_reminder=Preferences.DAY)
        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)
        assert after_ns.count() == n_deadlines_in_day_window
        assert after_ns.filter(node__preset=progres_inside_notifcation_window).exists()
        assert after_ns.filter(node__preset=progres_inside_notifcation_window2).exists()

        # A notification is generated for each of the deadlines within the WEEK preferences window
        factory.Journal(
            assignment=assignment, entries__n=0, ap__user__preferences__upcoming_deadline_reminder=Preferences.WEEK)
        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)
        assert after_ns.count() == n_deadlines_in_week_window
        assert after_ns.filter(node__preset=deadline_inside_notification_window).exists()

        # No notifaction is generated for the entry deadline, as it now has an entry
        journal_filled = factory.Journal(assignment=assignment, entries__n=0)
        factory.PresetEntry(node__journal=journal_filled, node__preset=deadline_inside_notification_window)
        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)
        assert after_ns.count() == 2, 'A Notifcation is generated for both the progress goals but not the entrydeadline'
        assert after_ns.filter(node__preset=progres_inside_notifcation_window).exists()
        assert after_ns.filter(node__preset=progres_inside_notifcation_window2).exists()

        journal_filled_and_graded_5 = factory.Journal(assignment=assignment)
        factory.PresetEntry(
            node__journal=journal_filled_and_graded_5, grade__grade=5, node__preset=deadline_inside_notification_window)
        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)
        assert after_ns.count() == 1, 'A Notifcation is generated for the remaining unmatched progress goal'
        assert after_ns.filter(node__preset=progres_inside_notifcation_window2).exists()

        journal_filled_and_graded_100 = factory.Journal(assignment=assignment)
        factory.PresetEntry(node__journal=journal_filled_and_graded_100, grade__grade=100,
                            node__preset=deadline_inside_notification_window)
        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)
        assert after_ns.count() == 0, 'Both the deadline and both progress nodes are filled'

        # Test assigned to
        group = Group.objects.create(course=assignment.courses.first(), name='test')
        assignment.assigned_groups.add(group)
        group.participation_set.add(Participation.objects.get(user=journal_empty.authors.first().user))

        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        generated_ns = notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)

        assert after_ns.filter(user=journal_empty.authors.first().user).count() == after_ns.count(), \
            'The only notifications are those for the student assigned to the group'

    def test_unpublished_assignment_generates_no_notifications(self):
        journal_unpublished_assignment = factory.Journal(assignment__is_published=False)
        # ENTRYDEADLINE inside weekly (default) notification window
        PresetNode.objects.create(
            description='Entrydeadline node description',
            due_date=timezone.now().date() + datetime.timedelta(days=7, hours=2),
            lock_date=timezone.now().date() + datetime.timedelta(days=8),
            type=Node.ENTRYDEADLINE,
            format=journal_unpublished_assignment.assignment.format,
        )

        before_ns = list(Notification.objects.all().values_list('pk', flat=True))
        notifications.generate_upcoming_deadline_notifications()
        after_ns = Notification.objects.all().exclude(pk__in=before_ns)

        after_ns.count() == 0, 'An unpublished assignment should yield no notifications'

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

        mails = [n.user.email for n in notifications.generate_upcoming_deadline_notifications()]
        assert len(notifications.generate_upcoming_deadline_notifications()) == 0, \
            'Generating the upcoming deadling notifications twice should give no new notifications'
        assert mails.count(in_journal.user.email) == 2, \
            'All students in journal should get a mail'
        assert mails.count(also_in_journal.user.email) == 2, \
            'All students in journal should get a mail'
        assert mails.count(not_in_journal.user.email) == 0, \
            'If not in journal, one should also not get a mail'

    def test_deadline_email_text(self):
        assignment = factory.Assignment()
        # ENTRYDEADLINE inside deadline
        entry = PresetNode.objects.create(
            description='Entrydeadline node description',
            due_date=timezone.now().date() + datetime.timedelta(days=7, hours=5),
            lock_date=timezone.now().date() + datetime.timedelta(days=8),
            type=Node.ENTRYDEADLINE,
            forced_template=Template.objects.filter(format__assignment=assignment).first(),
            format=assignment.format,
        )
        # PROGRESS inside deadline
        preset = PresetNode.objects.create(
            description='Progress node description',
            due_date=timezone.now().date() + datetime.timedelta(days=1, hours=5),
            lock_date=timezone.now().date() + datetime.timedelta(days=2),
            type=Node.PROGRESS,
            target=5,
            format=assignment.format,
        )
        journal = factory.Journal(assignment=assignment)
        notifications.generate_upcoming_deadline_notifications()

        assert f'{journal.grade}/' in Notification.objects.get(node__preset=preset).content
        assert entry.forced_template.name not in Notification.objects.get(node__preset=preset).content

        assert entry.forced_template.name in Notification.objects.get(node__preset=entry).content
        assert f'{journal.grade}/' not in Notification.objects.get(node__preset=entry).content
