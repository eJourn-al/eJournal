import datetime
import test.factory as factory

from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

import VLE.factory
from VLE.models import Notification, Preferences, User, gen_url
from VLE.permissions import get_supervisors_of
from VLE.tasks.beats.notifications import send_digest_notifications
from VLE.tasks.email import send_push_notification
from VLE.utils.error_handling import VLEParticipationError, VLEProgrammingError


class NotificationTest(TestCase):
    def check_send_push_notification(self, notification):
        outbox_len = len(mail.outbox)

        if getattr(notification.user.preferences, Notification.TYPES[notification.type]['name']) == Preferences.PUSH:
            send_push_notification(notification.pk)
            assert len(mail.outbox) == outbox_len, 'No actual mail should be sent, as it is already pushed'
        else:
            send_push_notification(notification.pk)
            assert len(mail.outbox) == outbox_len + 1, '1 new mail should be sent as the preference was not on push'

        assert notification.content in mail.outbox[-1].body, 'all content should be in mail'
        assert notification.title in mail.outbox[-1].body, 'all content should be in mail'
        assert notification.user.full_name in mail.outbox[-1].body, 'full name should be in mail'

    def test_gen_url(self):
        node = factory.Entry().node
        user = node.journal.authors.first().user

        assert 'nID' in gen_url(node=node, user=user), 'gen_url should give node id when node is supplied'
        assert str(node.pk) in gen_url(node=node, user=user), 'gen_url should give node id when node is supplied'

        assert 'nID' not in gen_url(journal=node.journal, user=user), \
            'gen_url should not give node id when not supplied'
        assert 'Journal' in gen_url(journal=node.journal, user=user), \
            'gen_url should give journal id when not supplied'
        assert str(node.journal.pk) in gen_url(journal=node.journal, user=user), \
            'gen_url should give journal id when not supplied'

        assert 'Journal' not in gen_url(assignment=node.journal.assignment, user=user), \
            'gen_url should not give journal id when not supplied'
        assert 'Assignment' in gen_url(assignment=node.journal.assignment, user=user), \
            'gen_url should give assignment id when not supplied'
        assert str(node.journal.assignment.pk) in gen_url(assignment=node.journal.assignment, user=user), \
            'gen_url should give assignment id when not supplied'

        assert 'Assignment' not in gen_url(course=node.journal.assignment.courses.first(), user=user), \
            'gen_url should not give assignment id when not supplied'
        assert 'Course' in gen_url(course=node.journal.assignment.courses.first(), user=user), \
            'gen_url should give course id when not supplied'
        assert str(node.journal.assignment.courses.first().pk) in gen_url(
            course=node.journal.assignment.courses.first(), user=user), \
            'gen_url should give course id when not supplied'

        self.assertRaises(VLEProgrammingError, gen_url, node=node)
        self.assertRaises(VLEProgrammingError, gen_url, user=factory.Student())
        self.assertRaises(VLEParticipationError, gen_url, node=node, user=factory.Student())

    def test_get_supervisors_of(self):
        unconnected_course = factory.Course()
        connected_course1 = factory.Course()
        connected_course2 = factory.Course()

        assignment = factory.Assignment(courses=[connected_course1, connected_course2])
        journal = factory.Journal(assignment=assignment)
        other_journal = factory.Journal(assignment=assignment)

        supervisors = get_supervisors_of(journal)
        assert unconnected_course.author not in supervisors
        assert connected_course1.author in supervisors
        assert connected_course2.author in supervisors
        assert assignment.author in supervisors
        assert journal.authors.first().user not in supervisors
        assert other_journal.authors.first().user not in supervisors

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_comment_notification(self):
        entry = factory.Entry()

        notifications_before = Notification.objects.filter(type=Notification.NEW_COMMENT).count()
        factory.TeacherComment(published=True, entry=entry)
        journal = entry.node.journal

        assert Notification.objects.filter(type=Notification.NEW_COMMENT).count() == notifications_before + 1, \
            '1 comment notification is created (and 1 entry notification)'
        notification = Notification.objects.last()
        assert notification.user == entry.author
        assert not notification.sent
        assert Notification.objects.last().type == Notification.NEW_COMMENT

        student_comment = factory.StudentComment(entry=entry)
        assert Notification.objects.filter(type=Notification.NEW_COMMENT).count() == notifications_before + 2, \
            '1 new comment notification is created'
        notification = Notification.objects.last()
        assert notification.user == student_comment.entry.node.journal.assignment.courses.first().author
        assert not notification.sent, \
            'Student should not get comment notifications pushed by default'

        self.check_send_push_notification(notification)

        factory.TeacherComment(published=False, entry=entry)
        assert Notification.objects.filter(type=Notification.NEW_COMMENT).count() == notifications_before + 2, \
            'No new notifications should be added'

        journal.authors.add(factory.AssignmentParticipation(assignment=journal.assignment))
        factory.TeacherComment(entry=entry, published=True)
        assert Notification.objects.filter(type=Notification.NEW_COMMENT).count() == notifications_before + 4, \
            '2 new comment notifications should be added for both students'

        factory.Participation(
            course=journal.assignment.courses.first(),
            role=journal.assignment.courses.first().role_set.filter(name='TA').first())
        # factory.AssignmentParticipation(assignment=journal.assignment, user=second_teacher)
        factory.StudentComment(entry=entry)
        assert Notification.objects.filter(type=Notification.NEW_COMMENT).count() == notifications_before + 7, \
            '3 new notifications should be added. One for each teacher, and one for the other student in the journal'

        # TODO: work out how to test with delay

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_grade_notification(self):
        entry = factory.Entry()
        notifications_before = Notification.objects.count()
        VLE.factory.make_grade(entry, entry.node.journal.assignment.author.pk, 10, published=True)
        VLE.factory.make_grade(entry, entry.node.journal.assignment.author.pk, 10, published=False)
        assert Notification.objects.count() == notifications_before + 1, '1 grade notification are created'
        assert Notification.objects.last().user == entry.node.journal.authors.first().user
        assert Notification.objects.last().type == Notification.NEW_GRADE

        self.check_send_push_notification(Notification.objects.last())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_entry_notification(self):
        journal = factory.Journal()
        notifications_before = Notification.objects.count()
        factory.Entry(node__journal=journal)
        assert Notification.objects.count() == notifications_before + 2, \
            '1 new notification is created for entry, and 1 for new deadline'
        assert Notification.objects.last().type == Notification.NEW_ENTRY

        self.check_send_push_notification(Notification.objects.last())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_assignment_notification(self):
        assignment = factory.Assignment(is_published=False)
        course = assignment.courses.first()
        participation = factory.Participation(course=course, role=course.role_set.get(name='Student'))
        notifications_before = Notification.objects.count()
        assignment.is_published = True
        assignment.save()
        assert Notification.objects.count() == notifications_before + 1, 'only for student notification is created'
        assert Notification.objects.last().user == participation.user
        assert Notification.objects.last().type == Notification.NEW_ASSIGNMENT

        self.check_send_push_notification(Notification.objects.last())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_course_notification(self):
        course = factory.Course()

        notifications_before = Notification.objects.count()
        VLE.factory.make_participation(course=course, user=factory.Student(), role=course.role_set.get(name='Student'))
        assert Notification.objects.count() == notifications_before + 1, 'participant should get notified by default'
        assert Notification.objects.last().type == Notification.NEW_COURSE
        notifications_before = Notification.objects.count()
        VLE.factory.make_participation(
            course=course, user=factory.Student(), role=course.role_set.get(name='Student'), notify_user=False)
        assert Notification.objects.count() == notifications_before, \
            'participant should not get notified if specified not to'

        self.check_send_push_notification(Notification.objects.last())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_node_notification(self):
        pass

    def test_digest(self):
        """Test digesting of emails.

        This will send the following notifications:
        for the teacher:
            1 new entry
            2 new comments (batched)
        for the student:
            2 new grades (1 extra because of limitations of the current factoryboy) (batched)
            1 new comment
            1 course membership
            1 assignment membership
        """
        journal = factory.Journal()  # added to course
        student = journal.authors.first().user
        teacher = journal.assignment.author

        # Check if everything is off, that nothing is send
        before_mail_count = len(mail.outbox)
        before_sent_count = Notification.objects.filter(sent=True).count()
        for type, preference in Notification.TYPES.items():
            student.preferences.__dict__[preference['name']] = Preferences.PUSH
            teacher.preferences.__dict__[preference['name']] = Preferences.OFF
        student.preferences.save()
        teacher.preferences.save()

        send_digest_notifications()

        assert before_mail_count == len(mail.outbox)
        assert before_sent_count == Notification.objects.filter(sent=True).count()

        # Check if everything is asked to sent, that also stuff is sending
        pref_type = Preferences.WEEKLY if datetime.datetime.today().weekday() == 0 else Preferences.DAILY
        for type, preference in Notification.TYPES.items():
            student.preferences.__dict__[preference['name']] = pref_type
            if type != Notification.NEW_COURSE:
                teacher.preferences.__dict__[preference['name']] = pref_type
            else:
                teacher.preferences.__dict__[preference['name']] = Preferences.OFF
        student.preferences.save()
        teacher.preferences.save()

        # "2" new grades for student, 1 new entry for teacher, 1 course & assignment membership for student
        entry = factory.Grade(entry__node__journal=journal).entry

        factory.StudentComment(entry=entry, author=student)
        factory.StudentComment(entry=entry, author=student)  # 2 new comments for teacher
        factory.TeacherComment(entry=entry, author=teacher, published=True)  # 1 new comment for student

        # 1 new assignment for student
        assignment = factory.Assignment(courses=journal.assignment.courses.all(), author=teacher, is_published=False)
        assignment.is_published = True
        assignment.save()

        before_count = Notification.objects.exclude(type=Notification.UPCOMING_DEADLINE).count()
        send_digest_notifications()
        assert Notification.objects.exclude(type=Notification.UPCOMING_DEADLINE).count() == before_count, \
            'Only two upcoming deadline notifications should be deleted'

        assert not Notification.objects.filter(user=student, sent=False).exists()
        assert Notification.objects.filter(user=teacher, sent=False).count() == 0, \
            'Teacher should not receive the two comment notifications as that is set on OFF'

        teacher_mail = mail.outbox[-2].body
        assert '2 new comments' in teacher_mail
        assert 'in the journal of {}'.format(student.full_name) in teacher_mail
        assert assignment.name not in teacher_mail

        student_mail = mail.outbox[-1].body
        assert 'You are now a member of' in student_mail
        assert 'New deadline' in student_mail
        # assert 'Upcoming deadline' in student_mail
        assert 'Course notifications' in student_mail
        assert entry.node.journal.assignment.courses.first().name in student_mail
        assert 'is now available' in student_mail

        before_len_mailbox = len(mail.outbox)
        send_digest_notifications()
        assert Notification.objects.exclude(type=Notification.UPCOMING_DEADLINE).count() == before_count, \
            'Only two upcoming deadline notifications should be deleted'

        before_len_mailbox = len(mail.outbox)
        factory.TeacherComment(entry=entry, author=teacher, published=True)  # 1 new comment for student
        User.objects.all().update(verified_email=False)
        send_digest_notifications()
        assert len(mail.outbox) == before_len_mailbox, \
            'No new notifications should be sent with unverified email'
        User.objects.all().update(verified_email=True)
        send_digest_notifications()
        assert len(mail.outbox) != before_len_mailbox, \
            'After verification, notification should be send'

    def test_save_notification(self):
        entry = factory.Entry()
        n = Notification.objects.last()
        assert n.assignment == entry.node.journal.assignment
        assert n.course == entry.node.journal.assignment.courses.first()

        grade = factory.Grade()
        n = Notification.objects.last()
        assert n.assignment == grade.entry.node.journal.assignment
        assert n.course == grade.entry.node.journal.assignment.courses.first()

        course = factory.Participation().course
        n = Notification.objects.filter(type=Notification.NEW_COURSE).last()
        assert n.assignment is None
        assert n.course == course
