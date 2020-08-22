import test.factory as factory
from test.utils import api

from computedfields.models import update_dependent
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

import VLE.factory
from VLE.models import (Assignment, AssignmentParticipation, Course, Journal, JournalImportRequest, Participation, Role,
                        User)
from VLE.utils.error_handling import VLEBadRequest


class JournalAPITest(TestCase):
    def setUp(self):
        self.journal = factory.Journal()
        self.student = self.journal.authors.first().user
        self.assignment = self.journal.assignment
        self.course = self.assignment.courses.first()
        self.teacher = self.course.author

        self.group_assignment = factory.Assignment(group_assignment=True)
        self.group_journal = factory.GroupJournal(assignment=self.group_assignment)
        self.group_journal2 = factory.GroupJournal(assignment=self.group_assignment)
        self.ap = factory.AssignmentParticipation(assignment=self.group_assignment)
        self.g_student = self.ap.user
        self.g_teacher = self.group_assignment.courses.first().author

    def test_journal_factory(self):
        c_count = Course.objects.count()
        a_count = Assignment.objects.count()
        j_count = Journal.all_objects.count()
        ap_count = AssignmentParticipation.objects.count()
        u_count = User.objects.count()

        # Generate a journal whose assignment is not attached to any courses
        journal = factory.Journal(assignment__courses=[])

        assert Course.objects.count() == c_count,\
            'Generating a journal whose assignment hold no courses, does indeed generate no courses'
        assert Assignment.objects.filter(journal=journal).exists() and Assignment.objects.count() == a_count + 1, \
            'A single assignment is generated when generating a journal'
        # QUESTION: Lars is het logisch dat hier all_objects nodig is?
        assert Journal.all_objects.count() == j_count + 1, 'A single journal is generated'
        assert AssignmentParticipation.objects.count() == ap_count + 1, 'Generating a journal generates a single AP'
        assert u_count + 2 == User.objects.count(), \
            'A single user is created when generating a user (plus assignment author)'

        c_count = Course.objects.count()
        a_count = Assignment.objects.count()
        j_count = Journal.objects.count()
        ap_count = AssignmentParticipation.objects.count()
        u_count = User.objects.count()

        # Generate a fully connected journal (course and assignment)
        journal = factory.Journal()

        assert Course.objects.filter(assignment=journal.assignment).exists() and Course.objects.count() == c_count + 1,\
            'A single course is generated when generating a journal'
        assert Assignment.objects.filter(journal=journal).exists() and Assignment.objects.count() == a_count + 1, \
            'A single assignment is generated when generating a journal'
        assert Journal.objects.count() == j_count + 1, 'A single journal is generated'
        assert AssignmentParticipation.objects.count() == ap_count + 2, \
            'Generating a journal generates an AP for both the journal user and the course author'
        assert u_count + 2 == User.objects.count(), \
            'When generating an assignment, a journal AP user is created, and a course author'

        assignment = factory.Assignment()
        journal = factory.Journal(assignment=assignment)

        assert c_count + 1 and a_count + 1, \
            'Generating an additional journal with a specific assignment, yields no additional courses or assignments'

        # Creating a journal creates an accompanying assignment participation and user
        AssignmentParticipation.objects.get(journal=journal, assignment=journal.assignment)

        user = factory.Student()
        journal = factory.Journal(ap__user=user, assignment=assignment)

        # It is possible to specify which user via deep paramater syntax
        AssignmentParticipation.objects.get(journal=journal, assignment=journal.assignment, user=user)
        # Generating a journal also generates a single corresponding AP
        AssignmentParticipation.objects.get(journal=journal)

        lti_journal = factory.LtiJournal(ap__user=user)
        # LtiJournal also creates a single user
        ap = AssignmentParticipation.objects.get(journal=lti_journal, assignment=lti_journal.assignment, user=user)
        assert ap.grade_url and ap.sourcedid, 'Lti journal requires a non empty grade_url and sourcedid'

    def test_journal_authors_course_participation(self):
        assignment = factory.Assignment()
        course = assignment.courses.first()
        student_role = Role.objects.get(name='Student', course=course)

        journal = factory.Journal(assignment=assignment)

        assert Participation.objects.filter(
            user=journal.authors.first().user, course=course, role=student_role).exists(), \
            'Journal authors are course members'

        g_assignment = factory.Assignment(group_assignment=True)
        course = g_assignment.courses.first()
        student_role = Role.objects.get(name='Student', course=course)
        journal = factory.GroupJournal(assignment=g_assignment, add_users=[factory.Student(), factory.Student()])

        for author in journal.authors.all():
            assert Participation.objects.filter(
                user=author.user, course=course, role=student_role).exists(), 'Journal authors are course members'

    def test_group_journal_factory(self):
        course = factory.Course()
        users = [factory.Student(), factory.Student()]
        user_count = User.objects.count()
        ap_count = AssignmentParticipation.objects.count()

        # Group journal, like journal, defaults to one user, here we add two more.
        group_journal = factory.GroupJournal(add_users=users, author_limit=3, assignment__courses=[course])

        assert user_count + 1 == User.objects.count(), 'One user is created by a group journal by default'
        assert ap_count + 4 == AssignmentParticipation.objects.count(), \
            '''Creating a group journal with 3 users, also creates three assignment participations (plus one for the
            teacher)'''
        assert AssignmentParticipation.objects.filter(
            journal=group_journal, user__in=group_journal.authors.all().values('user')).count() == 3, \
            'All students APs are attached to the journal'

        users.append(factory.Student())
        self.assertRaises(ValidationError, factory.GroupJournal, add_users=users, author_limit=3)

    def test_computed_name(self):
        # A short name which will not be truncated with two users in a journal
        short_name = 'Short name'
        # NOTE, comments or assert messages why the behaviour is expected missing
        journal = factory.Journal()
        assert journal.name == journal.authors.first().user.full_name

        # Test author name
        user = journal.authors.first().user
        user.full_name = short_name
        user.save()
        journal.refresh_from_db()
        assert journal.name == short_name
        assert journal.full_names == short_name
        assert journal.usernames == user.username

        # Test stored name
        journal.stored_name = 'stored name'
        journal.save()
        journal.refresh_from_db()
        assert journal.name == 'stored name'
        assert journal.full_names == short_name

        # Test add author
        group_journal = factory.GroupJournal(ap__user__full_name='Short name', add_users=[factory.Student()])
        ap = group_journal.authors.first()
        assert ', ' in group_journal.full_names
        assert ap.user.full_name in group_journal.full_names
        assert user.full_name in group_journal.full_names
        assert ap.user.username in group_journal.usernames
        assert ', ' in group_journal.usernames
        assert group_journal.name == 'Journal {}'.format(Journal.objects.filter(assignment=self.assignment).count()), \
            'Group journal name should default to assignments journal count'

        # Test updates also on .update
        User.objects.filter(pk=ap.user.pk).update(full_name='update name')
        update_dependent(User.objects.filter(pk=ap.user.pk))
        group_journal.refresh_from_db()
        assert 'update name' in group_journal.full_names, \
            'Updated users name is reflected in cached journals full names'
        assert group_journal.name

        # Test remove author
        group_journal.remove_author(ap)
        assert ap.user.full_name not in group_journal.name
        assert ap.user.full_name not in group_journal.full_names
        assert group_journal.full_names == group_journal.authors.first().user.full_name
        assert group_journal.name == 'Journal {}'.format(Journal.objects.filter(assignment=self.assignment).count()), \
            'Group journal name should still default to assignments journal count'

    def test_computed_import_requests(self):
        journal = factory.Journal(entries__n=0)
        source = factory.Journal()
        assert journal.import_requests == 0, 'A journal has no JIRs by default'

        jir = factory.JournalImportRequest(
            target=journal, state=JournalImportRequest.APPROVED_EXC_GRADES, source=source)
        assert journal.import_requests == 0, 'Only pending JIRs should count towards import request total'

        jir = factory.JournalImportRequest(target=journal, source=source, state=JournalImportRequest.PENDING)
        jir2 = factory.JournalImportRequest(target=journal, source=source, state=JournalImportRequest.PENDING)
        journal.refresh_from_db()
        assert journal.import_request_targets.count() == 3, 'Journal should have three JIRs with journal as target'
        assert journal.import_requests == 2, 'Import requests should update on the creation of a JIR'

        jir.delete()
        journal.refresh_from_db()
        assert journal.import_requests == 1, 'Import requests should update on the deletion of a JIR'

        jir2.state = JournalImportRequest.DECLINED
        jir2.save()
        journal.refresh_from_db()
        assert journal.import_requests == 0, 'Import requests should update on the state change of a JIR'

    def test_computed_grade(self):
        journal = factory.Journal(entries__n=0)
        assert journal.grade == 0
        assert journal.unpublished == 0
        assert journal.needs_marking == 0

        factory.Grade(grade=5, published=False, entry__node__journal=journal)
        journal.refresh_from_db()
        assert journal.grade == 0
        assert journal.unpublished == 1
        assert journal.needs_marking == 0

        grade = factory.Grade(grade=5, published=True, entry__node__journal=journal)
        journal.refresh_from_db()
        assert journal.grade == 5
        assert journal.unpublished == 1
        assert journal.needs_marking == 0

        factory.Grade(entry=grade.entry, grade=3, published=True)
        journal.refresh_from_db()
        assert journal.grade == 3
        assert journal.unpublished == 1
        assert journal.needs_marking == 0

        entry = factory.UnlimitedEntry(grade=None, node__journal=journal)
        journal.refresh_from_db()
        assert journal.grade == 3
        assert journal.unpublished == 1
        assert journal.needs_marking == 1

        factory.Grade(entry=entry, published=False, grade=10)
        journal.refresh_from_db()
        assert journal.grade == 3
        assert journal.unpublished == 2
        assert journal.needs_marking == 0

    def test_get_journal(self):
        payload = {'assignment_id': self.assignment.pk, 'course_id': self.course.pk}
        # Test list
        api.get(self, 'journals', params=payload, user=self.student, status=403)
        api.get(self, 'journals', params=payload, user=self.teacher)

        # Test get
        journal_resp = api.get(self, 'journals', params={'pk': self.journal.pk}, user=self.student)['journal']
        assert not journal_resp['usernames'], 'students should not get other usernames'
        assert not journal_resp['needs_lti_link'], 'student should not need an LTI link if it is not an LTI assignment'
        journal_resp = api.get(self, 'journals', params={'pk': self.journal.pk}, user=self.teacher)['journal']
        assert journal_resp['usernames'], 'teacher should get a list of usernames'
        assert not journal_resp['needs_lti_link'], 'student should not need an LTI link if it is not an LTI assignment'
        api.get(self, 'journals', params={'pk': self.journal.pk}, user=factory.Teacher(), status=403)

        lti_journal = factory.Journal(assignment=factory.LtiAssignment())
        lti_ap = lti_journal.authors.first()

        journal_resp = api.get(self, 'journals', params={'pk': lti_journal.pk}, user=lti_ap.user)['journal']
        assert lti_journal.authors.first().user.full_name in journal_resp['needs_lti_link'], \
            'student need an LTI link if it is an LTI assignment'

        lti_ap.sourcedid = 'filled'
        lti_ap.save()
        journal_resp = api.get(self, 'journals', params={'pk': lti_journal.pk}, user=lti_ap.user)['journal']
        assert lti_journal.authors.first().user.full_name not in journal_resp['needs_lti_link'], \
            'student should not need an LTI link if student has a sources id'

    def test_journal_get_image(self):
        assert self.journal.image == settings.DEFAULT_PROFILE_PICTURE
        self.student.profile_picture = 'new_image'
        self.student.save()
        self.journal.refresh_from_db()
        assert self.journal.image == 'new_image'

        second_ap = factory.AssignmentParticipation(assignment=self.group_assignment)
        self.group_journal.add_author(second_ap)
        assert self.group_journal.image == settings.DEFAULT_PROFILE_PICTURE
        second_ap.user.profile_picture = 'new_image'
        second_ap.user.save()
        self.group_journal.refresh_from_db()
        assert self.group_journal.image == 'new_image'

    def test_create_journal(self):
        payload = {
            'pk': self.group_journal.pk,
            'assignment_id': self.group_assignment.pk,
            'author_limit': 3,
            'amount': 2
        }
        before_count = Journal.all_objects.filter(assignment=self.group_assignment).count()

        # Check invalid users
        api.create(self, 'journals', params=payload, user=self.g_student, status=403)
        api.create(self, 'journals', params=payload, user=self.teacher, status=403)

        # Check valid creation of 2 journals
        api.create(self, 'journals', params=payload, user=self.g_teacher)

        # Check invalid amount
        payload['amount'] = 0
        api.create(self, 'journals', params=payload, user=self.g_teacher, status=400)

        after_count = Journal.all_objects.filter(assignment=self.group_assignment).count()

        assert before_count + 2 == after_count, '2 new journals should be added'
        assert Journal.objects.filter(assignment=self.group_assignment).last().author_limit == 3, \
            'Journal should have the proper max amount of users'
        assert Journal.objects.filter(assignment=self.group_assignment).first().name == 'Journal 1', \
            'Group journals should get a default name if it is not specified'

    def test_journal_name(self):
        non_group_journal = factory.Journal()
        assert non_group_journal.name == non_group_journal.authors.first().user.full_name, \
            'Non group journals should get name of author'
        non_group_journal.authors.first().user.full_name = non_group_journal.authors.first().user.full_name + 'NEW'
        non_group_journal.authors.first().user.save()
        assert non_group_journal.name == non_group_journal.authors.first().user.full_name, \
            'Non group journals name should get updated when author name changes'

    def test_make_journal(self):
        self.assertRaises(VLEBadRequest, VLE.factory.make_journal, self.group_assignment, author=self.student)
        self.assertRaises(VLEBadRequest, VLE.factory.make_journal, self.assignment, author_limit=4)
        other_student = factory.Student()
        VLE.factory.make_journal(self.assignment, author=other_student)
        assert Journal.all_objects.filter(assignment=self.assignment, authors__user=other_student).exists(), \
            'make_journal should create a journal and AP if they do not exist yet'
        VLE.factory.make_journal(self.assignment, author=other_student)
        assert Journal.all_objects.filter(assignment=self.assignment, authors__user=other_student).count() == 1, \
            'make_journal should not create a journal and AP if they already exist'

    def test_list_journal(self):
        assignment = factory.Assignment()
        course1 = assignment.courses.first()
        factory.Journal(assignment=assignment)
        course2 = factory.Course()
        assignment.courses.add(course2)
        factory.Journal(assignment=assignment)

        result = api.get(
            self, 'journals', params={'assignment_id': assignment.pk, 'course_id': course2.pk}, user=course2.author)
        assert len(result['journals']) == 1, 'Course2 is supplied, only journals from that course should appear (1)'

        result = api.get(
            self, 'journals', params={'assignment_id': assignment.pk}, user=self.teacher, status=400)

        result = api.get(
            self, 'journals', params={'assignment_id': assignment.pk, 'course_id': course1.pk}, user=course1.author)
        assert len(result['journals']) == 2, 'Course1 is supplied, only journals from that course should appear (2)'

        # Should not work when user is not in supplied course
        result = api.get(
            self, 'journals', params={'assignment_id': assignment.pk, 'course_id': course1.pk}, user=course2.author,
            status=403)

    def test_update_journal(self):
        # Check if students need to specify a name to update journals
        api.update(self, 'journals', params={'pk': self.journal.pk}, user=self.student, status=400)
        # Check teacher can always update name
        api.update(self, 'journals', params={'pk': self.journal.pk, 'name': 'new name'}, user=self.teacher)
        assert Journal.objects.get(pk=self.journal.pk).name == 'new name'

        # Check student can only update name if assignment allows
        api.update(self, 'journals', params={'pk': self.journal.pk, 'name': 'new name'}, user=self.student, status=403)
        self.assignment.can_set_journal_name = True
        self.assignment.save()
        api.update(self, 'journals', params={'pk': self.journal.pk, 'name': 'student name'}, user=self.student)
        assert Journal.objects.get(pk=self.journal.pk).name == 'student name'

        # Check teacher can update author_limit only for group assignment
        api.update(self, 'journals', params={'pk': self.journal.pk, 'author_limit': 4}, user=self.teacher, status=400)
        api.update(self, 'journals', params={'pk': self.group_journal.pk, 'author_limit': 4}, user=self.g_teacher)
        self.group_journal.refresh_from_db()
        assert self.group_journal.author_limit == 4, 'Author limit is succsefully update'

        assert self.group_journal.authors.count() == 1
        # Check teacher cannot update author_limit when there are more student in journal
        self.group_journal.add_author(factory.AssignmentParticipation(assignment=self.group_assignment))
        self.group_journal.add_author(factory.AssignmentParticipation(assignment=self.group_assignment))
        api.update(
            self, 'journals',
            params={'pk': self.group_journal.pk, 'author_limit': self.group_journal.authors.count() - 1},
            user=self.g_teacher, status=400
        )

        # Check teacher can update name and author_limit
        api.update(
            self, 'journals', params={'pk': self.group_journal.pk, 'author_limit': 9, 'name': 'NEW'},
            user=self.g_teacher)
        self.group_journal.refresh_from_db()
        assert self.group_journal.author_limit == 9 and self.group_journal.name == 'NEW'

        for i in range(self.group_journal.author_limit - self.group_journal.authors.count()):
            self.group_journal.add_author(factory.AssignmentParticipation(assignment=self.group_assignment))

        api.update(
            self, 'journals', params={'pk': self.group_journal.pk, 'author_limit': Journal.UNLIMITED},
            user=self.g_teacher)
        self.group_journal.refresh_from_db()
        assert self.group_journal.author_limit == Journal.UNLIMITED

        api.update(
            self, 'journals', params={'pk': self.group_journal.pk, 'author_limit': 3},
            user=self.g_teacher, status=400)
        self.group_journal.refresh_from_db()
        assert self.group_journal.author_limit == Journal.UNLIMITED
        api.update(
            self, 'journals', params={'pk': self.journal.pk, 'author_limit': 3}, user=self.teacher, status=400)
        api.update(
            self, 'journals', params={'pk': self.journal.pk, 'name': 'CHANGED'}, user=self.teacher)
        journal = Journal.objects.get(pk=self.journal.pk)
        assert journal.author_limit == 1 and journal.name == 'CHANGED'

        # Check if teacher can only update the published state
        api.update(self, 'journals', params={'pk': self.journal.pk}, user=self.teacher, status=400)
        api.update(self, 'journals', params={'pk': self.journal.pk, 'published': True}, user=self.teacher)

        # Check if the admin can update the journal
        api.update(self, 'journals', params={'pk': self.journal.pk, 'user': factory.Student().pk}, user=factory.Admin())

    def test_delete_journal(self):
        # Check student may not delete journals
        api.delete(self, 'journals', params={'pk': self.journal.pk}, user=self.student, status=403)
        # Check can only delete group journals
        api.delete(self, 'journals', params={'pk': self.journal.pk}, user=self.teacher, status=400)
        # Check cannot delete with authors
        api.delete(self, 'journals', params={'pk': self.group_journal.pk}, user=self.g_teacher, status=400)
        # Check valid deletion
        self.group_journal.remove_author(self.group_journal.authors.first())
        api.delete(self, 'journals', params={'pk': self.group_journal.pk}, user=self.g_teacher)

    def test_join_journal(self):
        assert not self.group_journal.authors.filter(user=self.g_student).exists(), \
            'Check if student is not yet in the journal'
        api.update(self, 'journals/join', params={'pk': self.group_journal.pk}, user=self.g_student)
        assert self.group_journal.authors.filter(user=self.g_student).exists(), \
            'Check if student is added to the journal'
        # Check already joined
        api.update(self, 'journals/join', params={'pk': self.group_journal.pk}, user=self.g_student, status=400)
        # Check not in assignment
        api.update(self, 'journals/join', params={'pk': self.group_journal.pk}, user=factory.Student(), status=403)
        # Check teacher is not able to join
        api.update(self, 'journals/join', params={'pk': self.group_journal.pk}, user=self.g_teacher, status=403)
        # Check only 1 journal at the time
        api.update(self, 'journals/join', params={'pk': self.group_journal2.pk}, user=self.g_student, status=400)
        # Check max student
        for _ in range(self.group_journal2.author_limit - self.group_journal2.authors.count()):
            api.update(
                self, 'journals/join', params={'pk': self.group_journal2.pk},
                user=factory.AssignmentParticipation(assignment=self.group_assignment).user)
        api.update(
            self, 'journals/join', params={'pk': self.group_journal2.pk},
            user=factory.AssignmentParticipation(assignment=self.group_assignment).user, status=400)

        # Check max set to 0 enables infinite amount
        self.group_journal2.author_limit = Journal.UNLIMITED
        self.group_journal2.save()
        for _ in range(3):
            api.update(
                self, 'journals/join', params={'pk': self.group_journal2.pk},
                user=factory.AssignmentParticipation(assignment=self.group_assignment).user)

        # Check can only leave if author_limit is too low
        self.group_journal2.author_limit = self.group_journal2.authors.count()
        self.group_journal2.save()
        api.update(
            self, 'journals/join', params={'pk': self.group_journal2.pk},
            user=factory.AssignmentParticipation(assignment=self.group_assignment).user, status=400)
        api.update(
            self, 'journals/leave', params={'pk': self.group_journal2.pk},
            user=self.group_journal2.authors.first().user)

        # Check locked journal
        self.group_journal.locked = True
        self.group_journal.save()
        api.update(self, 'journals/join', params={'pk': self.group_journal.pk}, user=self.g_student, status=400)

    def test_get_members(self):
        # Test students that are not added to the journal are NOT allowed to view other members
        api.get(
            self, 'journals/get_members', params={'pk': self.group_journal.pk},
            user=self.g_student, status=403)
        api.get(
            self, 'journals/get_members', params={'pk': self.group_journal.pk},
            user=factory.Teacher(), status=403)

        # Test before adding student, that student is not returned
        members = api.get(
            self, 'journals/get_members', params={'pk': self.group_journal.pk},
            user=self.g_teacher)['authors']
        assert self.g_student.pk not in [m['id'] for m in members]
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal.pk, 'user_ids': [self.g_student.pk]},
            user=self.g_teacher)

        # Test after adding student, that student is returned
        members = api.get(
            self, 'journals/get_members', params={'pk': self.group_journal.pk},
            user=self.g_teacher)['authors']
        assert self.g_student.pk not in [m['id'] for m in members]

        # Test students that are added to the journal ARE allowed to view other members
        api.get(
            self, 'journals/get_members', params={'pk': self.group_journal.pk},
            user=self.g_student)

    def test_add_members(self):
        assert not Journal.objects.get(pk=self.group_journal.pk).authors.filter(user=self.g_student).exists(), \
            'Check if user is not yet in the journal'
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal.pk, 'user_ids': [self.g_student.pk]},
            user=self.g_teacher)
        assert Journal.objects.get(pk=self.group_journal.pk).authors.filter(user=self.g_student).exists(), \
            'Check if user is added to the journal'
        # Check already joined
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal.pk, 'user_ids': [self.g_student.pk]},
            user=self.g_teacher, status=400)
        # Check not in assignment
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal.pk, 'user_ids': [factory.Student().pk]},
            user=self.g_teacher, status=403)
        # Check teacher is not able to join
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal.pk, 'user_ids': [self.g_teacher.pk]},
            user=self.g_teacher, status=403)
        # Check only 1 journal at the time
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal2.pk, 'user_ids': [self.g_student.pk]},
            user=self.g_teacher, status=400)
        # Check max members
        for _ in range(self.group_journal2.author_limit - self.group_journal2.authors.count()):
            student = factory.AssignmentParticipation(assignment=self.group_assignment).user
            api.update(
                self, 'journals/add_members', params={'pk': self.group_journal2.pk, 'user_ids': [student.pk]},
                user=self.g_teacher)
        student = factory.AssignmentParticipation(assignment=self.group_assignment).user
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal2.pk, 'user_ids': [student.pk]},
            user=self.g_teacher, status=400)

        # Check if teacher can still add when it is a locked journal
        self.group_journal.locked = True
        self.group_journal.save()
        api.update(
            self, 'journals/add_members', params={'pk': self.group_journal.pk, 'user_ids': [student.pk]},
            user=self.g_teacher)

    def test_leave(self):
        self.group_journal.add_author(self.ap)
        self.group_journal.save()

        assert self.group_journal.authors.filter(user=self.g_student).exists(), \
            'Check if student is added to the journal'
        api.update(self, 'journals/leave', params={'pk': self.group_journal.pk}, user=self.g_student)
        assert not self.group_journal.authors.filter(user=self.g_student).exists(), \
            'Check if student is not yet in the journal'

        # Check not in journal
        api.update(self, 'journals/leave', params={'pk': self.group_journal.pk}, user=self.g_student, status=400)
        # check not possible to leave non group assignment
        api.update(self, 'journals/leave', params={'pk': self.journal.pk}, user=self.student, status=400)
        # Check leave locked journal
        self.group_journal.add_author(self.ap)
        self.group_journal.locked = True
        self.group_journal.save()
        api.update(self, 'journals/leave', params={'pk': self.group_journal.pk}, user=self.g_student, status=400)

    def test_kick(self):
        self.group_journal.add_author(self.ap)
        self.group_journal.save()

        assert self.group_journal.authors.filter(user=self.g_student).exists(), \
            'Check if student is added to the journal'
        api.update(self, 'journals/kick', params={'pk': self.group_journal.pk, 'user_id': self.g_student.pk},
                   user=self.g_teacher)
        assert not self.group_journal.authors.filter(user=self.g_student).exists(), \
            'Check if student is not yet in the journal'

        # Check not in journal
        api.update(self, 'journals/kick', params={'pk': self.group_journal.pk, 'user_id': self.g_student.pk},
                   user=self.g_teacher, status=400)
        self.group_journal.add_author(self.ap)
        self.group_journal.locked = True
        self.group_journal.save()
        # check not possible to kick from non group assignment
        api.update(self, 'journals/kick', params={'pk': self.journal.pk, 'user_id': self.student.pk},
                   user=self.teacher, status=400)
        # Check student cannot kick others
        api.update(self, 'journals/kick', params={'pk': self.group_journal.pk, 'user_id': self.g_student.pk},
                   user=factory.AssignmentParticipation(assignment=self.group_assignment).user, status=403)
        # Check kick locked journal
        api.update(self, 'journals/kick', params={'pk': self.group_journal.pk, 'user_id': self.g_student.pk},
                   user=self.g_teacher)

    def test_lock(self):
        self.group_journal.add_author(self.ap)
        self.group_journal.save()

        api.update(self, 'journals/lock', params={
                'pk': self.group_journal.pk,
                'locked': True
            }, user=self.g_student)
        assert Journal.objects.get(pk=self.group_journal.pk).locked, \
            'Should be locked after student locks'
        api.update(self, 'journals/lock', params={
                'pk': self.group_journal.pk,
                'locked': False
            }, user=self.g_student)
        assert not Journal.objects.get(pk=self.group_journal.pk).locked, \
            'Should be unlocked after student unlocks'

        self.group_assignment.can_lock_journal = False
        self.group_assignment.save()
        api.update(self, 'journals/lock', params={
                'pk': self.group_journal.pk,
                'locked': True
            }, user=self.g_student, status=400)
        assert not Journal.objects.get(pk=self.group_journal.pk).locked, \
            'Should still be unlocked after failed attempt at locking'

        api.update(self, 'journals/lock', params={
                'pk': self.group_journal.pk,
                'locked': True
            }, user=self.g_teacher)
        assert Journal.objects.get(pk=self.group_journal.pk).locked, \
            'Teacher should sitll be able to lock journal'
