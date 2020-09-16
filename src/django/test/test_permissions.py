"""
test_permissions.py

This file tests whether all permissions behave as required.
"""
import datetime
import test.factory as test_factory
from test.factory.user import DEFAULT_PASSWORD

from django.core.validators import ValidationError
from django.test import TestCase

import VLE.factory as factory
import VLE.permissions as permissions
from VLE.models import Participation, Role
from VLE.utils.error_handling import VLEParticipationError, VLEPermissionError, VLEProgrammingError


class PermissionTests(TestCase):
    def setUp(self):
        self.user = factory.make_user('Username', DEFAULT_PASSWORD, email='some@email.address', full_name='Test User')

        self.course1 = factory.make_course('Course', 'crs', startdate=datetime.date.today())
        self.course2 = factory.make_course('Course2', 'crs2', startdate=datetime.date.today())
        self.course_independent = factory.make_course('Independent Course', 'crs3', startdate=datetime.date.today())

        self.assignment = factory.make_assignment('Assignment', 'Assignment linked to multiple courses.',
                                                  courses=[self.course1, self.course2])
        self.assignment_independent = factory.make_assignment('Assignment2', 'Assignment linked to separate course.',
                                                              courses=[self.course_independent])

    def test_no_permissions(self):
        """Ensure the user has no permissions when given no permissions."""
        role = factory.make_role_default_no_perms('SD', self.course_independent)
        factory.make_participation(self.user, self.course_independent, role)

        assert not self.user.has_permission('can_edit_institute_details')
        assert not self.user.has_permission('can_add_course')
        assert not self.user.has_permission('can_delete_course', self.course_independent)
        assert not self.user.has_permission('can_have_journal', self.assignment_independent)

    def test_permission(self):
        """Test whether the user has only the given permission."""
        role = factory.make_role_default_no_perms("SD", self.course_independent, can_delete_assignment=True)
        factory.make_participation(self.user, self.course_independent, role)

        assert self.user.has_permission('can_delete_assignment', self.course_independent)

        assert not self.user.has_permission('can_delete_course_user_group', self.course_independent)
        assert not self.user.has_permission('can_delete_assignment', self.course1)
        assert not self.user.has_permission('can_delete_assignment', self.course2)

    def test_assignment_permission(self):
        assignment = test_factory.Assignment()
        other_assignment = test_factory.Assignment()
        journal = test_factory.Journal(assignment=assignment)
        author = assignment.author
        student = journal.authors.first().user
        not_teacher_perms = ['can_have_journal']
        student_perms = ['can_have_journal', 'can_comment']
        for permission in Role.ASSIGNMENT_PERMISSIONS:
            assert permissions.has_assignment_permission(author, permission, assignment) != \
                (permission in not_teacher_perms)
            assert permissions.has_assignment_permission(student, permission, assignment) == \
                (permission in student_perms)

        assert not permissions.has_assignment_permission(author, 'can_comment', other_assignment)
        assert not permissions.has_assignment_permission(student, 'can_comment', other_assignment)
        self.assertRaises(
            VLEProgrammingError, permissions.has_assignment_permission, student, 'can_view_course_users', assignment)

    def test_course_permission(self):
        course = test_factory.Course()
        other_course = test_factory.Course()
        journal = test_factory.Journal(assignment__courses=[course])
        author = course.author
        student = journal.authors.first().user
        for permission in Role.COURSE_PERMISSIONS:
            assert permissions.has_course_permission(author, permission, course)
            assert not permissions.has_course_permission(student, permission, course)

        assert not permissions.has_course_permission(author, 'can_delete_course', other_course)
        assert not permissions.has_course_permission(student, 'can_delete_course', other_course)
        self.assertRaises(
            VLEProgrammingError, permissions.has_course_permission, student, 'can_publish_grades', course)

    def test_multi_course_assignment_permission(self):
        """Test whether the assignment has the correct permissions when bound to multiple courses."""
        role = factory.make_role_default_no_perms("SD", self.course1, can_have_journal=True)
        factory.make_participation(self.user, self.course1, role)
        role = factory.make_role_default_no_perms("SD", self.course2, can_have_journal=False)
        factory.make_participation(self.user, self.course2, role)

        assert self.user.has_permission('can_have_journal', self.assignment)

        assert not self.user.has_permission('can_edit_assignment', self.assignment)

    def test_multi_course_assignment_negations(self):
        """Test whether the assignment has the correct permissions when bound to multiple courses,
        by negation."""
        role = factory.make_role_default_no_perms("SD", self.course1, can_have_journal=True)
        factory.make_participation(self.user, self.course1, role)
        role = factory.make_role_default_no_perms("SD", self.course2, can_view_all_journals=True)
        factory.make_participation(self.user, self.course2, role)

        assert self.user.has_permission('can_view_all_journals', self.assignment)

        assert not self.user.has_permission('can_have_journal', self.assignment)

    def test_permission_constraints(self):
        factory.make_role_default_no_perms("SD1", self.course1,
                                           can_have_journal=True)
        factory.make_role_default_no_perms("SD2", self.course1,
                                           can_view_all_journals=True)
        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SD3", self.course1,
                          can_have_journal=True, can_view_all_journals=True)

        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SD4", self.course1,
                          can_add_course_users=True)
        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SD5", self.course1,
                          can_delete_course_users=True)
        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SD6", self.course1,
                          can_edit_course_user_group=True)
        factory.make_role_default_no_perms("SD7", self.course1,
                                           can_add_course_users=True, can_view_course_users=True)
        factory.make_role_default_no_perms("SD8", self.course1,
                                           can_delete_course_users=True, can_view_course_users=True)
        factory.make_role_default_no_perms("SD9", self.course1,
                                           can_edit_course_user_group=True, can_view_course_users=True)

        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SDA", self.course1,
                          can_grade=True)
        factory.make_role_default_no_perms("SDB", self.course1,
                                           can_grade=True, can_view_all_journals=True)

        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SDC", self.course1,
                          can_publish_grades=True)
        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SDD", self.course1,
                          can_publish_grades=True, can_view_all_journals=True)
        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SDE", self.course1,
                          can_publish_grades=True, can_grade=True)
        factory.make_role_default_no_perms("SDF", self.course1,
                                           can_publish_grades=True, can_grade=True,
                                           can_view_all_journals=True)

        self.assertRaises(ValidationError, factory.make_role_default_no_perms, "SDG", self.course1,
                          can_comment=True)
        factory.make_role_default_no_perms("SDH", self.course1,
                                           can_comment=True, can_view_all_journals=True)
        factory.make_role_default_no_perms("SDI", self.course1,
                                           can_comment=True, can_have_journal=True)

    def test_admin_permissions(self):
        """Test if the admin has all permissions."""
        user = factory.make_user(
            'superuser', DEFAULT_PASSWORD, email='some@other.com', is_superuser=True, full_name='Test User')

        assert user.has_permission('can_edit_institute_details')
        assert user.has_permission('can_add_course')
        assert user.has_permission('can_delete_course', self.course_independent)
        assert user.has_permission('can_edit_assignment', self.assignment_independent)

        assert not user.has_permission('can_have_journal', self.assignment_independent)

    def test_teacher_permissions(self):
        """Test if the teacher has the right general permissions."""
        user = factory.make_user(
            'teacher', DEFAULT_PASSWORD, email='some@other.com', is_teacher=True, full_name='Test User')

        assert user.has_permission('can_add_course')

        assert not user.has_permission('can_edit_institute_details')
        assert not user.has_permission('can_delete_course', self.course_independent)
        assert not user.has_permission('can_have_journal', self.assignment_independent)

    def test_check_permission(self):
        """Test whether check_permission throws VLEPermissionError when it should throw."""
        role = factory.make_role_default_no_perms("SD", self.course1, can_delete_course=True, can_have_journal=True)
        factory.make_participation(self.user, self.course1, role)

        self.user.check_permission('can_delete_course', self.course1)
        self.assertRaises(VLEPermissionError, self.user.check_permission, 'can_view_course_users', self.course1)
        self.user.check_permission('can_have_journal', self.assignment)
        self.assertRaises(VLEPermissionError, self.user.check_permission, 'can_grade', self.assignment)

    def test_check_participation(self):
        """Tests whether check_participation throws VLEParticipationError when it should throw."""
        role = factory.make_role_default_no_perms("SD", self.course1)
        factory.make_participation(self.user, self.course1, role)

        self.user.check_participation(self.course1)
        self.assertRaises(VLEParticipationError, self.user.check_participation, self.course_independent)
        self.assertRaises(VLEParticipationError, self.user.check_participation, self.course2)

        self.user.check_participation(self.assignment)
        self.assertRaises(VLEParticipationError, self.user.check_participation, self.assignment_independent)

    def test_invalid_permission(self):
        """Ensure the call does not silently fail when passed an invalid permission."""
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'invalid')
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'invalid', self.course_independent)
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'invalid', self.assignment_independent)

    def test_invalid_usage(self):
        """Ensure the call does not silently fail when passed an invalid argument."""
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_have_journal', 5)

    def test_invalid_level(self):
        """Ensure the call of a valid permission on an incorrect level does not silently fail."""
        # General permission on course and assignment level.
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_add_course', self.course_independent)
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_add_course', self.assignment)

        # Course permission on general and assignment level.
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_delete_course')
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_delete_course', self.assignment)

        # Assignment permission on general and course level.
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_have_journal')
        self.assertRaises(VLEProgrammingError, self.user.has_permission, 'can_have_journal', self.course_independent)

    def test_is_course_participant(self):
        """Test if is_participant correctly represents whether the user is participating
        in a course or not."""
        role = factory.make_role_default_no_perms("SD", self.course_independent)
        factory.make_participation(self.user, self.course_independent, role)

        assert self.user.is_participant(self.course_independent)

        assert not self.user.is_participant(self.course1)
        assert not self.user.is_participant(self.course2)

    def test_is_assignment_participant(self):
        """Test if is_participant correctly represent whether the user is participating
        in an assignment or not."""
        role = factory.make_role_default_no_perms("SD", self.course_independent)
        factory.make_participation(self.user, self.course_independent, role)

        assert self.user.is_participant(self.assignment_independent)

        assert not self.user.is_participant(self.assignment)

    def test_is_multi_participant(self):
        """Test if participating in one course does not implicitly participate the user
        in another course or assignment."""
        role = factory.make_role_default_no_perms("SD", self.course1)
        factory.make_participation(self.user, self.course1, role)

        assert self.user.is_participant(self.course1)
        assert self.user.is_participant(self.assignment)

        assert not self.user.is_participant(self.course2)
        assert not self.user.is_participant(self.course_independent)
        assert not self.user.is_participant(self.assignment_independent)

    def test_is_participant_invalid(self):
        self.assertRaises(VLEProgrammingError, self.user.is_participant, None)
        self.assertRaises(VLEProgrammingError, self.user.is_participant, 5)
        self.assertRaises(VLEProgrammingError, self.user.is_participant, 'something')

    def test_serialize(self):
        result = permissions.serialize_general_permissions(self.user)
        assert not result['can_edit_institute_details']
        assert not result['can_add_course']
        self.assertEqual(len(Role.GENERAL_PERMISSIONS), len(result))

        role = factory.make_role_default_no_perms("SD", self.course_independent,
                                                  can_view_course_users=True, can_edit_assignment=True)
        factory.make_participation(self.user, self.course_independent, role)

        result = permissions.serialize_course_permissions(self.user, self.course_independent)
        assert result['can_view_course_users']
        assert not result['can_edit_course_details']
        self.assertEqual(len(Role.COURSE_PERMISSIONS), len(result))

        result = permissions.serialize_assignment_permissions(self.user, self.assignment_independent)
        assert result['can_edit_assignment']
        assert not result['can_have_journal']
        self.assertEqual(len(Role.ASSIGNMENT_PERMISSIONS), len(result))

    def test_is_supervisor(self):
        high_user = test_factory.Teacher()
        middle_user = test_factory.Student()
        low_user = test_factory.Student()

        high1 = factory.make_role_default_no_perms(
            "HIGH", self.course1, can_view_course_users=True, can_view_all_journals=True)
        factory.make_participation(high_user, self.course1, high1)

        high2 = factory.make_role_default_no_perms(
            "HIGH", self.course2, can_view_course_users=True, can_view_all_journals=True)
        factory.make_participation(high_user, self.course2, high2)

        middle1 = factory.make_role_default_no_perms("MIDDLE", self.course1, can_view_course_users=True)
        factory.make_participation(middle_user, self.course1, middle1)

        low1 = factory.make_role_default_no_perms("LOW", self.course1)
        low2 = factory.make_role_default_no_perms("LOW", self.course2)
        factory.make_participation(low_user, self.course1, low1)
        factory.make_participation(low_user, self.course2, low2)

        assert permissions.is_user_supervisor_of(high_user, low_user)
        assert permissions.is_user_supervisor_of(high_user, middle_user)
        assert permissions.is_user_supervisor_of(middle_user, high_user)
        assert permissions.is_user_supervisor_of(middle_user, low_user)
        assert not permissions.is_user_supervisor_of(low_user, high_user)
        assert not permissions.is_user_supervisor_of(low_user, middle_user)

        Participation.objects.get(course=self.course1, user=low_user).delete()

        assert permissions.is_user_supervisor_of(high_user, low_user)
        assert not permissions.is_user_supervisor_of(middle_user, low_user)
        assert not permissions.is_user_supervisor_of(low_user, high_user)
        assert not permissions.is_user_supervisor_of(low_user, middle_user)

        Participation.objects.get(course=self.course2, user=low_user).delete()

        assert not permissions.is_user_supervisor_of(high_user, low_user)
        assert not permissions.is_user_supervisor_of(middle_user, low_user)
        assert not permissions.is_user_supervisor_of(low_user, high_user)
        assert not permissions.is_user_supervisor_of(low_user, middle_user)

    def test_all_permissions_are_in_model(self):
        assert set(p.name for p in Role._meta.get_fields(include_parents=False) if p.name.startswith('can_')) == \
            set(Role.PERMISSIONS), 'All permission fields should be in Role.PERMISSIONS and the other way around'
