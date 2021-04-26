"""
test_lti_launch.py.

Test lti launch.
"""

import datetime
import test.factory as factory
import time
from test.utils import api
from test.utils.lti import get_new_lti_id, get_signature, lti_launch_response_to_access_token

import oauth2
from django.conf import settings
from django.test import RequestFactory, TestCase

import VLE.lti_launch as lti
import VLE.views.lti as lti_view
from VLE.models import Group, Instance, Journal, Participation, User, access_gen

REQUEST = {
    # Authentication data
    'oauth_consumer_key': str(settings.LTI_KEY),
    'oauth_signature_method': 'HMAC-SHA1',
    'oauth_version': '1.0',
    'oauth_timestamp': 'null',
    'oauth_nonce': 'null',
    'lti_message_type': 'basic-lti-launch-request',
    'lti_version': 'LTI-1p0',
    # Assignment data
    'custom_assignment_due': '2022-11-10 23:59:00 +0100',
    'custom_assignment_id': 'assignment_lti_id',
    'custom_assignment_lock': '2022-12-15 23:59:59 +0100',
    'custom_assignment_title': 'Assignment Title',
    'custom_assignment_unlock': '2018-08-16 00:00:00 +0200',
    'custom_assignment_points': '10',
    'custom_assignment_publish': 'true',
    # Course data
    'custom_course_id': 'course_lti_id',
    'custom_course_name': 'Course Title',
    'custom_course_start': '2018-06-15 14:41:00 +0200',
    'context_label': 'aaaa',
    # Participation data
    'roles': '',
    'lis_outcome_service_url': 'a grade url',
    'lis_result_sourcedid': 'a sourcedid',
}


def create_request_body(user=None, course=None, assignment=None, is_teacher=False):
    request = REQUEST.copy()

    if user:
        request['custom_username'] = user.username
        request['custom_user_full_name'] = user.full_name
        request['custom_user_image'] = user.profile_picture
        request['user_id'] = user.lti_id or access_gen()
    else:
        n = User.objects.count()
        request['custom_username'] = f'user_{n}_{access_gen(size=10)}'
        request['custom_user_full_name'] = f'Fullname User{n}'
        request['custom_user_image'] = 'https://canvas.instructure.com/images/messages/avatar-50.png'
        request['user_id'] = access_gen()
        request['custom_user_email'] = f'email{access_gen(size=10)}@ejournal.app'

    if is_teacher:
        request['roles'] = 'urn:lti:role:ims/lis/Instructor'

    if course:
        assert course.active_lti_id, 'course needs to be an LTI course'
        request['custom_course_id'] = course.active_lti_id
        request['custom_course_name'] = course.name
        request['custom_course_start'] = course.startdate
        request['context_label'] = course.abbreviation
    else:
        request['custom_course_id'] = access_gen()
        request['custom_course_name'] = 'LTI course ' + access_gen(size=10)
        request['context_label'] = access_gen(size=3)
        request['custom_course_start'] = '2018-06-15 14:41:00 +0200'

    if assignment:
        assert assignment.active_lti_id, 'assignment needs to be an LTI assignment'
        request['custom_assignment_id'] = assignment.active_lti_id
        request['custom_assignment_title'] = assignment.name
        request['custom_assignment_unlock'] = assignment.unlock_date
        request['custom_assignment_due'] = assignment.due_date
        request['custom_assignment_lock'] = assignment.lock_date
        request['custom_assignment_points'] = assignment.points_possible
        request['custom_assignment_publish'] = ('false', 'true')[assignment.is_published]
    else:
        request['custom_assignment_id'] = access_gen()
        request['custom_assignment_title'] = 'LTI assignment ' + access_gen(size=10)
        request['custom_assignment_points'] = 10
        request['custom_assignment_publish'] = 'true'

    return request


