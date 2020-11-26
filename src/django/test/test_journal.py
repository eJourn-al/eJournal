import test.factory as factory
from test.utils import api
from test.utils.performance import queries_invariant_to_db_size

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from django.test import TestCase

from VLE.models import (Assignment, AssignmentParticipation, Comment, Content, Course, Entry, FileContext, Group,
                        Journal, JournalImportRequest, Participation, Role, User)
from VLE.serializers import JournalSerializer
from VLE.utils.error_handling import VLEProgrammingError


class JournalAPITest(TestCase):
    def setUp(self):
        self.journal = factory.Journal()
        self.journal = Journal.objects.get(pk=self.journal.pk)
        self.student = self.journal.authors.first().user
        self.assignment = self.journal.assignment
        self.course = self.assignment.courses.first()
        self.teacher = self.course.author

        self.group_assignment = factory.Assignment(group_assignment=True)
        self.group_journal = factory.GroupJournal(assignment=self.group_assignment)
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
        self.group_journal2 = factory.GroupJournal(assignment=self.group_assignment)
        self.group_journal2 = Journal.objects.get(pk=self.group_journal2.pk)
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

        empty_journal = factory.Journal(ap=False, assignment=assignment)
        assert not empty_journal.authors.exists()

    def test_journal_factory_assignment_author_chain(self):
        users_before = list(User.objects.values_list('pk', flat=True))
        journals_before = list(Journal.objects.values_list('pk', flat=True))
        journal = factory.Journal()
        assert User.objects.exclude(pk__in=users_before).count() == 2, 'Only a student and a teacher user are generated'
        assert Journal.objects.exclude(pk__in=journals_before).count() == 1, '1 journal for the student is generated'

        assignment = journal.assignment
        users_before = list(User.objects.values_list('pk', flat=True))
        factory.Journal(assignment=assignment)
        assert User.objects.exclude(pk__in=users_before).count() == 1, 'Only a student is generated'

        users_before = list(User.objects.values_list('pk', flat=True))
        factory.Journal(assignment__author=assignment.author)
        assert User.objects.exclude(pk__in=users_before).count() == 2, 'A student is generated and a course author'

        users_before = list(User.objects.values_list('pk', flat=True))
        factory.Journal(assignment__author=assignment.author, assignment__courses=[])
        assert User.objects.exclude(pk__in=users_before).count() == 1, 'Only a student is generated'

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
            """Creating a group journal with 3 users, also creates three assignment participations (plus one for the
            teacher)"""
        assert AssignmentParticipation.objects.filter(
            journal=group_journal, user__in=group_journal.authors.all().values('user')).count() == 3, \
            'All students APs are attached to the journal'

        users.append(factory.Student())
        self.assertRaises(ValidationError, factory.GroupJournal, add_users=users, author_limit=3)

    def test_lti_group_journal_factory(self):
        lti_group_journal = factory.LtiGroupJournal(add_users=[factory.Student()], entries__n=0)
        lti_group_assignment = lti_group_journal.assignment

        assert lti_group_assignment.is_group_assignment
        assert lti_group_journal.author_limit > 1

        assert lti_group_journal.authors.exists()
        for ap in lti_group_journal.authors.all():
            assert ap.grade_url
            assert ap.sourcedid

    def test_journal_validation(self):
        j = factory.GroupJournal(author_limit=1)
        # NOTE: This already saves the journal, bulk updates bypass model save
        j.authors.add(factory.AssignmentParticipation())
        self.assertRaises(ValidationError, j.save)

        j = factory.Journal()
        j.author_limit = 2
        self.assertRaises(ValidationError, j.save)

    def test_journal_reset(self):
        assignment = factory.Assignment(format__templates=[])
        factory.TemplateAllTypes(format=assignment.format)
        g_journal = factory.GroupJournal()
        entry = Entry.objects.get(node__journal=g_journal)
        student = entry.author

        factory.JournalImportRequest(target=g_journal, author=student, state=JournalImportRequest.PENDING)
        factory.JournalImportRequest(target=g_journal, author=student, state=JournalImportRequest.APPROVED_EXC_GRADES)
        factory.JournalImportRequest(source=g_journal, author=student, state=JournalImportRequest.PENDING)
        source_approved_jir = factory.JournalImportRequest(
            source=g_journal, author=student, state=JournalImportRequest.APPROVED_EXC_GRADES)

        g_journal.authors.remove(g_journal.authors.first())
        g_journal.reset()

        assert not g_journal.node_set.exists()
        assert not Entry.objects.filter(pk=entry.pk).exists()
        assert not Content.objects.filter(entry=entry).exists()
        assert not FileContext.objects.filter(journal=g_journal).exists()
        assert not FileContext.objects.filter(content__in=entry.content_set.all()).exists()
        assert not Comment.objects.filter(entry=entry).exists()

        remaining_jir_ids = g_journal.import_request_targets.all().values('pk') \
            | g_journal.import_request_sources.all().values('pk')
        remaining_jir = JournalImportRequest.objects.get(pk__in=remaining_jir_ids)
        assert remaining_jir == source_approved_jir, \
            """When a group journal is reset all jirs apart from those approved with the journal as source should be
            removed. Approved JIRs with the journal as source should persists as this is how entries are flagged as
            imported."""

    def test_annotated_name(self):
        # A short name which will not be truncated with two users in a journal
        short_name = 'Short name'
        # NOTE, comments or assert messages why the behaviour is expected missing
        journal = factory.Journal()
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.name == journal.authors.first().user.full_name

        # Test author name
        user = journal.authors.first().user
        user.full_name = short_name
        user.save()
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.name == short_name
        assert journal.full_names == short_name
        assert journal.usernames == user.username

        # Test stored name
        journal.stored_name = 'stored name'
        journal.save()
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.name == 'stored name'
        assert journal.full_names == short_name

        # Test add author
        group_journal = factory.GroupJournal(ap__user__full_name='Short name', add_users=[factory.Student()])
        group_journal = Journal.objects.get(pk=group_journal.pk)
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
        group_journal = Journal.objects.get(pk=group_journal.pk)
        assert 'update name' in group_journal.full_names, \
            'Updated users name is reflected in cached journals full names'
        assert group_journal.name

        # Test remove author
        group_journal.remove_author(ap)
        group_journal = Journal.objects.get(pk=group_journal.pk)
        assert ap.user.full_name not in group_journal.name
        assert ap.user.full_name not in group_journal.full_names
        assert group_journal.full_names == group_journal.authors.first().user.full_name
        assert group_journal.name == 'Journal {}'.format(Journal.objects.filter(assignment=self.assignment).count()), \
            'Group journal name should still default to assignments journal count'

    def test_annotated_import_requests(self):
        journal = factory.Journal(entries__n=0)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.import_requests == 0, 'A journal has no JIRs by default'

        jir = factory.JournalImportRequest(target=journal, state=JournalImportRequest.APPROVED_EXC_GRADES)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.import_requests == 0, 'Only pending JIRs should count towards import request total'

        jir = factory.JournalImportRequest(target=journal, state=JournalImportRequest.PENDING)
        jir2 = factory.JournalImportRequest(target=journal, state=JournalImportRequest.PENDING)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.import_request_targets.count() == 3, 'Journal should have three JIRs with journal as target'
        assert journal.import_requests == 2, 'Import requests should update on the creation of a JIR'

        jir.delete()
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.import_requests == 1, 'Import requests should update on the deletion of a JIR'

        jir2.state = JournalImportRequest.DECLINED
        jir2.save()
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.import_requests == 0, 'Import requests should update on the state change of a JIR'

    def test_annotated_grade(self):
        journal = factory.Journal(entries__n=0)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 0
        assert journal.unpublished == 0
        assert journal.needs_marking == 0

        factory.Grade(grade=5, published=False, entry__node__journal=journal)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 0
        assert journal.unpublished == 1
        assert journal.needs_marking == 0

        grade = factory.Grade(grade=5, published=True, entry__node__journal=journal)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 5
        assert journal.unpublished == 1
        assert journal.needs_marking == 0

        factory.Grade(entry=grade.entry, grade=3, published=True)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 3
        assert journal.unpublished == 1
        assert journal.needs_marking == 0

        entry = factory.UnlimitedEntry(grade=None, node__journal=journal)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 3
        assert journal.unpublished == 1
        assert journal.needs_marking == 1

        factory.Grade(entry=entry, published=False, grade=10)
        journal = Journal.objects.get(pk=journal.pk)
        assert journal.grade == 3
        assert journal.unpublished == 2
        assert journal.needs_marking == 0

    def test_annotated_groups(self):
        course = factory.Course()
        course2 = factory.Course()
        g_assignment = factory.Assignment(group_assignment=True, courses=[course, course2])
        g_journal = factory.GroupJournal(entries__n=0, add_users=[factory.Student()], assignment=g_assignment)
        g_journal = Journal.objects.get(pk=g_journal.pk)
        student = g_journal.authors.first().user
        student2 = g_journal.authors.last().user
        Participation.objects.filter(user=student, course=course2).delete()
        student_course_participation = Participation.objects.get(user=student, course=course)
        Participation.objects.filter(user=student2, course=course).delete()
        student2_course2_participation = Participation.objects.get(user=student2, course=course2)
        student_ap = g_journal.authors.get(user=student)

        assert g_journal.groups == [], 'By default a journal holds no groups'

        group = factory.Group(course=course)
        group2 = factory.Group(course=course2)

        student_course_participation.groups.add(group)
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert g_journal.groups == [group.pk], 'Added group appears in the computed property'

        student2_course2_participation.groups.add(group2)
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert group.pk in g_journal.groups and group2.pk in g_journal.groups, \
            'Added group appears in the computed property for all authors'

        student_course_participation.groups.remove(group)
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert g_journal.groups == [group2.pk], \
            'Removing a student from a group also removes the group pk from the journal computed group property'

        course2.delete()
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert g_journal.groups == [], \
            'Removing a course from an assignment should also remove the respective groups from a journal'

        student_course_participation.groups.add(group)
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert g_journal.groups == [group.pk], 'Journal groups once again holds a single value'
        student_ap.delete()
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert g_journal.groups == [], 'Removing a user from a journal updates the computed property'

        student_ap = factory.AssignmentParticipation(assignment=g_assignment, user=student, journal=g_journal)
        g_journal = Journal.objects.get(pk=g_journal.pk)
        assert g_journal.groups == [group.pk], \
            'Adding a user to a journal updates the journal\'s groups computed property'

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
        self.journal = Journal.objects.get(pk=self.journal.pk)
        assert self.journal.image == 'new_image'

        second_ap = factory.AssignmentParticipation(assignment=self.group_assignment)
        self.group_journal.add_author(second_ap)
        assert self.group_journal.image == settings.DEFAULT_PROFILE_PICTURE
        second_ap.user.profile_picture = 'new_image'
        second_ap.user.save()
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
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
        non_group_journal = Journal.objects.get(pk=non_group_journal.pk)
        assert non_group_journal.name == non_group_journal.authors.first().user.full_name, \
            'Non group journals should get name of author'
        non_group_journal.authors.first().user.full_name = non_group_journal.authors.first().user.full_name + 'NEW'
        non_group_journal.authors.first().user.save()
        assert non_group_journal.name == non_group_journal.authors.first().user.full_name, \
            'Non group journals name should get updated when author name changes'

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
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
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
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
        assert self.group_journal.author_limit == 9 and self.group_journal.name == 'NEW'

        for i in range(self.group_journal.author_limit - self.group_journal.authors.count()):
            self.group_journal.add_author(factory.AssignmentParticipation(assignment=self.group_assignment))

        api.update(
            self, 'journals', params={'pk': self.group_journal.pk, 'author_limit': Journal.UNLIMITED},
            user=self.g_teacher)
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
        assert self.group_journal.author_limit == Journal.UNLIMITED

        api.update(
            self, 'journals', params={'pk': self.group_journal.pk, 'author_limit': 3},
            user=self.g_teacher, status=400)
        self.group_journal = Journal.objects.get(pk=self.group_journal.pk)
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
        student1_group = factory.Student()
        group_journal = factory.GroupJournal(ap__user=student1_group)
        assignment = group_journal.assignment
        teacher = assignment.author
        unadded_student = factory.AssignmentParticipation(user=factory.Student(), assignment=assignment).user
        unrelated_student = factory.Student()

        # Test students that are not added to the journal are NOT allowed to view other members
        api.get(self, 'journals/get_members', params={'pk': group_journal.pk}, user=unadded_student, status=403)
        api.get(self, 'journals/get_members', params={'pk': group_journal.pk}, user=factory.Teacher(), status=403)

        # Test before adding student, that student is not returned
        members = api.get(self, 'journals/get_members', params={'pk': group_journal.pk}, user=teacher)['authors']
        serialized_user_ids = [m['user']['id'] for m in members]
        assert list(group_journal.authors.all().values_list('user__pk', flat=True)) == serialized_user_ids
        assert student1_group.pk in serialized_user_ids
        assert unadded_student.pk not in serialized_user_ids

        # Only students related to the assignment can be added to a journal
        api.update(self, 'journals/add_members', params={'pk': group_journal.pk, 'user_ids': [unrelated_student.pk]},
                   user=teacher, status=403)

        # Add the unadded student ot the journal
        api.update(self, 'journals/add_members', params={'pk': group_journal.pk, 'user_ids': [unadded_student.pk]},
                   user=teacher)
        student2_group = unadded_student

        members = api.get(self, 'journals/get_members', params={'pk': group_journal.pk}, user=teacher)['authors']
        serialized_user_ids = [m['user']['id'] for m in members]
        assert student2_group.pk in serialized_user_ids, \
            'After adding the student to the group journal, the newly added student should be serialized'

        # Test students that are added to the journal ARE allowed to view other members
        api.get(self, 'journals/get_members', params={'pk': group_journal.pk}, user=student2_group)

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

    def test_journal_author_property(self):
        journal = factory.Journal()

        with self.assertNumQueries(2):
            student = journal.authors.first().user

        with self.assertNumQueries(1):
            assert student == journal.author, 'Journal.author is correct and faster'

        group_journal = factory.GroupJournal()

        # Author access is ambiguous when dealing with a group journal
        with self.assertRaises(VLEProgrammingError):
            group_journal.author

    def test_journal_queryset_order_by_authors_first(self):
        assignment = factory.Assignment(group_assignment=True)

        journal_with_author = factory.GroupJournal(assignment=assignment)
        empty_journal = factory.GroupJournal(ap=False, assignment=assignment)
        empty_journal2 = factory.GroupJournal(ap=False, assignment=assignment)
        journal_with_2_authors = factory.GroupJournal(assignment=assignment, add_users=[factory.Student()])

        qry = Journal.objects.filter(assignment=assignment).order_by_authors_first()
        assert len(qry) == 4, 'Equal to the number of journals (not APs)'

        # Journals with authors come before those without
        assert qry[0] == journal_with_author or qry[1] == journal_with_author
        assert qry[0] == journal_with_2_authors or qry[1] == journal_with_2_authors
        assert qry[2] == empty_journal or qry[3] == empty_journal
        assert qry[2] == empty_journal2 or qry[3] == empty_journal2

    def test_journal_queryset_for_course(self):
        c1 = factory.Course()
        c2 = factory.Course()
        shared_assignment = factory.Assignment(courses=[c1, c2])
        p_c1 = factory.Participation(course=c1, role=c1.role_set.filter(name='Student').first())
        p_c2 = factory.Participation(course=c2, role=c2.role_set.filter(name='Student').first())
        j_c1 = factory.Journal(assignment=shared_assignment, ap__user=p_c1.user, ap__add_user_to_missing_courses=False)
        j_c2 = factory.Journal(assignment=shared_assignment, ap__user=p_c2.user, ap__add_user_to_missing_courses=False)

        assert Journal.objects.filter(assignment=shared_assignment).for_course(c1).get() == j_c1
        assert Journal.objects.filter(assignment=shared_assignment).for_course(c2).get() == j_c2

        shared_assignment = factory.Assignment(courses=[c1, c2], group_assignment=True)
        p_c1 = factory.Participation(course=c1, role=c1.role_set.filter(name='Student').first())
        p_c2 = factory.Participation(course=c2, role=c2.role_set.filter(name='Student').first())
        empty_group_journal = factory.GroupJournal(assignment=shared_assignment, ap=False)
        group_journal_c1 = factory.GroupJournal(
            assignment=shared_assignment, ap__user=p_c1.user, ap__add_user_to_missing_courses=False)
        group_journal_c2 = factory.GroupJournal(
            assignment=shared_assignment, ap__user=p_c2.user, ap__add_user_to_missing_courses=False)

        journals_for_course_c1 = Journal.objects.filter(assignment=shared_assignment).for_course(c1)
        assert empty_group_journal in journals_for_course_c1, 'Empty group journals should appear for all courses'
        assert group_journal_c1 in journals_for_course_c1
        assert group_journal_c2 not in journals_for_course_c1

        journals_for_course_c2 = Journal.objects.filter(assignment=shared_assignment).for_course(c2)
        assert empty_group_journal in journals_for_course_c2, 'Empty group journals should appear for all courses'
        assert group_journal_c2 in journals_for_course_c2
        assert group_journal_c1 not in journals_for_course_c2

    def test_journal_serializer(self):
        journal = factory.Journal()
        journal = Journal.objects.get(pk=journal.pk)
        student = journal.author
        assignment = journal.assignment
        teacher = assignment.author

        queries_invariant_to_db_size(
            call=JournalSerializer,
            call_args=[assignment],
            call_kwargs={'context': {'user': teacher}, 'many': True},
            add_state=[(factory.Journal, {'assignment': assignment})],
        )

        queries_invariant_to_db_size(
            call=JournalSerializer,
            call_args=[assignment],
            call_kwargs={'context': {'user': student}, 'many': True},
            add_state=[(factory.Journal, {'assignment': assignment})],
        )

        data = JournalSerializer(journal, context={'user': student}).data
        assert data['import_requests'] is None
        assert data['usernames'] is None

        data = JournalSerializer(journal, context={'user': teacher}).data
        assert data['import_requests'] == 0
        assert data['usernames'] == journal.usernames

    def test_annotate_grade(self):
        journal = factory.Journal(entries__n=0, bonus_points=0.5)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=True)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1.0051, grade__published=True)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)
        factory.UnlimitedEntry(node__journal=journal, grade=None)

        correct_grade = 2.51

        def grade(journal):
            """Old computed method"""
            return round(
                journal.bonus_points +
                journal.node_set.filter(
                    entry__grade__published=True
                ).values(
                    'entry__grade__grade'
                ).aggregate(
                    Sum(
                        'entry__grade__grade'
                    )
                )['entry__grade__grade__sum']
                or 0,
                2
            )
        old_grade = grade(journal)

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_grade().get()
        assert qry_journal.grade == old_grade == correct_grade

        journal = factory.Journal(entries__n=0, bonus_points=0, assignment=journal.assignment)
        qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_grade().get()
        assert qry_journal.grade == 0, 'Should default to zero not None'

    def test_annotate_unpublished(self):
        journal = factory.Journal(entries__n=0)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=True)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)
        factory.UnlimitedEntry(node__journal=journal, grade=None)

        unpublished = journal.node_set.filter(entry__grade__published=False).count()
        assert unpublished == 2

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_unpublished().get()
        assert qry_journal.unpublished == unpublished

        no_unpublished_journal = factory.Journal(entries__n=0, assignment=journal.assignment)
        no_unpublished_journal = Journal.all_objects.filter(
            pk=no_unpublished_journal.pk).allowed_journals().annotate_unpublished().get()
        assert no_unpublished_journal.unpublished == 0, 'Unpublished should default to zero not None'

    def test_annotate_import_requests(self):
        jir = factory.JournalImportRequest()
        target = jir.target

        import_requests = target.import_request_targets.filter(state=JournalImportRequest.PENDING).count()
        assert import_requests == 1

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=target.pk).annotate_import_requests().get()

        assert import_requests == qry_journal.import_requests

    def test_annotate_needs_marking(self):
        journal = factory.Journal(entries__n=0)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=True)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)
        factory.UnlimitedEntry(node__journal=journal, grade=None)

        needs_marking = journal.node_set.filter(entry__isnull=False, entry__grade__isnull=True).count()
        assert needs_marking == 1

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_needs_marking().get()
        assert qry_journal.needs_marking == needs_marking

        no_needs_marking_journal = factory.Journal(entries__n=0, assignment=journal.assignment)
        no_needs_marking_journal = Journal.all_objects.filter(
            pk=no_needs_marking_journal.pk).allowed_journals().annotate_needs_marking().get()
        no_needs_marking_journal.needs_marking == 0, 'Needs marking should default to zero not None'

    def test_annotate_needs_lti_link(self):
        student2 = factory.Student(full_name='student2')
        student3 = factory.Student(full_name='student3')
        journal = factory.LtiGroupJournal(ap__user__full_name='student', add_users=[student2, student3])
        journal.authors.filter(user__in=[student2, student3]).update(sourcedid=None)

        assert journal.authors.filter(sourcedid__isnull=True).count() == 2
        assert journal.assignment.active_lti_id

        def needs_lti_link(journal):
            """Old computed method"""
            if not journal.assignment.active_lti_id:
                return list()
            return list(journal.authors.filter(sourcedid__isnull=True).values_list('user__full_name', flat=True))

        old_needs_lti_link = needs_lti_link(journal)
        for name in old_needs_lti_link:
            assert name in [student2.full_name, student3.full_name]

        qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_needs_lti_link().get()
        assert qry_journal.needs_lti_link == old_needs_lti_link

        journal.assignment.active_lti_id = None
        journal.assignment.save()
        qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_needs_lti_link().get()
        assert qry_journal.needs_lti_link == [], 'No LTI links needed for a non LTI assignment'

        journal = factory.LtiJournal()
        qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_needs_lti_link().get()
        assert qry_journal.needs_lti_link == [], 'NO LTI links needed if all APs are correctly linked'

    def test_annotate_name(self):
        journal = factory.GroupJournal(ap__user__full_name='SAME', add_users=[factory.Student(full_name='SAME')])
        journal_stored_name = factory.Journal(stored_name='Stored name')

        def name(journal):
            """Old computed method"""
            if journal.stored_name:
                return journal.stored_name
            return ', '.join(journal.authors.values_list('user__full_name', flat=True))

        old_name = name(journal)
        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(
                pk=journal.pk).allowed_journals().annotate_full_names().annotate_name().get()
        assert old_name == qry_journal.name

        entry = Entry.objects.filter(node__journal=journal).annotate_full_names().annotate_name().first()
        assert entry.name == old_name

        old_name = name(journal_stored_name)
        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(
                pk=journal_stored_name.pk).annotate_full_names().annotate_name().get()
        assert old_name == qry_journal.name

        entry = Entry.objects.filter(node__journal=journal_stored_name).annotate_full_names().annotate_name().first()
        assert entry.name == old_name

    def test_annotate_image(self):
        student_default_pic = factory.Student()
        student_custom_pic = factory.Student(profile_picture='some pic link')
        student2_custom_pic = factory.Student(profile_picture='some pic link2')
        journal = factory.GroupJournal(
            author_limit=4,
            ap__user=student_default_pic,
            add_users=[student_default_pic, student_custom_pic, student2_custom_pic]
        )

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_image().get()
        assert qry_journal.image in [student_custom_pic.profile_picture, student2_custom_pic.profile_picture],\
            'First non default author image should be selected, order is not relevant'

        journal = factory.Journal(ap__user=student_default_pic)
        qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_image().get()
        assert qry_journal.image == student_default_pic.profile_picture

    def test_annotate_full_names(self):
        journal = factory.GroupJournal(ap__user__full_name='Diff', add_users=[factory.Student(full_name='Different')])
        assignment = journal.assignment
        full_names = journal.authors.values_list('user__full_name', flat=True)
        factory.Journal(ap__user=journal.authors.first().user)  # Some unrelated journal of same user

        def check_full_names(instance, oracle):
            split_annotation = instance.full_names.split(', ')
            assert len(split_annotation) == len(oracle)

            for name in split_annotation:
                assert name in oracle

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_full_names().get()
        check_full_names(qry_journal, full_names)

        entry = Entry.objects.filter(node__journal=journal).annotate_full_names().first()
        check_full_names(entry, full_names)

        journal = factory.GroupJournal(
            assignment=assignment, ap__user__full_name='SAME', add_users=[factory.Student(full_name='SAME')])
        qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_full_names().get()
        full_names = journal.authors.values_list('user__full_name', flat=True)
        assert len(qry_journal.full_names.split(', ')) != len(full_names), \
            'Equal names are merged, but this is acceptable since the occurance is low (same group and full names)'

    def test_annotate_usernames(self):
        journal = factory.GroupJournal(add_users=[factory.Student()])
        usernames = journal.authors.values_list('user__username', flat=True)
        factory.Journal(ap__user=journal.authors.first().user)  # Some unrelated journal of same user

        def check_usernames(instance, oracle):
            split_annotation = instance.usernames.split(', ')
            assert len(split_annotation) == len(oracle)

            for name in split_annotation:
                assert name in oracle

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_usernames().get()
        check_usernames(qry_journal, usernames)

        entry = Entry.objects.filter(node__journal=journal).annotate_usernames().first()
        check_usernames(entry, usernames)

    def test_annotate_groups(self):
        def groups(journal):
            """Old computed method"""
            return list(
                Group.objects.filter(
                    participation__user__in=journal.authors.values('user'),
                ).values_list(
                    'pk',
                    flat=True,
                ).distinct()
            )

        course = factory.Course()
        group = factory.Group(course=course)
        group2 = factory.Group(course=course)
        p1 = factory.Participation(course=course)
        p2 = factory.Participation(course=course)
        p3 = factory.Participation(course=course)
        p1.groups.add(group)
        p2.groups.add(group, group2)
        journal = factory.GroupJournal(ap__user=p1.user, add_users=[p2.user, p3.user])

        old_groups = groups(journal)

        with self.assertNumQueries(1):
            qry_journal = Journal.all_objects.filter(pk=journal.pk).allowed_journals().annotate_groups().get()

        assert len(old_groups) == len(qry_journal.groups)
        assert all(elem in old_groups for elem in qry_journal.groups), 'Order may differ'

    def test_annotated_fields(self):
        journal = factory.GroupJournal(add_users=[factory.Student(), factory.Student()])
        factory.JournalImportRequest(target=journal)

        with self.assertNumQueries(1):
            journal_qry = Journal.all_objects.filter(pk=journal.pk).annotate_fields().get()

        for annotated_field in Journal.ANNOTATED_FIELDS:
            assert hasattr(journal_qry, annotated_field)

    def test_missing_annotated_field(self):
        journal = factory.Journal()
        assert journal.missing_annotated_field

        journal = Journal.objects.get(pk=journal.pk)
        assert not journal.missing_annotated_field

        journal = Journal.all_objects.filter(pk=journal.pk).annotate(full_names=F('pk')).get()
        assert journal.missing_annotated_field

    def test_can_add(self):
        student = factory.Student()
        student2 = factory.Student()
        journal = factory.GroupJournal(ap__user=student, add_users=[student2])
        journal = Journal.objects.get(pk=journal.pk)
        unrelated_student = factory.AssignmentParticipation(assignment=journal.assignment).user
        teacher = journal.assignment.author
        admin = factory.Admin()

        assert not journal.can_add(None)
        assert not journal.can_add(False)
        with self.assertRaises(ValueError):
            assert not journal.can_add(journal.authors.first()), 'Check is based on user instance not AP'

        assert journal.can_add(student)
        assert journal.can_add(student2)

        assert not journal.can_add(unrelated_student)
        assert not journal.can_add(teacher)
        assert not journal.can_add(admin)
