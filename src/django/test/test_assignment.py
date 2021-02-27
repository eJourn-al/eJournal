import datetime
import test.factory as factory
import test.utils.generic_utils
from copy import deepcopy
from test.utils import api
from test.utils.generic_utils import check_equality_of_imported_file_context, equal_models
from test.utils.performance import QueryContext, assert_num_queries_less_than
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

import VLE.tasks.beats.cleanup as cleanup
import VLE.utils.statistics as stats_utils
from VLE.models import (Assignment, AssignmentParticipation, Category, Course, Entry, Field, FileContext, Format, Group,
                        Journal, JournalImportRequest, Node, Participation, PresetNode, Role, Template)
from VLE.serializers import AssignmentSerializer, SmallAssignmentSerializer
from VLE.utils.error_handling import VLEParticipationError, VLEProgrammingError
from VLE.utils.file_handling import get_files_from_rich_text
from VLE.views.assignment import day_neutral_datetime_increment, set_assignment_dates


class AssignmentAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = factory.Admin()
        cls.teacher = factory.Teacher()
        cls.course = factory.Course(author=cls.teacher)
        cls.student = factory.Participation(course=cls.course).user

        cls.create_params = {
            'name': 'test',
            'description': 'test_description',
            'points_possible': 10,
            'course_id': cls.course.pk
        }

    def test_rest(self):
        # Test the basic rest functionality as a superuser
        api.test_rest(self, 'assignments',
                      create_params=self.create_params,
                      get_params={'course_id': self.course.pk},
                      update_params={'description': 'test_description2'},
                      delete_params={'course_id': self.course.pk},
                      user=self.admin)

        # Test the basic rest functionality as a teacher
        api.test_rest(self, 'assignments',
                      create_params=self.create_params,
                      get_params={'course_id': self.course.pk},
                      update_params={'description': 'test_description2'},
                      delete_params={'course_id': self.course.pk},
                      user=self.teacher)

        # Test the basic rest functionality as a student
        api.test_rest(self, 'assignments',
                      create_params=self.create_params,
                      create_status=403,
                      user=factory.Student())

    def test_assignment_factory(self):
        # A Format should only be intialized via its respective Assignment
        self.assertRaises(VLEProgrammingError, factory.Format)

        j_all_count = Journal.all_objects.count()
        j_count = Journal.objects.count()
        ap_count = AssignmentParticipation.objects.count()

        assignment = factory.Assignment()
        assert assignment.author is not None, 'Author should be generated if not specified'
        assert assignment.courses.exists(), 'Course is generated for the generated assignment'
        assert assignment.format.template_set.exists(), 'Templates are generated alongside the assignment'
        assert not assignment.format.presetnode_set.exists(), 'Assignment is initialized by default without PresetNodes'
        assert j_count == Journal.objects.count(), 'The created journal (teachers) cannot be queried directly'
        assert j_all_count + 1 == Journal.all_objects.count(), 'One journal is created (assuming the teachers)'
        assert ap_count + 1 == AssignmentParticipation.objects.count(), 'One AP is created (assuming the teachers)'
        ap = AssignmentParticipation.objects.get(~Q(journal=None), user=assignment.author, assignment=assignment)
        assert ap.journal.authors.first().user.pk == assignment.author.pk, 'The AP belongs to the assignment author'
        assert ap.journal.assignment.pk == assignment.pk, 'AP is correctly linked to the teacher and assignment'

        assignment = factory.Assignment(courses=[])
        assert not assignment.courses.exists(), 'It is possible to generate an assignment without any associated course'
        assert assignment.author, 'The assignment still has an author, even without associated course.'

        assignment_author_name = 'Test'
        assignment = factory.Assignment(author__full_name=assignment_author_name)
        assert assignment.author.full_name == assignment_author_name, \
            'If any kwargs relate to the author, generate the author and pass the args along'

        course = factory.Course()
        assignment = factory.Assignment(courses=[course])
        teacher_role = Role.objects.get(name='Teacher', course=course)

        assert assignment.courses.filter(pk=course.pk).exists(), 'Assignment is successfully linked to the course'
        assert course.author.pk == assignment.author.pk, 'Course author is reused for the assignment by default'
        assert Participation.objects.filter(role=teacher_role, user=assignment.author, course=course).exists(), \
            'Assignment author is an actual teacher in the associated course'

        teacher = self.teacher
        course2 = factory.Course()
        assignment2 = factory.Assignment(courses=[course, course2], author=teacher)
        assert assignment2.author.pk == teacher.pk, 'Assignment author can be specified manually as well'
        assert Participation.objects.filter(
            role__name='Teacher', user=assignment2.author, course__in=[course, course2]).count() == 2, \
            'Assignment author is also an actual teacher in the associated courses when specified manually'

        lti_assignment = factory.LtiAssignment()
        assert lti_assignment.courses.filter(assignment_lti_id_set__contains=[lti_assignment.active_lti_id]).count() \
            == lti_assignment.courses.count(), 'The lti id is added to each course\'s assignment id'

        course = factory.Course()
        participation = factory.Participation(role=course.role_set.filter(name='Student').first(), course=course)
        journal_count = Journal.objects.count()
        assignment = factory.Assignment(courses=[course])
        assert journal_count + 1 == Journal.objects.count(), 'Student should have gotten a journal'
        assert Journal.objects.get(authors__user=participation.user, assignment=assignment)

    def test_group_assignment_factory(self):
        j_all_count = Journal.all_objects.count()
        ap_count = AssignmentParticipation.objects.count()
        j_count = Journal.all_objects.count()
        g_assignment = factory.Assignment(group_assignment=True)

        assert g_assignment.is_group_assignment
        assert j_all_count == Journal.all_objects.count(), \
            'There is no journal created for the teacher in a group assignment'
        assert ap_count + 1 == AssignmentParticipation.objects.count(), 'One AP created for the teacher'
        ap = AssignmentParticipation.objects.get(user=g_assignment.author, assignment=g_assignment)
        assert ap.journal is None, 'The AP of the teacher does not link to any journal in a group assignment'

        g_assignment.is_group_assignment = False
        g_assignment.save()

        ap = AssignmentParticipation.objects.get(user=g_assignment.author, assignment=g_assignment)
        assert j_all_count + 1 == Journal.all_objects.count(), 'One journal is created (assuming the teachers)'
        assert j_count == Journal.objects.count(), 'The created journal (teachers) cannot be queried directly'
        assert ap_count + 1 == AssignmentParticipation.objects.count(), 'One AP is created (assuming the teachers)'
        assert ap.journal.authors.first().user.pk == g_assignment.author.pk, 'The AP belongs to the assignment author'
        assert ap.journal.assignment.pk == g_assignment.pk, 'AP is correctly linked to the teacher and assignment'
        assert ap.journal is not None, \
            'The AP is linked to a journal now that the assignment is no longer a group assignment'
        assert ap.journal.authors.count() == 1 and ap.journal.authors.first().user.pk == g_assignment.author.pk, \
            'The created journal is linked to the assignment teacher'

    def test_assignment_update_params_factory(self):
        assignment = factory.Assignment()

        pre_update_assignment = AssignmentSerializer(
            AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
            context={'user': assignment.author},
        ).data

        format_update_dict = factory.AssignmentUpdateParams(assignment=assignment)
        api.update(self, 'assignments', params=format_update_dict, user=assignment.author)

        post_update_format = AssignmentSerializer(
            AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
            context={'user': assignment.author},
        ).data

        assert test.utils.generic_utils.equal_models(pre_update_assignment, post_update_format), \
            'Unmodified update paramaters should be able to succesfully update the format without making any changes'

    def test_assignment_constraint(self):
        with transaction.atomic():
            format = Format.objects.create()
            self.assertRaises(IntegrityError, Assignment.objects.create, points_possible=-1.0, format=format)

        with transaction.atomic():
            format = Format.objects.create()
            self.assertRaises(IntegrityError, Assignment.objects.create, points_possible=-0.001, format=format)

        format = Format.objects.create()
        Assignment.objects.create(points_possible=0, format=format)

    def test_create_assignment(self):
        lti_params = {**self.create_params, **{'lti_id': 'new_lti_id'}}
        resp = api.create(self, 'assignments', params=lti_params, user=self.teacher)['assignment']
        assignment = Assignment.objects.get(pk=resp['id'])
        assert assignment.active_lti_id in assignment.lti_id_set, 'lti id should be set in the lti_id_set as well'
        assert assignment.active_lti_id in assignment.courses.first().assignment_lti_id_set, \
            'lti id should be set in the course assignment_lti_id_set as well'

        # Test creation with default params is not a group assignment
        assignment = api.create(self, 'assignments', params=self.create_params, user=self.teacher)['assignment']
        assert 'is_group_assignment' in assignment and not assignment['is_group_assignment'], \
            'Default assignment should be individual'

        # Test required fields
        api.create(self, 'assignments', params={}, user=self.teacher, status=400)
        api.create(self, 'assignments', params={'name': 'test'}, user=self.teacher, status=400)
        api.create(self, 'assignments', params={'points_possible': 5}, user=self.teacher, status=400)

        # Test creation of group assignment
        params = {
            'name': 'test',
            'description': 'test_description',
            'points_possible': 10,
            'course_id': self.course.pk,
            'is_group_assignment': True,
            'remove_grade_upon_leaving_group': True,
        }
        assignment = api.create(self, 'assignments', params=params, user=self.teacher)['assignment']
        assert 'is_group_assignment' in assignment and assignment['is_group_assignment'], \
            'Assignment with group size should be a group assignment'
        assert 'remove_grade_upon_leaving_group' in assignment and assignment['remove_grade_upon_leaving_group'], \
            'Assignment should keep settings on creation'

        old_count = Journal.all_objects.count()
        params['is_published'] = True
        params['is_group_assignment'] = False
        api.create(self, 'assignments', params=params, user=self.teacher)
        assert Journal.all_objects.count() == old_count + 2, '2 new journals should be created (teacher & student)'

        old_count = Journal.all_objects.count()
        params['is_group_assignment'] = True
        factory.Participation(course=self.course, user=factory.Student())
        assert Journal.all_objects.count() == old_count + 1, 'After joining a course, 1 journal needs to be added'

        old_count = Journal.all_objects.count()
        api.create(self, 'assignments', params=params, user=self.teacher)
        assert Journal.all_objects.count() == old_count, 'No journals should be created when it is a group journal'

        params['lti_id'] = 'random_lti_id_salkdjfhas'
        api.create(self, 'assignments', params=params, user=self.teacher)
        self.course.refresh_from_db()
        assert 'random_lti_id_salkdjfhas' in self.course.assignment_lti_id_set

        params = {**self.create_params, **{'description': ''}}
        resp = api.create(self, 'assignments', params=params, user=self.teacher)['assignment']
        assert resp['description'] == '', 'It should be possible to create an assignment without a description.'

    def test_get_assignment_stats(self):
        unrelated_student = factory.Student()
        assignment = factory.Assignment(courses=[self.course])
        group = factory.Group(course=self.course)
        n_journals = 2
        n_entries = 10
        n_graded_entries = 4
        n_jirs = 1
        n_ungraded_entries = n_entries - n_graded_entries

        api.get(self, 'assignments', params={'pk': assignment.pk}, user=unrelated_student, status=403)

        # Add journals with some graded but unpublished entries
        for _ in range(n_journals):
            journal = factory.Journal(assignment=assignment, entries__n=n_ungraded_entries)
            factory.JournalImportRequest(target=journal)
            for i in range(n_graded_entries):
                entry = factory.UnlimitedEntry(
                    node__journal=journal, grade__grade=5, grade__published=False, grade__author=self.teacher)

        student = journal.authors.first().user
        resp = api.get(self, 'assignments', params={'pk': assignment.pk, 'course_id': self.course.pk},
                       user=student)['assignment']
        assert resp['journal'] is not None, 'Response should include student serializer'
        assert 'needs_marking' not in resp['stats'], 'Student serializer should not include grading stats'
        assert 'import_requests' not in resp['stats'], 'Student serializer should not import request stats'
        assert 'unpublished' not in resp['stats'], 'Student serializer should not include grading stats'
        assert 'needs_marking_own_groups' not in resp['stats'], 'Student serializer should not include grading stats'
        assert 'unpublished_own_groups' not in resp['stats'], 'Student serializer should not import request stats'
        assert 'import_requests_own_groups' not in resp['stats'], 'Student serializer should not include grading stats'
        assert resp['stats']['average_points'] == 0, \
            'Student serializer should not reveal stats about unpublished grades'

        resp = api.get(self, 'assignments', params={'pk': assignment.pk, 'course_id': self.course.pk},
                       user=self.teacher)['assignment']
        assert resp['journals'] is not None, 'Response should include teacher serializer'
        assert resp['stats']['needs_marking'] == n_ungraded_entries * n_journals, 'entries do not have a grade yet'
        assert resp['stats']['unpublished'] == n_graded_entries * n_journals, 'grades still need to be published'
        assert resp['stats']['import_requests'] == n_jirs * n_journals
        assert resp['stats']['needs_marking_own_groups'] == 0, \
            'Own group stats should be empty without being member of a group'
        assert resp['stats']['unpublished_own_groups'] == 0, \
            'Own group stats should be empty without being member of a group'
        assert resp['stats']['import_requests_own_groups'] == 0, 'No pending import request of own group'

        # Add student and teacher to the same group
        student.participation_set.first().groups.add(group)
        self.teacher.participation_set.get(course=self.course).groups.add(group)

        resp = api.get(self, 'assignments', params={'pk': assignment.pk, 'course_id': self.course.pk},
                       user=self.teacher)['assignment']
        assert resp['stats']['needs_marking'] == n_ungraded_entries * n_journals, \
            'Non-group stats shall remain the same when in a group'
        assert resp['stats']['unpublished'] == n_graded_entries * n_journals, \
            'Non-group stats shall remain the same when in a group'
        assert resp['stats']['import_requests'] == n_jirs * n_journals, \
            'Non group JIR stats shall remain the same when in a group'
        assert resp['stats']['needs_marking_own_groups'] == n_ungraded_entries, \
            'Entries in own group do not have a grade yet'
        assert resp['stats']['unpublished_own_groups'] == n_graded_entries, \
            'Grades in own group still need to be published'
        assert resp['stats']['import_requests_own_groups'] == n_jirs, 'Only one import request exists'

        # Grade all entries for the assignment and publish grades
        for entry in Entry.objects.filter(node__journal__assignment=assignment):
            api.create(self, 'grades', params={'entry_id': entry.pk, 'grade': 5, 'published': True},
                       user=self.teacher)
        # Decline all JIRs
        for jir in JournalImportRequest.objects.filter(target__assignment=assignment):
            api.patch(self, 'journal_import_request',
                      params={'pk': jir.pk, 'jir_action': JournalImportRequest.DECLINED}, user=self.teacher)

        resp = api.get(self, 'assignments', params={'pk': assignment.pk, 'course_id': self.course.pk},
                       user=self.teacher)['assignment']
        assert resp['stats']['needs_marking'] == 0, 'All entries are graded and grades are published'
        assert resp['stats']['unpublished'] == 0, 'All entries are graded and grades are published'
        assert resp['stats']['import_requests'] == 0
        assert resp['stats']['needs_marking_own_groups'] == 0, 'All entries are graded and grades are published'
        assert resp['stats']['unpublished_own_groups'] == 0, 'All entries are graded and grades are published'
        assert resp['stats']['import_requests_own_groups'] == 0

        # Check group assignment
        group_assignment = factory.Assignment(group_assignment=True)
        student = factory.AssignmentParticipation(assignment=group_assignment).user
        api.get(self, 'assignments', params={'pk': group_assignment.pk}, user=student)

    def test_get_assignment_with_given_course(self):
        assignment = factory.Assignment()
        course1 = assignment.courses.first()
        factory.Journal(assignment=assignment)
        course2 = factory.Course()
        assignment.courses.add(course2)
        factory.Journal(assignment=assignment)
        assignment = AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get()
        result = AssignmentSerializer(assignment, context={
            'user': course2.author, 'course': course2, 'serialize_journals': True}).data
        assert len(result['journals']) == 1, 'Course2 is supplied, only journals from that course should appear (1)'

        result = AssignmentSerializer(assignment, context={
            'user': course2.author, 'serialize_journals': True}).data
        assert not result['journals'], 'No course supplied should also return no journals'

        result = AssignmentSerializer(assignment, context={
            'user': course1.author, 'course': course1, 'serialize_journals': True}).data
        assert len(result['journals']) == 2, 'Course1 is supplied, only journals from that course should appear (2)'

        # Should not work when user is not in supplied course
        with pytest.raises(VLEParticipationError):
            result = AssignmentSerializer(assignment, context={
                'user': course2.author, 'course': course1, 'serialize_journals': True}).data

    def test_assigned_assignment(self):
        assignment = factory.Assignment()
        group = factory.Group(course=assignment.courses.first())
        assignment.assigned_groups.add(group)
        journal = factory.Journal(assignment=assignment)
        journal_not_viewable = factory.Journal(assignment=assignment)
        p = Participation.objects.get(user=journal.authors.first().user, course=assignment.courses.first())
        p.groups.add(group)
        assert not journal_not_viewable.authors.first().user.can_view(assignment)
        assert journal.authors.first().user.can_view(assignment)

    def test_list(self):
        course2 = factory.Course(author=self.teacher)
        factory.Assignment(courses=[self.course])
        factory.Assignment(courses=[self.course, course2])
        assignment = factory.Assignment()

        resp = api.get(self, 'assignments', params={'course_id': self.course.pk}, user=self.teacher)['assignments']
        assert len(resp) == 2, 'All connected courses should be returned'
        resp = api.get(self, 'assignments', params={'course_id': course2.pk}, user=self.teacher)['assignments']
        assert len(resp) == 1, 'Not connected courses should not be returned'

        # Connected assignment
        course = assignment.courses.first()
        factory.Participation(user=self.teacher, course=course)
        # Not connected assignment
        factory.Assignment()

        resp = api.get(self, 'assignments', user=self.teacher)['assignments']
        assert len(resp) == 3, 'Without a course supplied, it should return all assignments connected to user'

    def test_update_assignment(self):
        assignment = factory.Assignment(is_published=True)
        teacher = assignment.author
        journal = factory.Journal(entries__n=0, assignment=assignment)
        student = journal.author

        update_params = factory.AssignmentUpdateParams(assignment=assignment)

        def test_update_permission():
            # Assignment update is locked behind 'can_edit_assignment'
            with mock.patch('VLE.models.User.check_permission') as check_permission_mock:
                api.update(self, 'assignments', params=update_params, user=teacher)
                check_permission_mock.assert_called_with('can_edit_assignment', assignment)
            api.update(self, 'assignments', params=update_params, user=student, status=403)

        def test_update_is_published():
            unpublished = deepcopy(update_params)
            unpublished['is_published'] = False
            resp = api.update(self, 'assignments', params=unpublished, user=teacher)['assignment']
            assert not resp['is_published'], 'It is possible to unpublish an assignment without any entries.'

            # So we add an entry and check if it is no longer possible to unpublish
            assignment.is_published = True
            assignment.save()
            entry = factory.UnlimitedEntry(node__journal__assignment=assignment)
            api.update(self, 'assignments', params=unpublished, user=teacher, status=400)
            entry.delete()  # Cleanup

        def test_update_assignment_type():
            group_assignment = deepcopy(update_params)
            group_assignment['is_group_assignment'] = True
            resp = api.update(self, 'assignments', params=group_assignment, user=teacher)['assignment']
            assert resp['is_group_assignment'], \
                '''It is possible to switch an assignment's type if there are no entries created yet.'''
            assert not Journal.objects.filter(node__journal__assignment=assignment).exists(), \
                'All journals should be deleted after type change'

            # Afte adding an entry it should no longer be possible to change the assignment's type
            entry = factory.UnlimitedEntry(node__journal__assignment=assignment)
            individual_assignment = deepcopy(update_params)
            api.update(self, 'assignments', params=individual_assignment, user=teacher, status=400)
            entry.delete()  # Cleanup

        def test_script_sanitization():
            script_in_description = deepcopy(update_params)
            script_in_description['description'] = '<script>alert("asdf")</script>Rest'

            resp = api.update(self, 'assignments', params=script_in_description, user=teacher)['assignment']
            assert resp['description'] != script_in_description['description']

        test_update_permission()
        test_update_is_published()
        test_update_assignment_type()
        test_script_sanitization()

    def test_update_assignment_assign_to(self):
        assignment = factory.Assignment()
        course = assignment.courses.first()
        teacher = assignment.author
        update_params = factory.AssignmentUpdateParams(assignment=assignment)

        def check_groups(groups, status=200):
            api.update(self, 'assignments', params=update_params, user=teacher, status=status)

            if status == 200:
                assignment.refresh_from_db()

                assert assignment.assigned_groups.count() == len(groups), 'Assigned group amount should be correct'

                for group in Group.objects.all():
                    if group in groups:
                        assert assignment.assigned_groups.filter(pk=group.pk).exists(), \
                            'Group should be in assigned groups'
                    else:
                        assert not assignment.assigned_groups.filter(pk=group.pk).exists(), \
                            'Group should not be in assigned groups'

        group = factory.Group(course=course)
        update_params['assigned_groups'] = [
            {'id': group.pk},
        ]
        update_params['course_id'] = course.pk
        check_groups([group])

        # Test groups from other courses are not added when course_id is wrong
        course2 = factory.Course()
        assignment.add_course(course2)
        group2 = factory.Group(course=course2)
        update_params['assigned_groups'] = [
            {'id': group.pk},
            {'id': group2.pk},
        ]
        update_params['course_id'] = course.pk
        check_groups([group])

        # Course id has to be related to the provided assignment
        unrelated_course = factory.Course()
        update_params['course_id'] = unrelated_course.pk
        api.update(self, 'assignments', params={'pk': assignment.pk, **update_params}, user=teacher, status=400)
        update_params['course_id'] = course.pk

        # Unrelated groups cannot be assigned to
        unrelated_group = factory.Group(course=unrelated_course)
        update_params['assigned_groups'] = [
            {'id': group.pk},
            {'id': unrelated_group.pk}
        ]
        check_groups([group])

        # Test group gets added when other course is supplied, also check if other group does not get removed
        update_params['assigned_groups'] = [
            {'id': group2.pk},
        ]
        update_params['course_id'] = course2.pk
        check_groups([group, group2])

        # Test if only groups from supplied course get removed
        update_params['assigned_groups'] = []
        update_params['course_id'] = course2.pk
        check_groups([group])

    def test_delete_assignment(self):
        teach_course = factory.Course(author=self.teacher)
        other_course = factory.Course()

        assignment = factory.Assignment(
            courses=[self.course, teach_course, other_course], make_author_teacher_in_all_courses=False)

        # Test no course specified
        api.delete(self, 'assignments', params={'pk': assignment.pk}, user=self.teacher, status=400)

        # Test normal removal
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': teach_course.id}, user=self.teacher)
        assert 'removed' in resp['description'] and 'deleted' not in resp['description'], \
            'The assignment should be removed from the course, not deleted'

        # Test if only admins can delete assignments they are not part of
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': other_course.id}, user=self.teacher, status=403)
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': other_course.id}, user=self.teacher, status=403)
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': other_course.id}, user=self.admin, status=200)

        # Test delete
        resp = api.delete(self, 'assignments',
                          params={'pk': assignment.pk, 'course_id': self.course.id}, user=self.teacher)
        assert 'removed' not in resp['description'] and 'deleted' in resp['description'], \
            'The assignment should be deleted from the course, not removed'

    def test_lti_delete(self):
        assignment = factory.LtiAssignment()
        course = assignment.courses.first()
        assert assignment.active_lti_id in course.assignment_lti_id_set, \
            'assignment lti_id should be in assignment_lti_id_set of course before anything is deleted'
        # Test if deletion is possible to delete assignment if it has only one lti id
        api.delete(self, 'assignments', params={'pk': assignment.pk, 'course_id': course.pk}, user=self.admin)
        assert assignment.active_lti_id not in Course.objects.get(pk=course.pk).assignment_lti_id_set, \
            'assignment lti_id should get removed from the assignment_lti_id_set from the course'
        assignment = factory.LtiAssignment()
        course = assignment.courses.first()
        course2 = factory.LtiCourse()
        assignment.courses.add(course2)
        assignment.lti_id_set.append('second' + assignment.active_lti_id)
        assignment.save()
        # Test is deletion is not possible from connected LTI course
        api.delete(
            self, 'assignments', params={'pk': assignment.pk, 'course_id': course.pk}, user=self.admin, status=400)
        # Test is deletion is possible from other course
        api.delete(
            self, 'assignments', params={'pk': assignment.pk, 'course_id': course2.pk}, user=self.admin)

    def test_importable(self):
        teacher = self.teacher
        course = factory.Course(author=teacher)
        assignment = factory.Assignment(courses=[course])

        # Check importable return values
        resp = api.get(self, 'assignments/importable', user=teacher)['data']
        assert resp[0]['assignments'][0]['id'] == assignment.pk, 'importable assignment should be displayed'
        assert len(resp[0]['assignments']) == 1
        assert resp[0]['course']['id'] == course.id, 'importable course should be displayed'

        student = factory.Journal(assignment=assignment).authors.first().user
        data = api.get(self, 'assignments/importable', user=student, status=200)['data']
        assert len(data) == 0, 'A student should not be able to see any importable assignments'

        r = Participation.objects.get(course=course, user=teacher).role
        r.can_edit_assignment = False
        r.save()
        data = api.get(self, 'assignments/importable', user=teacher)['data']
        assert len(data) == 0, 'A teacher requires can_edit_assignment to see importable assignments.'

    def test_assignment_import(self):
        start2018_2019 = datetime.datetime(year=2018, month=9, day=1)
        start2019_2020 = datetime.datetime(year=2019, month=9, day=1)
        end2018_2019 = start2019_2020 - relativedelta(days=1)
        end2019_2020 = datetime.datetime(year=2020, month=9, day=1) - relativedelta(days=1)

        teacher = self.teacher
        course = factory.Course(
            author=teacher,
            startdate=start2018_2019,
            enddate=end2019_2020,
        )
        not_import_course = factory.Course()
        source_assignment = factory.Assignment(
            courses=[course, not_import_course],
            unlock_date=start2018_2019,
            due_date=end2018_2019,
            lock_date=end2018_2019,
        )
        source_assignment.active_lti_id = 'some id'
        source_assignment.save()
        source_format = source_assignment.format
        source_progress_node = factory.ProgressPresetNode(
            format=source_format,
            unlock_date=start2018_2019,
            due_date=start2018_2019 + relativedelta(months=6),
            lock_date=start2018_2019 + relativedelta(months=6),
        )
        source_deadline_node = factory.DeadlinePresetNode(
            format=source_format,
            unlock_date=None,
            due_date=start2018_2019 + relativedelta(months=6),
            lock_date=None,
        )

        source_template = factory.Template(format=source_format)
        student = factory.Student()
        # Create student participation and accompanying journal
        factory.Participation(user=student, course=course, role=Role.objects.get(course=course, name='Student'))
        assert Participation.objects.filter(course=course).count() == 2
        source_student_journal = Journal.objects.get(authors__user=student, assignment=source_assignment)
        assert Journal.objects.filter(assignment=source_assignment).count() == 1, \
            'Teacher assignment should not show up in count'
        source_entries = []
        number_of_source_student_journal_entries = 4
        for _ in range(number_of_source_student_journal_entries):
            source_entries.append(
                factory.UnlimitedEntry(template=source_template, node__journal=source_student_journal))

        assert Node.objects.count() == 10, \
            '2 nodes for the presets for teacher and student each, 4 for the student entries'
        assert source_entries[0].node.journal == source_student_journal
        assert Entry.objects.filter(
            node__journal=source_student_journal).count() == number_of_source_student_journal_entries, \
            'Only the entries explicitly created above exist for the source journal'
        assert Journal.objects.filter(assignment=source_assignment).count() == 1, \
            'The source assignment only holds the journals explicitly created above'

        before_source_preset_nodes = PresetNode.objects.filter(format=source_assignment.format)
        assert source_progress_node in before_source_preset_nodes, 'We are working with the correct node and format'
        before_source_templates = Template.objects.filter(format=source_assignment.format)
        before_source_ass_resp = api.get(self, 'assignments', params={'pk': source_assignment.pk}, user=teacher)

        pre_import_format_count = Format.objects.count()
        pre_import_journal_count = Journal.all_objects.count()
        pre_import_entry_count = Entry.objects.count()
        pre_import_node_count = Node.objects.count()
        pre_import_preset_node_count = PresetNode.objects.count()
        resp = api.post(self, 'assignments/{}/copy'.format(source_assignment.pk), params={
                'course_id': course.pk,
                'months_offset': 0,
            }, user=teacher)
        created_assignment = Assignment.objects.get(pk=resp['assignment_id'])
        created_format = created_assignment.format

        assert not created_assignment.is_published, 'Imported assignment should not be published'
        assert pre_import_journal_count == Journal.all_objects.count(), \
            """No journals should not be created before the assignment is published."""
        created_assignment.is_published = True
        created_assignment.save()

        assert pre_import_format_count + 1 == Format.objects.count(), 'One additional format is created'
        assert created_format == Format.objects.last(), 'Last created format should be the new assignment format'
        assert pre_import_journal_count * 2 - 1 == Journal.all_objects.count(), \
            """A journal should be created for each of the existing course users.
               However, old teacher should not get journal"""
        assert pre_import_entry_count == Entry.objects.count(), 'No additional entries are created'
        assert pre_import_node_count + 4 == Node.objects.count(), \
            'Both student and teacher receive nodes for the presets'
        assert pre_import_preset_node_count + 2 == PresetNode.objects.count(), \
            'The progress and preset nodes are imported'
        assert before_source_preset_nodes.count() == PresetNode.objects.filter(
            format=created_assignment.format).count(), 'All preset nodes should be imported along.'
        assert created_assignment.active_lti_id is None, 'Imported assignment should not be linked to LTI'
        assert created_assignment.lti_id_set == [], 'Imported assignment should not be linked to LTI'
        assert created_assignment.courses.count() == 1 and course in created_assignment.courses.all(), \
            'Only the course where we call import from should be part of the created assignment course set'

        resp = api.post(self, 'assignments/{}/copy'.format(source_assignment.pk), params={
                'course_id': course.pk,
                'months_offset': 0,
                'lti_id': 'test'
            }, user=teacher)
        created_assignment = Assignment.objects.get(pk=resp['assignment_id'])
        created_format = created_assignment.format
        assert created_assignment.author == teacher
        assert not created_assignment.is_published, 'Imported assignment should not be published'
        assert created_assignment.active_lti_id == 'test', 'Imported assignment should not be linked to LTI'
        assert created_assignment.lti_id_set == ['test'], 'Imported assignment should not be linked to LTI'

        after_source_preset_nodes = PresetNode.objects.filter(format=source_assignment.format)
        after_source_templates = Template.objects.filter(format=source_assignment.format)
        after_source_ass_resp = api.get(self, 'assignments', params={'pk': source_assignment.pk}, user=teacher)
        created_ass_resp = api.get(self, 'assignments', params={'pk': created_assignment.pk}, user=teacher)

        # Validate that the entire imported response format is unchanged
        before_source_ass_resp['assignment']['courses'] = before_source_ass_resp['assignment']['courses'].sort(
            key=lambda c: c['id'])
        after_source_ass_resp['assignment']['courses'] = after_source_ass_resp['assignment']['courses'].sort(
            key=lambda c: c['id'])
        assert equal_models(before_source_ass_resp, after_source_ass_resp), \
            'Source format should remain unchanged'

        # The check above is extensive, but limited by the serializer, so let us check the db fully.
        assert before_source_preset_nodes.count() == after_source_preset_nodes.count() \
            and before_source_templates.count() == after_source_templates.count(), \
            'Format of the import target should remain unchanged'
        for before_n, after_n in zip(before_source_preset_nodes, after_source_preset_nodes):
            assert equal_models(before_n, after_n), 'Import target preset nodes should remain unchanged'
        for before_t, after_t in zip(before_source_templates, after_source_templates):
            assert equal_models(before_t, after_t), 'Import target templates should remain unchanged'
        assert len(Entry.objects.filter(node__journal=source_student_journal)) == \
            number_of_source_student_journal_entries, 'Old entries should not be removed'

        assert created_assignment.pk == created_ass_resp['assignment']['id'], \
            'The most recently created assignment should be returned.'

        # Validate the import result values without the meddling of the serializer
        created_preset_nodes = PresetNode.objects.filter(format=created_format)
        created_templates = Template.objects.filter(format=created_format)
        assert not source_format.presetnode_set.filter(pk__in=created_preset_nodes).exists(), \
            'No overlap exists between the preset nodes of source and target assignment'
        assert not source_format.template_set.filter(pk__in=created_templates).exists(), \
            'No overlap exists between the templates of source and target assignment'

        assert before_source_preset_nodes.count() == created_preset_nodes.count() \
            and before_source_templates.count() == created_templates.count(), \
            'Format of the import should be equal to the import target'
        ignoring = ['id', 'format', 'forced_template', 'creation_date', 'update_date']
        for before_n, created_n in zip(before_source_preset_nodes, created_preset_nodes):
            assert equal_models(before_n, created_n, ignore_keys=ignoring), 'Import preset nodes should be equal'
        for before_t, created_t in zip(before_source_templates, created_templates):
            assert equal_models(before_t, created_t, ignore_keys=ignoring), 'Import target templates should be equal'

        # Import again, but now update all dates
        resp = api.post(self, 'assignments/{}/copy'.format(source_assignment.pk), params={
                'course_id': course.pk,
                'months_offset': 12,
            }, user=teacher)
        created_assignment = Assignment.objects.get(pk=resp['assignment_id'])
        created_format = created_assignment.format
        created_ass_resp = api.get(self, 'assignments', params={'pk': created_assignment.pk}, user=teacher)

        # The import result values should still be equal apart from the dates
        created_preset_nodes = PresetNode.objects.filter(format=created_format)
        created_templates = Template.objects.filter(format=created_format)
        assert before_source_preset_nodes.count() == created_preset_nodes.count() \
            and before_source_templates.count() == created_templates.count(), \
            'Format of the import should be equal to the import target'
        for before_n, created_n in zip(before_source_preset_nodes, created_preset_nodes):
            assert equal_models(before_n, created_n,
                                ignore_keys=ignoring + ['unlock_date', 'due_date', 'lock_date']), \
                'Import preset nodes should be equal, apart from the moved dates'
        for before_t, created_t in zip(before_source_templates, created_templates):
            assert equal_models(before_t, created_t,
                                ignore_keys=ignoring + ['unlock_date', 'due_date', 'lock_date']), \
                'Import target templates should be equal, apart from the moved dates'

        created_progress_node = created_preset_nodes.filter(type=Node.PROGRESS).first()
        created_deadline_node = created_preset_nodes.filter(type=Node.ENTRYDEADLINE).first()
        assert created_deadline_node.unlock_date is None and created_deadline_node.lock_date is None, \
            'Times which were unset in original should not be changed'
        assert created_deadline_node.due_date.weekday() == source_deadline_node.due_date.weekday() and \
            created_progress_node.unlock_date.weekday() == source_progress_node.unlock_date.weekday() and \
            created_progress_node.due_date.weekday() == source_progress_node.due_date.weekday() and \
            created_progress_node.lock_date.weekday() == source_progress_node.lock_date.weekday() and \
            'Week days should be preserved'
        assert relativedelta(created_deadline_node.due_date, source_deadline_node.due_date).years == 1 and \
            created_deadline_node.due_date.month == source_deadline_node.due_date.month, \
            'Deadline should shift 1 year but otherwise be similar'
        assert relativedelta(created_progress_node.unlock_date, source_progress_node.unlock_date).years == 1 and \
            created_progress_node.unlock_date.month == source_progress_node.unlock_date.month, \
            'Deadline should shift 1 year but otherwise be similar'
        assert relativedelta(created_progress_node.due_date, source_progress_node.due_date).years == 1 and \
            created_progress_node.due_date.month == source_progress_node.due_date.month, \
            'Deadline should shift 1 year but otherwise be similar'
        assert relativedelta(created_progress_node.lock_date, source_progress_node.lock_date).years == 1 and \
            created_progress_node.lock_date.month == source_progress_node.lock_date.month, \
            'Deadline should shift 1 year but otherwise be similar'

    def test_assignment_copy_templates_and_categories(self):
        target_course = factory.Course(author=self.teacher)

        source_course = self.course
        source_assignment = factory.Assignment(courses=[source_course], format__templates=False)
        source_format = source_assignment.format
        source_template = factory.Template(format=source_format, name='Template1', add_fields=[{'type': Field.TEXT}])
        source_template2 = factory.Template(format=source_format, name='Template2', add_fields=[{'type': Field.TEXT}])
        source_category = factory.Category(assignment=source_assignment)
        source_category2 = factory.Category(assignment=source_assignment)
        source_template.categories.add(source_category)
        source_template.categories.add(source_category2)
        source_template2.categories.add(source_category)

        resp = api.post(self, 'assignments/{}/copy'.format(source_assignment.pk), params={
            'course_id': target_course.pk,
            'months_offset': 0,
        }, user=self.teacher)

        assignment_copy = Assignment.objects.get(pk=resp['assignment_id'])
        assert assignment_copy.categories.count() == source_assignment.categories.count()
        assert assignment_copy.format.template_set.count() == source_assignment.format.template_set.count()

        for source_category in source_assignment.categories.all():
            target_category = Category.objects.get(name=source_category.name, assignment=assignment_copy)
            assert equal_models(
                source_category,
                target_category,
                ignore_keys=['id', 'creation_date', 'update_date', 'assignment', 'templates']
            ), 'Category is succesfully copied'
            assert source_category.templates.count() == target_category.templates.count()

            for source_category_template in source_category.templates.all():
                # The copied category is linked to a new template which is equal to the old
                # We use unique templates names to simplify the test
                target_category_template = target_category.templates.get(
                    name=source_category_template.name,
                    preset_only=source_category_template.preset_only,
                    archived=source_category_template.archived,
                    chain__allow_custom_categories=source_category_template.chain.allow_custom_categories,
                )
                for source_field, target_field in zip(
                    source_category_template.field_set.order_by('location'),
                    target_category_template.field_set.order_by('location')
                ):
                    assert equal_models(
                        source_field,
                        target_field,
                        ignore_keys=['id', 'template', 'creation_date', 'update_date']
                    ), 'Of the linked templates the fields are equal'

    def test_assignment_copy_files(self):
        fc_ignore_keys = ['last_edited', 'creation_date', 'update_date', 'id', 'access_id', 'assignment']

        target_course = factory.Course(author=self.teacher)

        # Setup a source assignment with files for all 'assignment level' FileContexts
        # (field description, assignment description, preset node description, preset node attachment,
        # category description)
        source_course = self.course
        source_assignment = factory.Assignment(courses=[source_course], format__templates=False)
        source_format = source_assignment.format

        source_assignment_description_fc = factory.RichTextAssignmentDescriptionFileContext(
            assignment=source_assignment)

        source_template = factory.Template(format=source_format, add_fields=[{'type': Field.TEXT}])
        source_template_field = source_template.field_set.first()
        source_template_field_fc = factory.RichTextFieldDescriptionFileContext(
            assignment=source_assignment, field=source_template_field)

        source_category = factory.Category(assignment=source_assignment)
        source_category_description_fc = factory.RichTextCategoryDescriptionFileContext(category=source_category)

        source_deadline = factory.DeadlinePresetNode(format=source_format, n_rt_files=1, n_att_files=1)
        source_deadline_att_fc = source_deadline.attached_files.first()
        assert source_deadline_att_fc
        source_deadline_description_fc = get_files_from_rich_text(source_deadline.description).first()
        assert source_deadline_description_fc

        # Import the assignment (hopefull sucesfully copying all FileContexts as well)
        resp = api.post(self, 'assignments/{}/copy'.format(source_assignment.pk), params={
            'course_id': target_course.pk,
            'months_offset': 0,
        }, user=self.teacher)

        target_assignment = Assignment.objects.get(pk=resp['assignment_id'])

        # First confirm all files are new copies (instead of just references to fcs of the old assignment)

        # Assignment RT description file is a new (equal) copy
        target_assignment_description_fc = get_files_from_rich_text(target_assignment.description).first()
        check_equality_of_imported_file_context(
            source_assignment_description_fc, target_assignment_description_fc, fc_ignore_keys)

        # Template RT field description file is a new (equal) copy
        target_template = target_assignment.format.template_set.get(name=source_template.name)
        target_template_field = target_template.field_set.first()
        target_template_field_fc = get_files_from_rich_text(target_template_field.description).first()
        check_equality_of_imported_file_context(source_template_field_fc, target_template_field_fc, fc_ignore_keys)

        # Category RT description file is a new (equal) copy
        category_ignore_keys = ['last_edited', 'creation_date', 'update_date', 'id', 'access_id', 'category']
        target_category = target_assignment.categories.get(name=source_category.name)
        target_category_description_fc = get_files_from_rich_text(target_category.description).first()
        check_equality_of_imported_file_context(
            source_category_description_fc, target_category_description_fc, category_ignore_keys)

        # Deadline attached file is a new (equal) copy
        target_deadline = target_assignment.format.presetnode_set.get(display_name=source_deadline.display_name)
        target_deadline_att_fc = target_deadline.attached_files.first()
        check_equality_of_imported_file_context(source_deadline_att_fc, target_deadline_att_fc, fc_ignore_keys)
        # Deadline RT description file is a new (equal) copy
        target_deadline_description_fc = get_files_from_rich_text(target_deadline.description).first()
        check_equality_of_imported_file_context(
            source_deadline_description_fc, target_deadline_description_fc, fc_ignore_keys)

        # Now we remove the files from the source assignment, this should not change anything for the target assignment
        source_assignment.description = ''
        source_assignment.save()

        source_template_field.description = ''
        source_template_field.save()

        source_category.description = ''
        source_category.save()

        source_deadline.attached_files.remove(source_deadline_att_fc)
        source_deadline.description = ''
        source_deadline.save()

        # Cleanup should not remove any of the underlying FC's as they are still referenced in the target assignment
        cleanup.remove_unused_files(datetime.datetime.now())

        # Source files should be cleaned
        assert not FileContext.objects.filter(pk=source_assignment_description_fc.pk).exists()
        assert not FileContext.objects.filter(pk=source_template_field_fc.pk).exists()
        assert not FileContext.objects.filter(pk=source_category_description_fc.pk).exists()
        assert not FileContext.objects.filter(pk=source_deadline_att_fc.pk).exists()
        assert not FileContext.objects.filter(pk=source_deadline_description_fc.pk).exists()

        # Target files should remain
        assert FileContext.objects.filter(pk=target_assignment_description_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_template_field_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_category_description_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_deadline_att_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_deadline_description_fc.pk).exists()

        # Deleting the source assignment should not remove any of the copied FC's
        source_assignment.delete()
        assert FileContext.objects.filter(pk=target_assignment_description_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_template_field_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_category_description_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_deadline_att_fc.pk).exists()
        assert FileContext.objects.filter(pk=target_deadline_description_fc.pk).exists()

        # Removing the references to the FCs in the target assignment SHOULD delete the FCs after cleanup
        target_assignment.description = ''
        target_assignment.save()

        target_template_field.description = ''
        target_template_field.save()

        target_category.description = ''
        target_category.save()

        target_deadline.attached_files.remove(target_deadline_att_fc)
        target_deadline.description = ''
        target_deadline.save()

        # With the references removed, cleanup should actually remove all files
        cleanup.remove_unused_files(datetime.datetime.now())
        assert not FileContext.objects.filter(pk=target_assignment_description_fc.pk).exists()
        assert not FileContext.objects.filter(pk=target_template_field_fc.pk).exists()
        assert not FileContext.objects.filter(pk=target_category_description_fc.pk).exists()
        assert not FileContext.objects.filter(pk=target_deadline_att_fc.pk).exists()
        assert not FileContext.objects.filter(pk=target_deadline_description_fc.pk).exists()

    def test_upcoming_basic(self):
        course = factory.Course()
        teacher = course.author
        factory.Assignment(courses=[course])

        # We create another course, any assignments linked to this course should not be returned
        course2 = factory.Course(author=teacher)
        factory.Assignment(courses=[course2])

        def test_upcoming_for_a_specific_course(self):
            resp = api.get(self, 'assignments/upcoming', params={'course_id': course.pk}, user=teacher)['upcoming']
            assert len(resp) == 1, 'Only information regarding the provided course_id is returned'
            resp = resp[0]

            assert resp['course']['name'] == course.name
            assert resp['course']['abbreviation'] == course.abbreviation
            assert 'stats' in resp, 'Stats are required to displayed stats specific to ones own and all groups'

        def test_upcoming_without_course_id(self):
            resp = api.get(self, 'assignments/upcoming', user=teacher)['upcoming']
            assert len(resp) == 2, 'Without a course id supplied, both assignments should be returned'
            assert all([len(r['courses']) == 1 for r in resp]), 'Each assignment is linked to a single course'

        def test_locked_assignments_should_not_be_serialized(self):
            assignment3 = factory.Assignment(
                courses=[course], author=teacher, due_date=timezone.now(), lock_date=timezone.now())
            resp = api.get(self, 'assignments/upcoming', user=teacher)['upcoming']
            assert len(resp) == 2 and not any([ass['course']['name'] == assignment3.name for ass in resp]), \
                'The locked assignment should not be serialized'

        def test_upcoming_for_assignment_with_multiple_courses(self):
            course = factory.Course()
            course2 = factory.Course()
            factory.Assignment(courses=[course, course2])

            resp = api.get(self, 'assignments/upcoming', user=course.author)['upcoming']
            abbrs = [course.abbreviation, course2.abbreviation]
            assert len(resp) == 1 and len(resp[0]['courses']) == 2, 'One assignment linked to two courses'
            assert all([c['abbreviation'] in abbrs for c in resp[0]['courses']]), \
                'All the assignment\'s courses\' abbreviations are required for deadline display'

        test_upcoming_for_a_specific_course(self)
        test_upcoming_without_course_id(self)
        test_locked_assignments_should_not_be_serialized(self)
        test_upcoming_for_assignment_with_multiple_courses(self)

    def test_upcoming_assignment_group_stats_with_shared_assignments(self):
        def add_student_to_course_and_group(user, group):
            p = factory.Participation(user=user, course=group.course, role=group.course.role_set.get(name='Student'))
            p.groups.add(group)

        # Setup assignment structure

        pav1 = factory.Course(name='PAV1')
        gr_pav1 = factory.Group(course=pav1)

        # Add teacher to gr_pav1, and Student1
        teacher_both_groups = pav1.author
        Participation.objects.get(course=pav1, user=teacher_both_groups).groups.add(gr_pav1)
        stu_in_gr_pav1 = factory.Student(full_name='Student in group PAV1')
        add_student_to_course_and_group(stu_in_gr_pav1, gr_pav1)
        student_ungrouped_in_pav1 = factory.Student(full_name='Student ungrouped in group PAV1')
        factory.Participation(user=student_ungrouped_in_pav1, course=pav1, role=pav1.role_set.get(name='Student'))

        pav2 = factory.Course(name='PAV2', author=teacher_both_groups)
        gr_pav2 = factory.Group(course=pav2)

        # Add teacher to gr_pav2, TA and Student2
        Participation.objects.get(course=pav2, user=teacher_both_groups).groups.add(gr_pav2)
        ta_only_in_gr_pav2 = factory.Student(full_name='Ta in group PAV2')
        ta_role = pav2.role_set.get(name='TA')
        ta_role.can_manage_journal_import_requests = True
        ta_role.save()
        factory.Participation(
            course=pav2, user=ta_only_in_gr_pav2, role=ta_role).groups.add(gr_pav2)
        stu_in_gr_pav2 = factory.Student(full_name='Student in group PAV2')
        add_student_to_course_and_group(stu_in_gr_pav2, gr_pav2)
        # Add an ungrouped student to PAV2
        student_ungrouped_in_pav2 = factory.Student(full_name='Student ungrouped in group PAV2')
        factory.Participation(user=student_ungrouped_in_pav2, course=pav2, role=pav2.role_set.get(name='Student'))

        logboek = factory.Assignment(courses=[pav1, pav2], name='Logboek', format__templates=[{'type': Field.TEXT}])
        journal_stu_in_gr_pav1 = factory.Journal(ap__user=stu_in_gr_pav1, assignment=logboek, entries__n=0)
        journal_stu_in_gr_pav2 = factory.Journal(ap__user=stu_in_gr_pav2, assignment=logboek, entries__n=0)
        journal_stu_ungrouped_pav1 = factory.Journal(
            ap__user=student_ungrouped_in_pav1, assignment=logboek, entries__n=0)
        journal_stu_ungrouped_pav2 = factory.Journal(
            ap__user=student_ungrouped_in_pav2, assignment=logboek, entries__n=0)

        # End structure, validate grouping of users

        all_users = [stu_in_gr_pav1, student_ungrouped_in_pav1, stu_in_gr_pav2, student_ungrouped_in_pav2]
        assert Journal.objects.filter(assignment=logboek).count() == len(all_users)
        assert not Journal.objects.exclude(authors__user__in=all_users).exists()
        all_users = logboek.assignmentparticipation_set.filter(
            journal__in=Journal.objects.filter(assignment=logboek)).values('user')

        pav1_users = pav1.participation_set.filter(role__name='Student').values('user')

        gr_pav1_users = [stu_in_gr_pav1]
        assert gr_pav1.participation_set.filter(role__name='Student').count() == len(gr_pav1_users)
        assert not gr_pav1.participation_set.filter(role__name='Student').values(
            'user').exclude(user__in=gr_pav1_users).exists()
        gr_pav1_users = gr_pav1.participation_set.filter(role__name='Student').values('user')

        pav2_users = pav2.participation_set.filter(role__name='Student').values('user')

        gr_pav2_users = [stu_in_gr_pav2]
        assert gr_pav2.participation_set.filter(role__name='Student').count() == len(gr_pav2_users)
        assert not gr_pav2.participation_set.filter(role__name='Student').values(
            'user').exclude(user__in=gr_pav2_users).exists()
        gr_pav2_users = gr_pav2.participation_set.filter(role__name='Student').values('user')

        def test_stat_utils(self):
            def compare_p_user_values(a, b, msg=''):
                assert set(a.values_list('pk', flat=True).distinct()) \
                    == set(b.values_list('user', flat=True).distinct()), msg

            # Assignment generic teacher stats
            teacher_logboek_stats = stats_utils.get_user_lists_with_scopes(logboek, teacher_both_groups)
            compare_p_user_values(
                teacher_logboek_stats['all'], all_users, 'Teacher is part of all courses so all users are of interest')
            compare_p_user_values(teacher_logboek_stats['own'], gr_pav1_users.union(gr_pav2_users).order_by('user__pk'),
                                  'Teacher is part of all groups so all grouped users are of interest')
            # PAV1 specific teacher stats
            teacher_pav1_stats = stats_utils.get_user_lists_with_scopes(logboek, teacher_both_groups, course=pav1)
            compare_p_user_values(
                teacher_pav1_stats['all'], pav1_users, '''Despite teacher being part of all courses, when evaluating
                from the perspective of pav1, all should yield only pav1 users part of logboek''')
            compare_p_user_values(teacher_pav1_stats['own'], gr_pav1_users,
                                  '''Own should only yield a subset of all's users which are part of the pav1 groups
                                     teacher is a member of''')
            # PAV2 specific teacher stats
            teacher_pav2_stats = stats_utils.get_user_lists_with_scopes(logboek, teacher_both_groups, course=pav2)
            compare_p_user_values(
                teacher_pav2_stats['all'], pav2_users, '''Despite teacher being part of all courses, when evaluating
                from the perspective of pav2, all should yield only pav2 users part of logboek''')
            compare_p_user_values(teacher_pav2_stats['own'], gr_pav2_users,
                                  '''Own should only yield a subset of all's users which are part of the pav2 groups
                                     teacher is a member of''')

            # Assignment generic ta_only_in_gr_pav2 stats
            ta_logboek_stats = stats_utils.get_user_lists_with_scopes(logboek, ta_only_in_gr_pav2)
            compare_p_user_values(
                ta_logboek_stats['all'], pav2_users, 'TA is only part of pav2 so all should only yields those users')
            compare_p_user_values(ta_logboek_stats['own'], gr_pav2_users,
                                  'TA is only part of a group in pav2, so own should only yield those users')
            # PAV1 specific ta_only_in_gr_pav2 stats
            ta_logboek_stats = stats_utils.get_user_lists_with_scopes(logboek, ta_only_in_gr_pav2, course=pav1)
            assert not ta_logboek_stats['all'].exists(), 'TA is not a member of PAV1 so results for PAV1 specific'
            assert not ta_logboek_stats['own'].exists(), 'TA is not a member of PAV1 so results for PAV1 specific'
            # PAV2 specific ta_only_in_gr_pav2 stats
            ta_logboek_stats = stats_utils.get_user_lists_with_scopes(logboek, ta_only_in_gr_pav2, course=pav2)
            compare_p_user_values(
                ta_logboek_stats['all'], pav2_users, 'TA is only part of pav2 so all should only yields those users')
            compare_p_user_values(ta_logboek_stats['own'], gr_pav2_users,
                                  'TA is only part of a group in pav2, so own should only yield those users')

        def test_returned_stats(self):
            # Setup stuff to do for PAV1
            ungrouped_pav1_needs_marking = 7
            ungrouped_pav1_outstanding_jirs = 5
            for _ in range(ungrouped_pav1_needs_marking):
                factory.UnlimitedEntry(node__journal=journal_stu_ungrouped_pav1)
            for _ in range(ungrouped_pav1_outstanding_jirs):
                factory.JournalImportRequest(target=journal_stu_ungrouped_pav1, author=student_ungrouped_in_pav1)

            gr_pav1_needs_marking = 3
            gr_pav1_outstanding_jirs = 2
            # Group pav 1 should yield 3 needs marking, 1 jir to approve
            for _ in range(gr_pav1_needs_marking):
                factory.UnlimitedEntry(node__journal=journal_stu_in_gr_pav1)
            for _ in range(gr_pav1_outstanding_jirs):
                factory.JournalImportRequest(target=journal_stu_in_gr_pav1, author=stu_in_gr_pav1)

            pav1_needs_marking = ungrouped_pav1_needs_marking + gr_pav1_needs_marking
            pav1_oustanding_jirs = ungrouped_pav1_outstanding_jirs + gr_pav1_outstanding_jirs

            # Setup stuff to do for PAV2
            ungrouped_pav2_needs_marking = 13
            ungrouped_pav2_outstanding_jirs = 3
            for _ in range(ungrouped_pav2_needs_marking):
                factory.UnlimitedEntry(node__journal=journal_stu_ungrouped_pav2)
            for _ in range(ungrouped_pav2_outstanding_jirs):
                factory.JournalImportRequest(target=journal_stu_ungrouped_pav2, author=student_ungrouped_in_pav2)

            gr_pav2_needs_marking = 5
            gr_pav2_outstanding_jirs = 0
            # Group pav 2 shield yield 5 entries need marking
            for _ in range(gr_pav2_needs_marking):
                factory.UnlimitedEntry(node__journal=journal_stu_in_gr_pav2)
            for _ in range(gr_pav2_outstanding_jirs):
                factory.JournalImportRequest(target=journal_stu_in_gr_pav2, author=stu_in_gr_pav2)

            pav2_needs_marking = ungrouped_pav2_needs_marking + gr_pav2_needs_marking
            pav2_outstanding_jirs = ungrouped_pav2_outstanding_jirs + gr_pav2_outstanding_jirs

            all_needs_marking = pav1_needs_marking + pav2_needs_marking
            all_outstanding_jirs = pav1_oustanding_jirs + pav2_outstanding_jirs

            api_path = 'assignments/upcoming'
            # Teacher assingment specific upcoming
            stats = api.get(self, api_path, user=teacher_both_groups)['upcoming'][0]['stats']
            assert stats['needs_marking'] == all_needs_marking
            assert stats['needs_marking_own_groups'] == gr_pav1_needs_marking + gr_pav2_needs_marking
            assert stats['import_requests'] == all_outstanding_jirs
            assert stats['import_requests_own_groups'] == gr_pav1_outstanding_jirs + gr_pav2_outstanding_jirs
            # Teacher pav1 specific upcoming
            stats = api.get(
                self, api_path, params={'course_id': pav1.pk}, user=teacher_both_groups)['upcoming'][0]['stats']
            assert stats['needs_marking'] == pav1_needs_marking
            assert stats['needs_marking_own_groups'] == gr_pav1_needs_marking
            assert stats['import_requests'] == pav1_oustanding_jirs
            assert stats['import_requests_own_groups'] == gr_pav1_outstanding_jirs
            # Teacher pav2 specific upcoming
            stats = api.get(
                self, api_path, params={'course_id': pav2.pk}, user=teacher_both_groups)['upcoming'][0]['stats']
            assert stats['needs_marking'] == pav2_needs_marking
            assert stats['needs_marking_own_groups'] == gr_pav2_needs_marking
            assert stats['import_requests'] == pav2_outstanding_jirs
            assert stats['import_requests_own_groups'] == gr_pav2_outstanding_jirs

            # ta_only_in_gr_pav2 assignment specific upcoming
            stats = api.get(self, api_path, user=ta_only_in_gr_pav2)['upcoming'][0]['stats']
            assert stats['needs_marking'] == pav2_needs_marking
            assert stats['needs_marking_own_groups'] == gr_pav2_needs_marking
            assert stats['import_requests'] == pav2_outstanding_jirs
            assert stats['import_requests_own_groups'] == gr_pav2_outstanding_jirs
            # ta_only_in_gr_pav2 pav2 specific upcoming
            stats = api.get(
                self, api_path, params={'course_id': pav2.pk}, user=ta_only_in_gr_pav2)['upcoming'][0]['stats']
            assert stats['needs_marking'] == pav2_needs_marking
            assert stats['needs_marking_own_groups'] == gr_pav2_needs_marking
            assert stats['import_requests'] == pav2_outstanding_jirs
            assert stats['import_requests_own_groups'] == gr_pav2_outstanding_jirs

        def test_jir_stats_permission_serialization(self):
            ta_role.can_manage_journal_import_requests = False
            ta_role.save()

            stats = api.get(self, 'assignments/upcoming', user=ta_only_in_gr_pav2)['upcoming'][0]['stats']
            assert 'import_requests' not in stats
            assert 'import_requests_own_groups' not in stats

        test_stat_utils(self)
        test_returned_stats(self)
        test_jir_stats_permission_serialization(self)

    def test_get_all_users(self):
        c1 = factory.Course()
        c2 = factory.Course()
        c1p1 = factory.Participation(course=c1).user.pk
        c1p2 = factory.Participation(course=c1).user.pk
        c2p1 = factory.Participation(course=c2).user.pk
        both = self.teacher
        a = factory.Assignment(courses=[c1, c2], author=both)
        c1set = [c1p1, c1p2, c1.author.pk, both.pk]
        c2set = [c2p1, c2.author.pk, both.pk]

        assert set(c1set + c2set) == set(a.get_all_users(journals_only=False).values_list('pk', flat=True)), \
            'When no parameters are set, all users should be retrieved'
        assert set(c1set) == set(a.get_all_users(
            courses=Course.objects.filter(pk=c1.pk), journals_only=False).values_list('pk', flat=True)), \
            'When courses are set, only get the users from those courses'
        assert set(c2set) == set(a.get_all_users(user=c2.author, journals_only=False).values_list('pk', flat=True)), \
            'When the user param is set, the courses should get filtered to only be in their courses'
        assert set() == set(a.get_all_users(
            user=c2.author, courses=Course.objects.filter(pk=c1.pk), journals_only=False).values_list(
            'pk', flat=True)), \
            'When both user and courses are set, it should be an AND operator (filter on both user and courses)'

        j1 = factory.Journal(assignment=a)
        j2 = factory.Journal(assignment=a)
        assert set([j1.authors.first().user.pk, j2.authors.first().user.pk]) == set(a.get_all_users(
            courses=Course.objects.filter(pk=c1.pk)).values_list('pk', flat=True)), \
            'When journals_only is set, only get users that also have a journal'

    def test_lti_id_model_logic(self):
        # Test if a single lTI id can only be coupled to a singular assignment
        ltiAssignment1 = factory.LtiAssignment()
        ltiAssignment2 = factory.LtiAssignment()
        assert ltiAssignment1.active_lti_id != ltiAssignment2.active_lti_id, \
            'LTI ids of generated assignments should be unique.'

        ltiAssignment2.active_lti_id = ltiAssignment1.active_lti_id
        self.assertRaises(
            ValidationError,
            ltiAssignment2.save,
            msg='lti_id_set and assignment should be unique together for each arrayfield value'
        )
        assert ltiAssignment2.active_lti_id not in ltiAssignment2.lti_id_set, \
            'LTI id validaton should prevent an an invalid lti id from being added to the assignment lti_id_set'

        new_lti_id = 'Some new id'
        ltiAssignment2.active_lti_id = new_lti_id
        ltiAssignment2.save()
        assert new_lti_id in ltiAssignment2.lti_id_set, \
            'LTI ids added to the assignment should als be added to the lti_id_set'

        journal = factory.Journal(assignment=ltiAssignment1)
        journal.authors.first().grade_url = 'Not None'
        journal.authors.first().sourcedid = 'Not None'
        journal.save()
        ltiAssignment1.active_lti_id = 'new lti id'
        ltiAssignment1.save()
        # Refresh the journal instance after the assignment update
        journal = Journal.objects.get(pk=journal.pk)

        assert journal.authors.first().grade_url is None and journal.authors.first().sourcedid is None, \
            'Updating the active LTI id of an assignment should reset the grade_url and sourcedid of all nested ' \
            'journals'

    def test_deadline(self):
        journal = factory.Journal(assignment=factory.Assignment(points_possible=10), entries__n=0)
        assignment = journal.assignment
        teacher = assignment.courses.first().author

        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] == 'End of assignment', \
            'Default end of assignment should be shown'

        resp = api.get(self, 'assignments/upcoming', user=teacher)['upcoming']
        assert resp[0]['deadline']['date'] is None, \
            'Default no deadline for a teacher be shown'

        factory.ProgressPresetNode(
            format=assignment.format, due_date=timezone.now() + datetime.timedelta(days=3), target=7)

        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] == '0/7 points', \
            'When not having completed an progress node, that should be shown'

        journal.bonus_points = 7
        journal.save()
        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] == 'End of assignment', \
            'Journal bonus points should count to grade total, including fulfilling progress goals'
        journal.bonus_points = 0
        journal.save()

        entrydeadline = factory.DeadlinePresetNode(
            format=assignment.format,
            due_date=timezone.now() + datetime.timedelta(days=1),
            forced_template=assignment.format.template_set.first()
        )

        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] == assignment.format.template_set.first().name, \
            'When not having completed an entry deadline, that should be shown'

        entry = factory.PresetEntry(node=journal.node_set.get(preset=entrydeadline))

        resp = api.get(self, 'assignments/upcoming', user=teacher)['upcoming']
        assert resp[0]['deadline']['date'] is not None, \
            'With ungraded entry a deadline for a teacher be shown'

        api.create(self, 'grades', params={'entry_id': entry.pk, 'grade': 5, 'published': False}, user=teacher)
        resp = api.get(self, 'assignments/upcoming', user=teacher)['upcoming']
        assert resp[0]['deadline']['date'] is not None, \
            'With only graded & NOT published entries a deadline for a teacher be shown'

        api.create(self, 'grades', params={'entry_id': entry.pk, 'grade': 5, 'published': True}, user=teacher)
        resp = api.get(self, 'assignments/upcoming', user=teacher)['upcoming']
        assert resp[0]['deadline']['date'] is None, \
            'With only graded & published entries no deadline for a teacher be shown'

        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] == '5/7 points', \
            'With only graded & published entries progres node should be the deadline'

        api.create(self, 'grades', params={'entry_id': entry.pk, 'grade': 7, 'published': True}, user=teacher)
        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] == 'End of assignment', \
            'With full points of progress node, end of assignment should be shown'

        api.create(self, 'grades', params={'entry_id': entry.pk, 'grade': 10, 'published': True}, user=teacher)
        resp = api.get(self, 'assignments/upcoming', user=journal.authors.first().user)['upcoming']
        assert resp[0]['deadline']['name'] is None, \
            'With full points of assignment, no deadline should be shown'

    def test_publish_all_assignment_grades(self):
        grade_to_publish = factory.Grade(published=False)
        journal = grade_to_publish.entry.node.journal
        grade_published = factory.Grade(published=True, entry__node__journal=journal)
        grade_other_journal = factory.Grade(published=False)

        # Make sure setup is correct
        assert Entry.objects.get(pk=grade_published.entry.pk).grade.published
        assert not Entry.objects.get(pk=grade_to_publish.entry.pk).grade.published
        assert not Entry.objects.get(pk=grade_other_journal.entry.pk).grade.published

        with QueryContext() as queries_for_publishing_one_grade:
            api.patch(
                self,
                'grades/publish_all_assignment_grades',
                params={'assignment_id': journal.assignment.pk},
                user=journal.assignment.author,
            )

        assert Entry.objects.get(pk=grade_published.entry.pk).grade.published, \
            'published grades should stay published'
        assert Entry.objects.get(pk=grade_to_publish.entry.pk).grade.published, \
            'unpublished grades should now be published'
        assert not Entry.objects.get(pk=grade_other_journal.entry.pk).grade.published, \
            'grades not in assignment should not be published'

        for _ in range(10):
            factory.Grade(published=False, entry__node__journal=journal)

        with assert_num_queries_less_than(len(queries_for_publishing_one_grade) + 1, verbose=True):
            api.patch(
                self,
                'grades/publish_all_assignment_grades',
                params={'assignment_id': journal.assignment.pk},
                user=journal.assignment.author,
            )

    def test_get_active_course(self):
        no_startdate = factory.Course(startdate=None)
        teacher = no_startdate.author
        second_no_startdate = factory.Course(startdate=None, author=teacher)
        assignment = factory.Assignment(courses=[no_startdate, second_no_startdate])
        assert assignment.get_active_course(teacher) == no_startdate, \
            'Select first course with no startdate if there are no other courses to select from'
        assert assignment.get_active_course(factory.Student()) is None, \
            'When someone is not related to the assignment, it should not respond with any course'

        future_course = factory.Course(startdate=timezone.now() + datetime.timedelta(weeks=2), author=teacher)
        assignment.courses.add(future_course)
        later_future_course = factory.Course(startdate=timezone.now() + datetime.timedelta(weeks=5), author=teacher)
        assignment.courses.add(later_future_course)
        assert assignment.get_active_course(teacher) == future_course, \
            'Select first upcomming course as there is no LTI course or course that has already started'
        assert assignment.get_active_course(factory.Student()) is None, \
            'When someone is not related to the assignment, it should not respond with any course'

        past_course = factory.Course(startdate=timezone.now() - datetime.timedelta(weeks=5), author=teacher)
        assignment.courses.add(past_course)
        recent_course = factory.Course(startdate=timezone.now() - datetime.timedelta(weeks=3), author=teacher)
        assignment.courses.add(recent_course)
        assert assignment.get_active_course(teacher) == recent_course, \
            'Select most recent course as there is no LTI course'
        assert assignment.get_active_course(factory.Student()) is None, \
            'When someone is not related to the assignment, it should not respond with any course'

        lti_course = factory.LtiCourse(startdate=timezone.now() + datetime.timedelta(weeks=1), author=teacher)
        assignment.courses.add(lti_course)
        assignment.active_lti_id = 'lti_id'
        lti_course.assignment_lti_id_set.append('lti_id')
        lti_course.save()
        assignment.save()
        assert assignment.get_active_course(teacher) == lti_course, \
            'Select LTI course above all other courses'
        assert assignment.get_active_course(factory.Student()) is None, \
            'When someone is not related to the assignment, it should not respond with any course'

        past = factory.Course(startdate=timezone.now() - datetime.timedelta(days=1))
        assignment.courses.add(past)
        future = factory.Course(startdate=timezone.now() + datetime.timedelta(days=1))
        assignment.courses.add(future)
        lti = factory.LtiCourse(startdate=timezone.now() + datetime.timedelta(weeks=1))
        assignment.courses.add(lti)
        assert assignment.get_active_course(teacher) == lti_course, \
            'Do not select any course that the user is not in'
        assert assignment.get_active_course(factory.Student()) is None, \
            'When someone is not related to the assignment, it should not respond with any course'

    def test_day_neutral_datetime_increment(self):
        dt = datetime.datetime(year=2018, month=9, day=1)
        inc = day_neutral_datetime_increment(dt, 13)
        assert inc.weekday() == dt.weekday()
        assert inc.year == dt.year + 1
        assert inc.month == dt.month + 1

        inc = day_neutral_datetime_increment(dt, -13)
        assert inc.weekday() == dt.weekday()
        assert inc.year == dt.year - 1
        assert inc.month == dt.month - 1

        dt = datetime.datetime(year=2018, month=1, day=1) - relativedelta(days=1)
        inc = day_neutral_datetime_increment(dt, 1)
        assert inc.weekday() == dt.weekday()
        assert inc.year == dt.year + 1
        assert inc.month == 2, '4/2/2018 is the closest tuesday to 12/31/2017 + 1 month'

        inc = day_neutral_datetime_increment(dt, 12)
        assert inc == datetime.datetime(year=2019, month=1, day=6), \
            '06/01/2019 is the closest tuesday to 12/31/2017 + 1 year'
        assert inc.weekday() == dt.weekday()

    def test_set_assignment_dates(self):
        start2018_2019 = datetime.datetime(year=2018, month=9, day=1)
        start2019_2020 = datetime.datetime(year=2019, month=9, day=1)
        end2018_2019 = start2019_2020 - relativedelta(days=1)

        assignment = factory.Assignment(
            unlock_date=start2018_2019,
            due_date=end2018_2019,
            lock_date=end2018_2019,
        )

        set_assignment_dates(assignment, months=12)
        assert relativedelta(assignment.unlock_date, start2018_2019).years == 1 \
            and relativedelta(assignment.due_date, end2018_2019).years == 1 \
            and relativedelta(assignment.lock_date, end2018_2019).years == 1, \
            'Set dates should be moved 1 year forward'

        assignment.unlock_date = None
        assignment.due_date = None
        assignment.lock_date = None
        set_assignment_dates(assignment, months=12)
        assert assignment.unlock_date is None and assignment.due_date is None \
            and assignment.lock_date is None, \
            'Unset dates should not be modified'

    def test_create_journals(self):
        course_before = factory.Course()
        course_after = factory.Course()
        teacher = course_before.author
        student_before = factory.Student()
        student_after = factory.Student()
        normal_before = factory.Assignment(courses=[course_before])
        factory.Assignment(courses=[course_before], group_assignment=True)
        normal_unpublished = factory.Assignment(courses=[course_before], is_published=False)
        factory.Participation(user=student_before, course=course_before)
        normal_after = factory.Assignment(courses=[course_before])
        group_after = factory.Assignment(courses=[course_before], group_assignment=True)
        journals = Journal.all_objects.filter(authors__user=student_before)

        assert journals.filter(assignment=normal_before).exists(), 'Normal assignment should get journals'
        assert journals.filter(assignment=normal_after).exists(), \
            'Journal needs to be created even when student is added later'
        assert journals.count() == 2, 'Two journals should be created'
        journals = Journal.all_objects.filter(authors__user=teacher)
        assert journals.count() == 2, 'Teacher should also get 2 journals'

        normal_unpublished.is_group_assignment = False
        normal_unpublished.is_published = True
        normal_unpublished.save()
        journals = Journal.all_objects.filter(authors__user=student_before)
        assert journals.count() == 3, 'After publishing an extra journal needs to be created'
        journals = Journal.all_objects.filter(authors__user=teacher)
        assert journals.count() == 3, 'Teacher should also get 3 journals'

        factory.Participation(user=student_after, course=course_after)
        normal_after.add_course(course_after)
        group_after.add_course(course_after)
        journals = Journal.all_objects.filter(authors__user=student_after)
        assert journals.filter(assignment=normal_after, authors__user=student_after).exists(), \
            'Normal assignment should get journals also for students where course is added later'
        assert journals.count() == 1, 'Only normal_after should generate journal for that student'

    def test_assignment_participation_unique(self):
        journal = factory.Journal()
        student = journal.authors.first().user
        assignment = journal.assignment

        self.assertRaises(IntegrityError, AssignmentParticipation.objects.create, user=student, assignment=assignment)

    def test_participants_without_journal(self):
        assignment = factory.Assignment(group_assignment=True)
        ap1 = factory.AssignmentParticipation(user=factory.Student(), assignment=assignment)
        ap2 = factory.AssignmentParticipation(user=factory.Student(), assignment=assignment)
        ap3_in_journal = factory.AssignmentParticipation(user=factory.Student(), assignment=assignment)
        j1 = factory.GroupJournal(assignment=assignment)
        j1.add_author(ap3_in_journal)
        t1 = factory.Participation(
            user=self.teacher, course=assignment.courses.first(),
            role=Role.objects.get(course=assignment.courses.first(), name='Teacher'))
        t2 = assignment.author

        api.get(
            self, 'assignments/participants_without_journal', params={'pk': assignment.pk},
            user=ap1.user, status=403)
        participants = api.get(
            self, 'assignments/participants_without_journal', params={'pk': assignment.pk},
            user=t2, status=200)['participants']

        ids = [p['id'] for p in participants]
        assert ap2.user.pk in ids, 'check if student is in response'
        assert ap1.user.pk in ids, 'check if student is in response'
        assert ap3_in_journal.user.pk not in ids, 'check if student that is in journal is not in response'
        assert t1.user.pk not in ids, 'check if teacher is not in response'
        assert t2.pk not in ids, 'check if author of assignment is not in response'

    # LMS should be called, however, as there is nothing in ejournal.app to catch it, it will crash
    # TODO: create a valid testing env to improve this testing, set CELERY_TASK_EAGER_PROPAGATES=True
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_bonus(self):
        lti_teacher = factory.LtiTeacher()
        lti_course = factory.LtiCourse(author=lti_teacher)
        lti_assignment = factory.LtiAssignment(courses=[lti_course])
        lti_journal = factory.LtiJournal(assignment=lti_assignment)
        lti_journal = Journal.objects.get(pk=lti_journal.pk)
        lti_bonus_student = lti_journal.authors.first().user

        def test_bonus_helper(content, status=200, user=lti_teacher, delimiter=','):
            if delimiter != ',':
                content = content.replace(',', delimiter)
            MULTIPART_CONTENT = 'multipart/form-data; boundary=BoUnDaRyStRiNg'
            bonus_file = SimpleUploadedFile('bonus.csv', str.encode(content), content_type='text/csv')

            return api.post(
                self, 'assignments/{}/add_bonus_points'.format(lti_assignment.pk), params={'file': bonus_file},
                user=user, content_type=MULTIPART_CONTENT, status=status)['description']

        for d in [',', ';']:
            resp = test_bonus_helper(
                '{},2\n{},3'.format(lti_bonus_student.username, lti_assignment.author.username),
                status=400,
                delimiter=d
            )
            assert 'non_participants' in resp and len(resp['non_participants']) == 1, \
                'Teacher should not be able to get bonus points'

            resp = test_bonus_helper(
                '{},2\n{},3'.format(lti_bonus_student.username, lti_bonus_student.username), status=400, delimiter=d)
            assert 'duplicates' in resp and len(resp['duplicates']) == 1, \
                'Duplicates should not be able to work, even with different numbers'

            resp = test_bonus_helper(
                '{},2\n{},3'.format(lti_bonus_student.username, factory.Student().username), status=400, delimiter=d)
            assert 'non_participants' in resp and len(resp['non_participants']) == 1, \
                'Users that are not participating should not be able to get bonus points'

            resp = test_bonus_helper(
                '{},2\n{},3'.format(lti_bonus_student.username, 'non_exiting_student_hgfdswjhgq'),
                status=400,
                delimiter=d
            )
            assert 'unknown_users' in resp and len(resp['unknown_users']) == 1, \
                'Users that are not registerd should not be able to get bonus points'

            resp = test_bonus_helper(
                '{},2\n{},3\n{},4\n{},5\n{},3\nasdf,asdf'.format(
                    lti_bonus_student.username, 'non_exiting_student_hgfdswjhgq', factory.Student().username,
                    lti_assignment.author.username, lti_bonus_student.username), status=400, delimiter=d)
            assert 'unknown_users' in resp and 'non_participants' in resp and 'duplicates' in resp and \
                'incorrect_format_lines' in resp, \
                'Multiple errors should be returned at once'

            test_bonus_helper(
                '{},2'.format(lti_bonus_student.username), status=200, delimiter=d)
            assert Journal.objects.get(pk=lti_journal.pk).grade == 2 + lti_journal.grade, \
                'Bonus points should be added'

        # With ; this would return 2 lines as it cannot find the correct delimiter, therefor this test is only once
        resp = test_bonus_helper(
            '{},2\n{},,3'.format(lti_bonus_student.username, lti_assignment.author.username), status=400)
        assert 'incorrect_format_lines' in resp and len(resp['incorrect_format_lines']) == 1, \
            'Incorrect formatted lines should return error'

        # Non related teachers should not be able to update the bonus points
        test_bonus_helper('{},2'.format(lti_bonus_student.username), user=self.teacher, status=403)
        # Nor should students
        test_bonus_helper('{},2'.format(lti_bonus_student.username), user=lti_bonus_student, status=403)

    def test_assignment_state_actions(self):
        def init_assignment(**fields):
            return Assignment(name='Test', **fields)

        def create_assignment(**fields):
            format = Format.objects.create()
            return Assignment.objects.create(format=format, name='Test', **fields)

        created_assignment = create_assignment()
        self.assertRaises(VLEProgrammingError, Assignment.state_actions, new=created_assignment, old=None)

        def test_published():
            assignment = init_assignment(is_published=True)
            r = Assignment.state_actions(new=assignment)
            assert r['published']
            assert not r['unpublished']

            r = Assignment.state_actions(new=init_assignment(is_published=False))
            assert not r['published']
            assert not r['unpublished']

            pk = assignment.pk
            assignment.pk = None
            r = Assignment.state_actions(new=assignment)
            assert r['published']
            assert not r['unpublished']

            assignment.pk = pk
            r = Assignment.state_actions(new=assignment, old=create_assignment(is_published=False))
            assert r['published']
            assert not r['unpublished']

            r = Assignment.state_actions(
                new=init_assignment(is_published=False), old=create_assignment(is_published=True))
            assert not r['published']
            assert not r['unpublished']

        def test_type_changed():
            r = Assignment.state_actions(new=init_assignment(is_group_assignment=False))
            assert not r['type_changed']

            r = Assignment.state_actions(new=init_assignment(is_group_assignment=True))
            assert not r['type_changed']

            group_assignment = create_assignment(is_group_assignment=True)
            non_group_assignment = create_assignment(is_group_assignment=False)

            assert not Assignment.state_actions(new=group_assignment, old=group_assignment)['type_changed']
            assert Assignment.state_actions(new=group_assignment, old=non_group_assignment)['type_changed']
            assert Assignment.state_actions(new=non_group_assignment, old=group_assignment)['type_changed']
            assert not Assignment.state_actions(new=non_group_assignment, old=non_group_assignment)['type_changed']

        def test_active_lti_id_modified():
            assert not Assignment.state_actions(new=init_assignment(active_lti_id=None))['active_lti_id_modified']
            assert Assignment.state_actions(new=init_assignment(active_lti_id=0))['active_lti_id_modified']
            assert Assignment.state_actions(new=init_assignment(active_lti_id=1))['active_lti_id_modified']

            assignment_lti_none = create_assignment(active_lti_id=None)
            assignment_lti_zero = create_assignment(active_lti_id=0)
            assignment_lti_one = create_assignment(active_lti_id=1)

            assert not Assignment.state_actions(
                new=assignment_lti_none, old=assignment_lti_none)['active_lti_id_modified']
            assert Assignment.state_actions(new=assignment_lti_zero, old=assignment_lti_none)['active_lti_id_modified']
            assert Assignment.state_actions(new=assignment_lti_one, old=assignment_lti_none)['active_lti_id_modified']

            assert Assignment.state_actions(new=assignment_lti_none, old=assignment_lti_one)['active_lti_id_modified']
            assert Assignment.state_actions(new=assignment_lti_zero, old=assignment_lti_one)['active_lti_id_modified']
            assert not Assignment.state_actions(
                new=assignment_lti_one, old=assignment_lti_one)['active_lti_id_modified']

            assert Assignment.state_actions(new=assignment_lti_none, old=assignment_lti_zero)['active_lti_id_modified']
            assert not Assignment.state_actions(
                new=assignment_lti_zero, old=assignment_lti_zero)['active_lti_id_modified']
            assert Assignment.state_actions(new=assignment_lti_one, old=assignment_lti_zero)['active_lti_id_modified']

        test_published()
        test_type_changed()
        test_active_lti_id_modified()

    def test_assignment_handle_active_lti_id_modified(self):
        lti_group_journal = factory.LtiGroupJournal(entries__n=0, add_users=[factory.Student()])
        lti_group_journal = Journal.objects.get(pk=lti_group_journal.pk)
        assignment = lti_group_journal.assignment

        assert not lti_group_journal.needs_lti_link, 'Assignment, AP and Journal are initialized correctly '
        '(assignment participations have a sourcedid and grade_url, assignment an active_lti_id, and therefore '
        'the journal has no authors which still need an active lti link.'

        assignment.handle_active_lti_id_modified()

        for ap in lti_group_journal.authors.select_related('user', 'journal'):
            journal = Journal.objects.get(pk=ap.journal.pk)
            assert ap.user.full_name in journal.needs_lti_link, 'All users require a new LTI link'

    def test_assignment_serializer(self):
        assignment = factory.Assignment(format__templates=False)
        course = assignment.courses.first()
        factory.TextTemplate(format=assignment.format)

        # Some base state
        journal = factory.Journal(assignment=assignment)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1)
        factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)
        student = journal.author
        factory.Journal(assignment=assignment)
        factory.DeadlinePresetNode(format=assignment.format)
        factory.ProgressPresetNode(format=assignment.format)
        factory.Category(assignment=assignment, author=assignment.author)

        def add_state():
            factory.TextTemplate(**{'format': assignment.format})
            factory.Journal(**{'assignment': assignment})
            factory.UnlimitedEntry(**{'node__journal': journal, 'grade__grade': 1})
            factory.UnlimitedEntry(**{'node__journal': journal, 'grade__grade': 1, 'grade__published': False})
            factory.Category(assignment=assignment, author=assignment.author)

        # Student perspective
        with QueryContext() as context_pre:
            AssignmentSerializer(
                AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
                context={'user': student, 'course': course, 'serialize_journals': True}
            ).data
        add_state()
        with QueryContext() as context_post:
            AssignmentSerializer(
                AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
                context={'user': student, 'course': course, 'serialize_journals': True}
            ).data
        assert len(context_pre) == len(context_post) and len(context_pre) <= 39

        # Teacher perspective
        with QueryContext() as context_pre:
            AssignmentSerializer(
                AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
                context={'user': assignment.author, 'course': course, 'serialize_journals': True}
            ).data
        add_state()
        with QueryContext() as context_post:
            AssignmentSerializer(
                AssignmentSerializer.setup_eager_loading(Assignment.objects.filter(pk=assignment.pk)).get(),
                context={'user': assignment.author, 'course': course, 'serialize_journals': True}
            ).data
        assert len(context_pre) == len(context_post) and len(context_pre) <= 31

    def test_small_assignment_serializer(self):
        assignment = factory.Assignment(format__templates=False)

        # User is required context for any serializer which inherits AssignmentSerializer
        with self.assertRaises(VLEProgrammingError):
            SmallAssignmentSerializer(assignment).data

    def test_bulk_create_aps(self):
        assignment = factory.Assignment()
        factory.ProgressPresetNode(format=assignment.format)
        aps = [
            AssignmentParticipation(
                assignment=assignment,
                user=factory.Participation().user,
            )
            for _ in range(10)
        ]
        aps = AssignmentParticipation.objects.bulk_create(aps)
        for ap in aps:
            assert ap.journal, 'journals should be created'
            assert Node.objects.filter(journal=ap.journal).exists(), 'nodes should be created inside journal'

    def test_assignment_validate_dates(self):
        assignment = factory.Assignment()
        one_day = datetime.timedelta(days=1)

        default_unlock_date = assignment.unlock_date
        default_due_date = assignment.due_date
        default_lock_date = assignment.lock_date

        # Unmodified assignment and deadline should not break assignment validation
        deadline = factory.DeadlinePresetNode(format=assignment.format)
        assignment.validate_unlock_date()
        assignment.validate_due_date()
        assignment.validate_lock_date()
        deadline.delete()

        def reset_assignment():
            assignment.unlock_date = default_unlock_date
            assignment.due_date = default_due_date
            assignment.lock_date = default_lock_date

            assignment.format.presetnode_set.all().delete()

        def test_validate_unlock_date():
            # Unlock date cannot exceed due date
            assignment.unlock_date = assignment.due_date + one_day
            self.assertRaises(ValidationError, assignment.validate_unlock_date)
            reset_assignment()

            # Unlock date cannot exceed lock date
            assignment.unlock_date = assignment.lock_date + one_day
            self.assertRaises(ValidationError, assignment.validate_unlock_date)
            reset_assignment()

            # A deadline cannot unlock before the assignment unlocks
            factory.DeadlinePresetNode(format=assignment.format, unlock_date=assignment.unlock_date - one_day)
            self.assertRaises(ValidationError, assignment.validate_unlock_date)
            reset_assignment()

            # A deadline cannot be due before the assignment unlocks
            factory.DeadlinePresetNode(format=assignment.format, due_date=assignment.unlock_date - one_day)
            self.assertRaises(ValidationError, assignment.validate_unlock_date)
            reset_assignment()

            # A deadline cannot lock before the assignment unlocks
            factory.DeadlinePresetNode(format=assignment.format, lock_date=assignment.unlock_date - one_day)
            self.assertRaises(ValidationError, assignment.validate_unlock_date)
            reset_assignment()

        def test_validate_due_date():
            # Due date cannot occur before unlock date
            assignment.due_date = assignment.unlock_date - one_day
            self.assertRaises(ValidationError, assignment.validate_due_date)
            reset_assignment()

            # Due date cannot exceed lock date
            assignment.due_date = assignment.lock_date + one_day
            self.assertRaises(ValidationError, assignment.validate_due_date)
            reset_assignment()

            # A deadline cannot unlock after the assignment is due
            factory.DeadlinePresetNode(format=assignment.format, unlock_date=assignment.due_date + one_day)
            self.assertRaises(ValidationError, assignment.validate_due_date)
            reset_assignment()

            # A deadline cannot be due after the assignment is due
            factory.DeadlinePresetNode(format=assignment.format, due_date=assignment.due_date + one_day)
            self.assertRaises(ValidationError, assignment.validate_due_date)
            reset_assignment()

        def test_validate_lock_date():
            # Lock date cannot occur before unlock date
            assignment.lock_date = assignment.unlock_date - one_day
            self.assertRaises(ValidationError, assignment.validate_lock_date)
            reset_assignment()

            # Lock date cannot occur before due date
            assignment.lock_date = assignment.due_date - one_day
            self.assertRaises(ValidationError, assignment.validate_lock_date)
            reset_assignment()

            # A deadline cannot unlock after the assignment locks
            factory.DeadlinePresetNode(format=assignment.format, unlock_date=assignment.lock_date + one_day)
            self.assertRaises(ValidationError, assignment.validate_lock_date)
            reset_assignment()

            # A deadline cannot be due after the assignment locks
            factory.DeadlinePresetNode(format=assignment.format, due_date=assignment.lock_date + one_day)
            self.assertRaises(ValidationError, assignment.validate_lock_date)
            reset_assignment()

            # A deadline cannot be locked after the assignment locks
            factory.DeadlinePresetNode(format=assignment.format, lock_date=assignment.lock_date + one_day)
            self.assertRaises(ValidationError, assignment.validate_lock_date)
            reset_assignment()

        test_validate_unlock_date()
        test_validate_due_date()
        test_validate_lock_date()