def create_request(
        request_body={}, timestamp=None, nonce=None, delete_field=False, to_lti_launch=True,
        user=None, course=None, assignment=None, is_teacher=False):
    if nonce is None:
        nonce = str(oauth2.generate_nonce())
    if timestamp is None:
        timestamp = str(int(time.time()))
    request = create_request_body(user=user, course=course, assignment=assignment, is_teacher=is_teacher)
    request['oauth_timestamp'] = timestamp
    request['oauth_nonce'] = nonce

    for key, value in request_body.items():
        if key != 'oauth_signature':
            request[key] = value

    if delete_field is not False:
        request.pop(delete_field, None)

    request['oauth_signature'] = get_signature(request)

    if 'oauth_signature' in request_body:
        request['oauth_signature'] = request_body['oauth_signature']

    if not to_lti_launch:
        return request

    return RequestFactory().post('http://127.0.0.1:8000/lti/launch', request)


def lti_launch(
        request_body={}, response_value=lti_view.LTI_STATES.NO_USER.value, timestamp=None,
        nonce=None, status=302, assert_msg='', delete_field=False):
    if nonce is None:
        nonce = str(oauth2.generate_nonce())
    if timestamp is None:
        timestamp = str(int(time.time()))
    request = create_request(request_body, timestamp, nonce, delete_field)
    response = lti_view.lti_launch(request)
    assert response.status_code == status
    assert 'state={0}'.format(response_value) in response.url, assert_msg
    return response


def get_jwt(obj, request_body={}, timestamp=None, nonce=None,
            user=None, status=200, response_msg='', assert_msg='', response_value=None, delete_field=False,
            access=None, url='get_lti_params_from_jwt'):
    if nonce is None:
        nonce = str(oauth2.generate_nonce())
    if timestamp is None:
        timestamp = str(int(time.time()))
    request = create_request(request_body, timestamp, nonce, delete_field, to_lti_launch=False)
    jwt_params = lti_view.encode_lti_params(request)
    response = api.post(obj, url, params={'jwt_params': jwt_params},  user=user, status=status, access=access)
    if response_msg:
        if 'description' in response:
            assert response_msg in response['description'], assert_msg
        else:
            assert response_msg in response['detail'], assert_msg
    elif response_value:
        assert response['params']['state'] in response_value, assert_msg
    return response


class LtiLaunchTest(TestCase):
    """Lti launch test.

    Test if the gradepassback XML can be created.
    """

    def setUp(self):
        """Setup."""
        self.factory = RequestFactory()

        self.new_lti_id = 'new_lti_id'

        self.teacher = factory.Teacher()
        self.teacher.lti_id = 'teacher_lti_id'
        self.teacher.save()

        self.journal = factory.Journal()
        self.student = self.journal.authors.first().user
        self.student.lti_id = 'student_lti_id'
        self.student.save()
        self.request = REQUEST.copy()
        self.assignment = self.journal.assignment

    def test_select_user(self):
        selected_user = lti.get_user_lti({'user_id': self.student.lti_id})
        assert selected_user == self.student, 'get_user_lti should return a user when given an lti_id'

    def test_lti_launch_no_user_no_info(self):
        lti_launch(
            assert_msg='Without anything, it should give redirect msg with state = NO_USER'
        )

    def test_lti_launch_no_user(self):
        lti_launch(
            request_body={
                'custom_user_full_name': 'testpersoon voor Science',
                'custom_username': 'TestUser',
                'custom_user_email': 'ltiTest@test.com'
            },
            assert_msg='Without a user lti_id, it should give redirect msg with state = NO_USER',
        )

    def test_lti_launch_user(self):
        old_last_login = self.student.last_login
        lti_launch(
            request_body={
                'user_id': self.student.lti_id
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With a user_id the user should login',
        )
        assert old_last_login != User.objects.get(pk=self.student.pk).last_login, \
            'Last login should be updated'

    def test_lti_launch_user_update_email(self):
        old_last_login = self.student.last_login
        old_email = self.student.email
        lti_launch(
            request_body={
                'user_id': self.student.lti_id,
                'custom_user_email': 'NEW' + self.student.email
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With a user_id the user should login',
        )
        assert old_email != User.objects.get(pk=self.student.pk).email, \
            'Email should be updated'
        assert old_last_login != User.objects.get(pk=self.student.pk).last_login, \
            'Last login should be updated'

    def test_lti_launch_multiple_roles(self):
        lti_launch(
            request_body={
                'roles': 'Extra,urn:lti:instrole:ims/lis/Instructor',
                'user_id': self.student.lti_id
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With only institution wide teacher role (no context teacher) student should not become teacher',
        )
        assert not User.objects.get(lti_id=self.student.lti_id).is_teacher, \
            'Student should not become a teacher when loggin in with only institution wide Instructor role'

        lti_launch(
            request_body={
                'roles': 'Extra,urn:lti:role:ims/lis/Instructor',
                'user_id': self.student.lti_id
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With a user_id the user should login',
        )
        assert User.objects.get(lti_id=self.student.lti_id).is_teacher, \
            'Student should become a teacher when loggin in with Instructor role'
        lti_launch(
            request_body={
                'roles': 'Extra,Hello',
                'user_id': self.student.lti_id
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With a user_id the user should login',
        )
        assert User.objects.get(lti_id=self.student.lti_id).is_teacher, \
            'Teacher should stay teacher when roles change'

    def test_lti_launch_content_developer(self):
        lti_launch(
            request_body={
                'roles': 'Extra,urn:lti:role:ims/lis/ContentDeveloper',
                'user_id': self.student.lti_id
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With a user_id the user should login',
        )
        assert User.objects.get(lti_id=self.student.lti_id).is_teacher, \
            'Student should become a teacher when loggin in with content developer role'

    def test_lti_launch_unknown_role(self):
        lti_launch(
            request_body={
                'roles': 'urn:lti:role:ims/lis/Administrator',
                'user_id': self.student.lti_id
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With an invalid role the user should still login',
        )

    def test_lti_launch_wrong_signature(self):
        lti_launch(
            request_body={
                'roles': 'urn:lti:role:ims/lis/Administrator',
                'user_id': get_new_lti_id(),
                'oauth_signature': 'invalid'
            },
            response_value=lti_view.LTI_STATES.BAD_AUTH.value,
            assert_msg='With an invalid signature, a user should not be able to login',
        )

    def test_lti_launch_key_error(self):
        lti_launch(
            request_body={'user_id': get_new_lti_id()},
            response_value=lti_view.LTI_STATES.KEY_ERR.value,
            assert_msg='Without all the keys, it should return a KEY_ERROR',
            delete_field='custom_username',
        )

    def test_lti_launch_account_exists(self):
        resp = lti_launch(
            request_body={
                'user_id': get_new_lti_id(),
                'custom_username': 'TestUser',
            },
            response_value=lti_view.LTI_STATES.NO_USER.value,
            assert_msg='With a user_id the user should login',
        )
        assert 'username_already_exists=True' not in resp.url, \
            'When user does not exists, it should not specify it in response'
        resp = lti_launch(
            request_body={
                'user_id': self.student.lti_id,
                'custom_username': self.student.username,
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='With a user_id the user should login',
        )
        assert 'username_already_exists=True' not in resp.url, \
            'When user already exists but user_id is correct, it should not specify it in response'
        resp = lti_launch(
            request_body={
                'user_id': get_new_lti_id(),
                'custom_username': self.student.username,
            },
            response_value=lti_view.LTI_STATES.NO_USER.value,
            assert_msg='With a new user_id, user should not login',
        )
        assert 'username_already_exists=True' in resp.url, \
            'When user already exists, but user_id is not correct, it should specify it in response'

    def test_lti_flow_test_user(self):
        course = factory.LtiCourse()
        assignment = factory.LtiAssignment(courses=[course])
        test_user_params = factory.JWTTestUserParams(user_id=get_new_lti_id())

        resp = lti_launch(
            request_body=test_user_params,
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='A test user should directly be created on lti launch if not exist.',
        )
        test_student = User.objects.get(lti_id=test_user_params['user_id'])
        assert test_student.is_test_student, 'A new test user should be created and flagged accordingly.'
        total_users = User.objects.count()

        get_jwt(
            self, user=test_student, status=200, access=lti_launch_response_to_access_token(resp),
            request_body={
                **test_user_params,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a course and assign linked, a fresh test student should be forwarded to finish state.'
        )

        resp = lti_launch(
            request_body=test_user_params,
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
            assert_msg='A reused test user can launch successfully after being created.',
        )

        get_jwt(
            self, user=test_student, status=200, access=lti_launch_response_to_access_token(resp),
            request_body={
                **test_user_params,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a course and assign linked, a reused test student should be forwarded to finish state.'
        )

        assert total_users == User.objects.count(), 'Launching and relaunching should create no additional users.'

        # Test the flow of another test user part of the same course and assignment
        test_user_params2 = factory.JWTTestUserParams(user_id=get_new_lti_id())

        resp = lti_launch(request_body=test_user_params2, response_value=lti_view.LTI_STATES.LOGGED_IN.value)
        test_student2 = User.objects.get(lti_id=test_user_params2['user_id'])
        get_jwt(
            self, user=test_student2, status=200, access=lti_launch_response_to_access_token(resp),
            request_body={
                **test_user_params2,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='A second fresh test student from the same course and assign should be forwarded to finish state'
        )
        assert User.objects.filter(lti_id=test_user_params2['user_id']).exists(), 'Second test user should be created.'
        assert not User.objects.filter(lti_id=test_student.lti_id).exists(), 'Can only be one test student per course.'

    def test_get_lti_params_from_valid_test_user(self):
        course = factory.LtiCourse()
        assignment = factory.LtiAssignment(courses=[course])
        test_student = factory.TestUser()
        get_jwt(
            self, user=test_student, status=200,
            request_body={
                'user_id': test_student.lti_id,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a course and assign linked, a test student should be forwarded to finish state.')

        test_student2 = factory.TestUser()
        get_jwt(
            self, user=test_student2, status=200,
            request_body={
                'user_id': test_student2.lti_id,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a course and assign linked, a test student should be forwarded to finish state.')
        assert not User.objects.filter(lti_id=test_student.lti_id).exists(), 'Max of 1 test student per course.'

        course2 = factory.LtiCourse()
        assignment2 = factory.LtiAssignment(courses=[course2])

        test_student3 = factory.TestUser()
        get_jwt(
            self, user=test_student3, status=200,
            request_body={
                'user_id': test_student3.lti_id,
                'custom_course_id': course2.active_lti_id,
                'custom_assignment_id': assignment2.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a course and assign linked, a test student should be forwarded to finish state.')
        assert User.objects.filter(lti_id=test_student2.lti_id).exists(), \
            'Linking a test user to one course should not delete test users of a different course.'

    def test_get_lti_params_from_invalid_user_id(self):
        get_jwt(
            self, user=self.student, status=404,
            request_body={'user_id': 'invalid_user_id'},
            response_msg='User does not exist',
            assert_msg='Without a valid lti_id it should not find the user')

    def test_update_lti_groups(self):
        course = factory.LtiCourse()
        assignment = factory.LtiAssignment(courses=[course])
        test_student = factory.TestUser()
        group_count = Group.objects.filter(course=course).count()

        get_jwt(
            self, url='update_lti_groups',
            user=self.student, status=404,
            request_body={'user_id': 'invalid_user_id'},
            response_msg='User does not exist',
            assert_msg='Without a valid lti_id it should not find the user',
        )

        get_jwt(
            self, url='update_lti_groups',
            user=test_student, status=200,
            request_body={
                'user_id': test_student.lti_id,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_msg='',
            assert_msg='With valid params it should response successfully',
        )
        assert group_count == Group.objects.filter(course=course).count(), \
            'No new groups should be created, if no supplied'

        # User is added to two groups on the LMS unknown to eJournal
        lms_group_ids = {'new_group1', 'new_group2'}
        body = {
            'user_id': test_student.lti_id,
            'custom_section_id': ','.join(lms_group_ids),
            'custom_course_id': course.active_lti_id,
            'custom_assignment_id': assignment.active_lti_id,
        }
        get_jwt(
            self, url='update_lti_groups',
            user=test_student, status=200,
            request_body=body,
            response_msg='',
            assert_msg='With valid params it should response successfully',
        )
        assert group_count + 2 == Group.objects.filter(course=course).count() and \
            Group.objects.filter(course=course, lti_id='new_group2').exists(), \
            'New groups should be created'
        test_student_participation = test_student.participation_set.get(course=course)
        assert set(test_student_participation.groups.values_list('lti_id', flat=True)) == lms_group_ids, \
            'The newly created LMS groups have been added to the participation of the student'

        # User is removed from 'new_group2' group manually on EJ
        new_group2 = Group.objects.get(lti_id='new_group2')
        test_student_participation.groups.remove(new_group2)
        get_jwt(
            self, url='update_lti_groups',
            user=test_student, status=200,
            request_body=body,
            response_msg='',
            assert_msg='With valid params it should response successfully',
        )
        assert set(test_student_participation.groups.values_list('lti_id', flat=True)) == lms_group_ids, (
            'LTI launch overwrites any group corrections made specifically on the EJ side, when the group is part of '
            'the lti launch params.'
        )

        # User is added to a group created manually on EJ
        ej_group = factory.Group(course=course, lti_id='')
        test_student_participation.groups.add(ej_group)
        group_pks = set(test_student_participation.groups.values_list('pk', flat=True))
        get_jwt(
            self, url='update_lti_groups',
            user=test_student, status=200,
            request_body=body,
            response_msg='',
            assert_msg='With valid params it should response successfully',
        )
        assert set(test_student_participation.groups.values_list('pk', flat=True)) == group_pks, \
            'LTI launch does not affect groups which are not part of the request body (only syncs mentioned groups).'

    def test_get_lti_params_from_jwt_wrong_user(self):
        get_jwt(
            self, user=self.teacher, status=403,
            request_body={'user_id': self.student.lti_id},
            response_msg='The user specified that should be logged in according',
            assert_msg='With an lti_id from another user, it should return forbidden')

    def test_get_lti_params_from_jwt_unauthorized(self):
        get_jwt(
            self, user=None, status=401,
            request_body={'user_id': self.student.lti_id},
            response_msg='Authentication credentials were not provided.',
            assert_msg='User needs to be logged in before the user can extract lti_params')

    def test_get_lti_params_from_jwt_expired(self):
        get_jwt(
            self, user=self.student, status=403,
            request_body={
                'user_id': self.student.lti_id,
                'exp': datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
            },
            response_msg='expired',
            assert_msg='App should return expired if experation time is past')

    def test_get_lti_params_from_jwt_course_teacher(self):
        get_jwt(
            self, user=self.teacher, status=200,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:role:ims/lis/Instructor'},
            response_value=lti_view.LTI_STATES.NEW_COURSE.value,
            assert_msg='When a teacher gets jwt_params for the first time it should return the NEW_COURSE state')

    def test_get_lti_params_from_jwt_course_student(self):
        get_jwt(
            self, user=self.student, status=200,
            request_body={'user_id': self.student.lti_id},
            response_value=lti_view.LTI_STATES.LACKING_PERMISSION_TO_SETUP_COURSE.value,
            assert_msg='Connecting to an course which has not been setup yet as a student, should flag accordingly')

    def test_get_lti_params_from_jwt_assignment_teacher(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        get_jwt(
            self, user=self.teacher, status=200,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:role:ims/lis/Instructor',
                'custom_course_id': course.active_lti_id},
            response_value=lti_view.LTI_STATES.NEW_ASSIGN.value,
            assert_msg='When a teacher gets jwt_params after course is created it should return the NEW_ASSIGN state')

    def test_get_lti_params_from_jwt_old_assignment_teacher(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        old_id = assignment.active_lti_id
        assignment.active_lti_id = assignment.active_lti_id + '_new'
        assignment.save()

        response = get_jwt(
            self, user=self.teacher, status=200,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:role:ims/lis/Instructor',
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': old_id},
            response_value=lti_view.LTI_STATES.FINISH_T.value,
            assert_msg='When a teacher joins via a no longer active lti assignment, he should still be normally' +
                       ' forwarded.')
        assert response['params']['jID'] is None, 'A teacher should receive no journal id'

    def test_get_lti_params_from_jwt_old_assignment_student_with_journal(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='When after assignment is created it should return the FINISH_S state for students')
        old_id = assignment.active_lti_id
        assignment.active_lti_id = assignment.active_lti_id + '_new'
        assignment.save()
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'roles': 'Student',
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': old_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='When a student with journal joins via an old LTI connection, he should still be normally ' +
                       'forwarded (FINISH_S state)')

    def test_get_lti_params_from_jwt_no_context_label(self):
        get_jwt(
            self, user=self.teacher, status=200,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:role:ims/lis/Instructor'},
            response_value=lti_view.LTI_STATES.NEW_COURSE.value,
            delete_field='context_label')

    def test_get_lti_params_from_jwt_assignment_student(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'custom_course_id': course.active_lti_id},
            response_value=lti_view.LTI_STATES.LACKING_PERMISSION_TO_SETUP_ASSIGNMENT.value,
            assert_msg='Connecting to an assignment which has not been setup yet as a student, should flag accordingly')

    def test_get_lti_params_from_jwt_journal_teacher(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        get_jwt(
            self, user=self.teacher, status=200,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:role:ims/lis/Instructor',
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_T.value,
            assert_msg='When after assignment is created it should return the FINISH_T state for teachers')

    def test_get_lti_params_from_jwt_journal_ta(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'roles': 'urn:lti:role:ims/lis/TeachingAssistant',
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_T.value,
            assert_msg='When after assignment is created it should return the FINISH_T state for teaching assistents')

    def test_get_lti_params_from_jwt_journal_mentor(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'roles': 'urn:lti:role:ims/lis/Mentor',
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_T.value,
            assert_msg='When after assignment is created it should return the FINISH_T state for mentors')

    def test_get_lti_params_from_jwt_journal_student(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id},
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='When after assignment is created it should return the FINISH_S state for students')

    def test_legit_student_new_journal_update_passback(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        student = factory.LtiStudent()
        journal_exists = Journal.objects.filter(authors__user=student, assignment=assignment).exists()
        assert not journal_exists, "The student is assumed to have no journal beforehand"

        get_jwt(
            self, user=student, status=200,
            request_body={
                'user_id': student.lti_id,
                'custom_course_id': course.active_lti_id,
                'custom_assignment_id': assignment.active_lti_id,
                'lis_outcome_service_url': REQUEST['lis_outcome_service_url'],
                'lis_result_sourcedid': REQUEST['lis_result_sourcedid'],
            },
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a setup assignment, a legitimate student jwt connection should return FINISH_S state')

        journal_qry = Journal.objects.filter(authors__user=student, assignment=assignment)
        assert journal_qry.count() == 1, 'A legitimate student jwt connection should create a single journal.'
        journal = journal_qry.first()
        assert journal.authors.first().sourcedid == REQUEST['lis_result_sourcedid'], \
            'A legitimate student jwt route should set a journal sourcedid.'
        assert journal.authors.first().grade_url == REQUEST['lis_outcome_service_url'], \
            'A legitimate student jwt route should set a journal grade_url.'

    def test_legit_student_from_old_uplink_update_passback(self):
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        assignment = factory.LtiAssignment(
            author=self.teacher, courses=[course], name=REQUEST['custom_assignment_title'])
        student = factory.LtiStudent()
        journal = factory.Journal(assignment=assignment, ap__user=student)
        assignment = journal.assignment

        journal_exists = Journal.objects.filter(authors__user=student, assignment=assignment, pk=journal.pk).exists()
        assert journal_exists, "The student is assumed to have a single nested journal beforehand"

        journal.authors.first().grade_url = 'before'
        journal.authors.first().sourcedid = 'before'
        course.active_lti_id = 'new'
        assignment.active_lti_id = 'new'
        course.save()
        assignment.save()
        journal.save()

        get_jwt(
            self, user=student, status=200,
            request_body={
                'user_id': student.lti_id,
                'custom_course_id': 'new',
                'custom_assignment_id': 'new',
                'lis_outcome_service_url': REQUEST['lis_outcome_service_url'],
                'lis_result_sourcedid': REQUEST['lis_result_sourcedid'],
            },
            response_value=lti_view.LTI_STATES.FINISH_S.value,
            assert_msg='With a setup assignment, a legitimate student jwt connection should return FINISH_S state',
        )

        journal = Journal.objects.get(authors__user=student, assignment=assignment)
        assert journal.authors.first().sourcedid == REQUEST['lis_result_sourcedid'], \
            'A legitimate student jwt route should set a journal sourcedid.'
        assert journal.authors.first().grade_url == REQUEST['lis_outcome_service_url'], \
            'A legitimate student jwt route should set a journal grade_url.'

    def test_get_lti_params_from_jwt_multiple_roles(self):
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'roles': 'Learner,urn:lti:role:ims/lis/Instructor'},
            response_value=lti_view.LTI_STATES.NEW_COURSE.value,
            assert_msg='When a student tries to create a new course, with also a new Instructor role, \
                        it should grand its permissions')

    def test_get_lti_params_from_jwt_administrator_role(self):
        get_jwt(
            self, user=self.student, status=200,
            request_body={
                'user_id': self.student.lti_id,
                'roles': 'Learner,urn:lti:role:ims/lis/Administrator'},
            response_value=lti_view.LTI_STATES.NEW_COURSE.value,
            assert_msg='When a student tries to create a new course, with also a new Administrator role, \
                        it should grand its permissions')

    def test_get_lti_params_from_jwt_unknown_role(self):
        get_jwt(
            self, user=self.teacher, status=200,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:instrole:ims/lis/nothing'},
            response_value=lti_view.LTI_STATES.LACKING_PERMISSION_TO_SETUP_COURSE.value,
            assert_msg='When a teacher goes to the platform without a teacher role, it should lose its teacher powers')

    def test_get_lti_params_from_jwt_key_error(self):
        get_jwt(
            self, user=self.teacher, status=400,
            request_body={
                'user_id': self.teacher.lti_id,
                'roles': 'urn:lti:role:ims/lis/Instructor'},
            delete_field='custom_course_id',
            response_msg='missing',
            assert_msg='When missing keys, it should return a keyerror')

    def test_get_lti_params_update_prifile_picture(self):
        lti_launch(
            request_body={
                'user_id': self.teacher.lti_id,
                'custom_username': self.teacher.username,
                'custom_user_image': 'https://canvas.uva.nl/' +
                Instance.objects.get_or_create(pk=1)[0].default_lms_profile_picture,
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
        )
        self.teacher.refresh_from_db()
        assert self.teacher.profile_picture == settings.DEFAULT_PROFILE_PICTURE
        lti_launch(
            request_body={
                'user_id': self.teacher.lti_id,
                'custom_username': self.teacher.username,
                'custom_user_image': 'https://www.ejournal.app/img/ejournal-logo-white.83c3aad1.svg',
            },
            response_value=lti_view.LTI_STATES.LOGGED_IN.value,
        )
        self.teacher.refresh_from_db()
        assert self.teacher.profile_picture == 'https://www.ejournal.app/img/ejournal-logo-white.83c3aad1.svg'

    def test_select_course_with_participation(self):
        """Hopefully select a course."""
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        selected_course = lti.update_lti_course_if_exists(
            {'custom_course_id': course.active_lti_id},
            user=self.teacher, role=settings.ROLES['Teacher'][0])
        assert selected_course == course

    def test_select_course_with_participation_and_groups(self):
        """Hopefully creates extra groups."""
        course = factory.LtiCourse(author=self.teacher, name=REQUEST['custom_course_name'])
        factory.Group(name='existing group', course=course, lti_id='1000')
        factory.Group(name='existing group2', course=course, lti_id='1001')
        selected_course = lti.update_lti_course_if_exists({
                'custom_course_id': course.active_lti_id,
                'custom_section_id': ','.join(['1000', '1001', '1002', '1003']),
            }, user=self.teacher, role=settings.ROLES['Teacher'][0])
        assert selected_course == course
        assert Group.objects.filter(course=course, name='Group 3').exists(), \
            'Groups with an LTI id that are do not exist need to get renamed'
        assert Group.objects.filter(course=course).count() == 4, \
            'Groups with an LTI id that exists should not create new groups'
        assert Participation.objects.get(user=self.teacher, course=course).groups.count() == 4, \
            'Teacher needs to be added to all groups'

        lti.update_lti_course_if_exists({
                'custom_course_id': course.active_lti_id,
                'custom_section_id': ','.join(['1000', '1001', '1002', '1003']),
            }, user=self.teacher, role=settings.ROLES['Teacher'][0])

        assert Group.objects.filter(course=course).count() == 4, \
            'No new groups should be created'

        assignment = factory.LtiAssignment(courses=[course], author=self.teacher)
        journal = factory.Journal(assignment=assignment)
        student = journal.authors.first().user
        groups = ['1000', '1001', '100123987']

        lti.update_lti_course_if_exists({
                'custom_course_id': course.active_lti_id,
                'custom_section_id': ','.join(groups),
            }, user=student, role=settings.ROLES['Teacher'][0])

        journal = Journal.objects.get(pk=journal.pk)
        assert set(journal.groups) == set(Group.objects.filter(lti_id__in=groups).values_list('pk', flat=True)), \
            'Journal groups should also be updated'

        course.active_lti_id = '6068'
        course.save()
        lti.update_lti_course_if_exists({
            'custom_course_id': course.active_lti_id,
            'custom_section_id': '12489,12492',
        }, user=student, role=settings.ROLES['Teacher'][0])
        assert Group.objects.filter(name='Cohort 2017').exists()

    def test_select_journal(self):
        """Hopefully select a journal."""
        selected_journal = lti.select_create_journal(
            {
                'roles': settings.ROLES['Student'][0],
                'custom_assignment_id': self.assignment.active_lti_id,
                'lis_result_sourcedid': "267-686-2694-585-0afc8c37342732c97b011855389af1f2c2f6d552",
                'lis_outcome_service_url': "https://uvadlo-tes.instructure.com/api/lti/v1/tools/267/grade_passback"
            },
            self.student,
            self.assignment
        )
        assert selected_journal == self.journal

        new_assignment = factory.LtiAssignment(courses=self.assignment.courses.all())
        factory.AssignmentParticipation(assignment=new_assignment, user=self.student)
        new_journal = Journal.objects.get(assignment=new_assignment, authors__user=self.student)
        assert new_journal.needs_lti_link
        new_url = "https://uvadlo-tes.instructure.com/api/lti/v1/tls/267/grade_passback"
        new_id = "267-686-2694-585-0afc8c37342732c97b011855gfdshsdbfaf1f2c2f6d552"
        selected_journal = lti.select_create_journal(
            {
                'roles': settings.ROLES['Student'][0],
                'custom_assignment_id': new_assignment.active_lti_id,
                'lis_result_sourcedid': new_id,
                'lis_outcome_service_url': new_url,
            },
            self.student,
            new_assignment
        )
        assert selected_journal == new_journal
        assert not selected_journal.needs_lti_link
        assert selected_journal.authors.first().grade_url == new_url
        assert selected_journal.authors.first().sourcedid == new_id

    def test_select_journal_no_assign(self):
        """Hopefully select None."""
        selected_journal = lti.select_create_journal(
            {
                'roles': settings.ROLES['Student'][0],
                'custom_assignment_id': self.assignment.active_lti_id,
                'lis_result_sourcedid': "267-686-2694-585-0afc8c37342732c97b011855389af1f2c2f6d552",
                'lis_outcome_service_url': "https://uvadlo-tes.instructure.com/api/lti/v1/tools/267/grade_passback"
            },
            self.student,
            None
        )
        assert selected_journal is None
