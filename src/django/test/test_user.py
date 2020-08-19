import test.factory as factory
import test.factory.user as user_factory
from test.utils import api
from test.utils.lti import gen_jwt_params

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.settings import api_settings

import VLE.factory as creation_factory
import VLE.permissions as permissions
import VLE.validators as validators
from VLE.models import Instance, User


class UserAPITest(TestCase):
    def setUp(self):
        self.create_params = {
            'username': 'test', 'password': 'Pa$$word!', 'email': 'test@ejournal.app',
            'full_name': 'test user'
        }
        self.lti_creation_params = {
            'user_id': 'LMS_user_id',
            'custom_user_image': 'https://LMS_user_profile_image_link.com',
            'custom_user_full_name': 'full name of LMS user',
            'custom_user_email': 'validLMS@address.com',
        }

    def test_user_factory(self):
        user = factory.Student()
        assert user.preferences.grade_notifications, 'Generating a user also generates preferences, set to default'

        user = factory.Student(preferences__grade_notifications=False)
        assert not user.preferences.grade_notifications, 'User factory supports deep syntax for preferences'

    def test_rest(self):
        api.test_rest(self, 'users',
                      create_params=self.create_params, get_is_create=False,
                      update_params={'username': 'test2'},
                      user=factory.Admin())

    def test_get(self):
        journal = factory.Journal()
        student = journal.authors.first().user
        admin = factory.Admin()
        teacher = journal.assignment.courses.first().author

        # Test get all users
        api.get(self, 'users', user=student, status=403)
        resp = api.get(self, 'users', user=admin)['users']
        assert len(resp) == User.objects.count(), 'Test if the admin got all the users'

        # Test get own user
        resp = api.get(self, 'users', params={'pk': 0}, user=student)['user']
        assert 'id' in resp, 'Test if the student got userdata'
        assert 'verified_email' in resp, 'Test if the student got all their userdata'

        resp = api.get(self, 'users', params={'pk': 0}, user=admin)['user']
        assert resp['is_superuser'], 'Admin user should be flagged as superuser.'

        # Check if a user cant see other users data
        api.get(self, 'users', params={'pk': admin.pk}, user=student, status=403)

        # Test get user as supervisor
        assert permissions.is_user_supervisor_of(teacher, student), 'Teacher should be supervisor of student'
        resp = api.get(self, 'users', params={'pk': student.pk}, user=teacher)['user']
        assert 'username' in resp, 'Supervisor can retrieve basic supervisee data'
        assert 'full_name' in resp, 'Supervisor can retrieve basic supervisee data'
        assert 'verified_email' not in resp, 'Supervisor can\'t retrieve all supervisee data'
        assert 'email' not in resp, 'Supervisor can\'t retrieve all supervisee data'

        # Test get user as admin
        resp = api.get(self, 'users', params={'pk': student.pk}, user=admin)['user']
        assert 'id' in resp, 'Admin can retrieve basic user data'
        assert 'verified_email' in resp, 'Admin can retrieve all user data'
        assert 'email' in resp, 'Admin can retrieve all user data'

    def test_create_user(self):
        params = dict(self.create_params)

        # Test a valid creation
        resp = api.create(self, 'users', params=params)['user']
        assert 'id' in resp, 'Check if id is in resp'
        assert resp['username'] == params['username'], 'Check if the username is the same'
        user = User.objects.get(username=params['username'])
        assert user.has_usable_password(), 'Normal users should have a usable password.'

        # Test a creation with the same username and email
        resp = api.create(self, 'users', params=params, status=400)

        # Test a non lti creation without email
        params_without_email = {'username': 'test2', 'password': 'Pa$$word!', 'full_name': 'test user2'}
        resp = api.create(self, 'users', params=params_without_email, status=400)
        params_without_email = {'username': 'test2', 'password': 'Pa$$word!', 'full_name': 'test user2', 'email': ''}
        resp = api.create(self, 'users', params=params_without_email, status=400)
        assert resp['description'] == 'No email address is provided.'
        params_without_email = {'username': 'test2', 'password': 'Pa$$word!', 'full_name': 'test user2', 'email': None}
        resp = api.create(self, 'users', params=params_without_email, status=400)
        assert resp['description'] == 'No email address is provided.'
        params_without_email = {
            'username': 'test2', 'password': 'Pa$$word!', 'full_name': '', 'email': 'valid@email.com'}
        resp = api.create(self, 'users', params=params_without_email, status=400)
        assert resp['description'] == 'No full name is provided.'

        # Test a creation with the different username and same email
        params['username'] = 'test2'
        params['email'] = self.create_params['email']
        resp = api.create(self, 'users', params=params, status=400)

        # Test a creation with the same username and different email
        params['username'] = self.create_params['username']
        params['email'] = 'test2@ejournal.app'
        resp = api.create(self, 'users', params=params, status=400)

        # Test a creation with the different username and email
        params['username'] = 'test2'
        params['email'] = 'test2@ejournal.app'
        resp = api.create(self, 'users', params=params)['user']

    def test_lti_creation(self):
        user_params = factory.UserParams()

        # User creation via LTI requires an LTI_ID
        api.create(self, 'users', params={**user_params, **gen_jwt_params(factory.JWTParams(user_id=None))}, status=400)

        # Standard LTI user creation
        jwt_params = factory.JWTParams()
        jwt_params['custom_user_image'] = Instance.objects.get_or_create(pk=1)[0].default_lms_profile_picture
        api.create(self, 'users', params={**user_params, **gen_jwt_params(jwt_params)})
        user = User.objects.get(username=user_params['username'])
        assert not user.is_test_student, 'A default user created via LTI parameters should not be flagged ' \
            'as a test student.'
        assert user.profile_picture == settings.DEFAULT_PROFILE_PICTURE
        # Standard LTI user creation
        jwt_params = factory.JWTParams()
        jwt_params['user_id'] = 'second_user'
        user_params['username'] = 'second_user'
        jwt_params['custom_user_image'] = 'https://www.ejournal.app/img/ejournal-logo-white.83c3aad1.svg'
        api.create(self, 'users', params={**user_params, **gen_jwt_params(jwt_params)})
        user = User.objects.get(username=user_params['username'])
        assert not user.is_test_student, 'A default user created via LTI parameters should not be flagged ' \
            'as a test student.'
        assert user.profile_picture == 'https://www.ejournal.app/img/ejournal-logo-white.83c3aad1.svg'

        # Can't create two users with the same lti ID
        resp = api.create(self, 'users', params={
            **factory.UserParams(),
            **gen_jwt_params(factory.JWTParams(user_id=jwt_params['user_id']))
        }, status=400)
        assert 'lti id already exists' in resp['description']

        # Test student creation
        user_params = factory.UserParams()
        api.create(self, 'users', params={
            **user_params,
            **gen_jwt_params(factory.JWTTestUserParams()),
        })
        user = User.objects.get(username=user_params['username'])
        assert user.is_test_student, 'A user created via LTI parameters without email and with full_name {} should ' \
            'should be flagged as a test student.'.format(settings.LTI_TEST_STUDENT_FULL_NAME)

        # It should be possible to create multiple test students (all without email under the unique contraint)
        api.create(self, 'users', params={
            **factory.UserParams(),
            **gen_jwt_params(factory.JWTTestUserParams()),
        })

    def test_update_user(self):
        user = factory.Student()
        user2 = factory.Student()
        lti_user = factory.LtiStudent()
        admin = factory.Admin()

        # Test update the own user
        old_username = user.username
        resp = api.update(self, 'users', params={'pk': 0, 'username': 'test2', 'full_name': 'abc'}, user=user)['user']
        assert resp['username'] == old_username, 'Username should not be updated'
        assert resp['full_name'] == 'abc', 'Firstname should be updated'

        # Test update user as admin
        resp = api.update(self, 'users', params={'pk': user.pk, 'full_name': 'not_admin'}, user=admin)['user']
        assert resp['full_name'] == 'not_admin', 'Firstname should be updated'

        # Test update other user as user
        api.update(self, 'users', params={'pk': user.pk, 'full_name': 'not_admin'}, user=user2, status=403)

        # Cant update user full name or username if the user has an LTI id
        resp = api.update(
            self,
            'users',
            params={
                'pk': 0,
                'full_name': 'new name',
                'username': 'new username',
            },
            user=lti_user
        )['user']
        updated_lti_user = User.objects.get(pk=lti_user.pk)
        assert lti_user.username == updated_lti_user.username
        assert lti_user.full_name == updated_lti_user.full_name

        is_test_student = factory.TestUser(lti_id=None)
        resp = api.update(self, 'users', user=is_test_student, params={
            'email': 'new_cor@m.com', 'pk': is_test_student.pk})['user']
        is_test_student = User.objects.get(pk=is_test_student.pk)
        assert is_test_student.is_test_student, 'Test student status should remain intact after updating email.'
        assert not is_test_student.verified_email, 'Updating email without LTI should not validate said email.'
        assert resp['email'] == 'new_cor@m.com', 'Email should be updated'

    def test_lti_update(self):
        # Valid LTI coupling to pre-existing account
        user = factory.Student(verified_email=False)
        resp = api.update(self, 'users', user=user, params={
            **gen_jwt_params(params={
                    'user_id': 'valid_id1',
                    'custom_user_full_name': 'new full name',
                    'custom_user_email': 'newmail@address.com',
                    'custom_user_image': 'https://new.com/img.png',
                }, user=user),
            'pk': user.pk,
        })['user']
        user = User.objects.get(pk=user.pk)
        assert user.lti_id, 'Pre-existing user should now be linked via LTI'
        assert resp['full_name'] == 'new full name' and user.full_name == 'new full name', 'Full name should be updated'
        assert user.verified_email, 'Updating email via LTI should also verify it'
        assert resp['email'] == 'newmail@address.com' and user.email == 'newmail@address.com', 'Email should be updated'
        assert user.profile_picture == 'https://new.com/img.png', 'Profile picture should be updated.'

        # Cannot couple an account using an already known LTI id
        user2 = factory.Student()
        resp = api.update(self, 'users', user=user2, params={
            **gen_jwt_params(params={'user_id': user.lti_id}, user=user2),
            'pk': user2.pk,
        }, status=400)
        assert 'lti id already exists' in resp['description']

        # Cannot link to a user when the email address is already claimed
        resp = api.update(self, 'users', user=user2, params={
            **gen_jwt_params(params={'custom_user_email': user.email}),
            'pk': user2.pk,
        }, status=400)
        assert 'is taken' in resp['description'], 'Cannot link to a user when the email address is already claimed'

        # It is forbidden to link a test account to an existing account
        lti_teacher = factory.LtiTeacher()
        resp = api.update(self, 'users', user=lti_teacher, params={
            **gen_jwt_params(params=factory.JWTTestUserParams()),
            'pk': 0,
        }, status=403)
        teacher = factory.Teacher()
        resp = api.update(self, 'users', user=teacher, params={
            **gen_jwt_params(params=factory.JWTTestUserParams()),
            'pk': 0,
        }, status=403)

    def test_delete(self):
        user = factory.Student()
        user2 = factory.Student()
        user3 = factory.Student()
        admin = factory.Admin()
        admin2 = factory.Admin()

        # Test to delete user as other user
        api.delete(self, 'users', params={'pk': user2.pk}, user=user, status=403)

        # Test to delete own user
        api.delete(self, 'users', params={'pk': user.pk}, user=user)
        api.get(self, 'users', params={'pk': user.pk}, user=admin, status=404)
        api.delete(self, 'users', params={'pk': 0}, user=user2)
        api.get(self, 'users', params={'pk': user2.pk}, user=admin, status=404)

        # Test to delete user as admin
        api.delete(self, 'users', params={'pk': user3.pk}, user=admin)
        api.get(self, 'users', params={'pk': user3.pk}, user=admin, status=404)

        # Test to see if the last admin cannot be removed
        api.delete(self, 'users', params={'pk': admin2.pk}, user=admin)
        api.delete(self, 'users', params={'pk': admin.pk}, user=admin, status=400)
        api.get(self, 'users', params={'pk': admin2.pk}, user=admin, status=404)

    def test_login(self):
        user = factory.Student()
        old_last_login = User.objects.get(pk=user.pk).last_login
        api.login(self, user)
        assert old_last_login != User.objects.get(pk=user.pk).last_login, 'Last login should be updated'

        old_last_login = User.objects.get(pk=user.pk).last_login
        api.login(self, user, password="wrong", status=401)
        assert old_last_login == User.objects.get(pk=user.pk).last_login, 'Last login should not be updated'

        # Check that login should also be possible with different capitalizations
        api.post(self, api.reverse('token_obtain_pair'),
                 params={'username': user.username.lower(), 'password': user_factory.DEFAULT_PASSWORD})
        api.post(self, api.reverse('token_obtain_pair'),
                 params={'username': user.username.upper(), 'password': user_factory.DEFAULT_PASSWORD})

    def test_password(self):
        user = factory.Student()

        user_factory.DEFAULT_PASSWORD
        # Test with wrong password
        api.update(self, 'users/password', params={'old_password': 'test', 'new_password': 'test'},
                   user=user, status=400)

        # Test with invalid new password
        api.update(self, 'users/password',
                   params={'old_password': user_factory.DEFAULT_PASSWORD, 'new_password': 'test'},
                   user=user, status=400)

        # Test with valid new password
        api.update(self, 'users/password',
                   params={'old_password': user_factory.DEFAULT_PASSWORD, 'new_password': 'Pa$$word1'}, user=user)

    def test_email_restriction(self):
        params = self.create_params.copy()

        params.pop('email')
        with pytest.raises(ValidationError) as exception_info:
            User.objects.create(**params)
        assert 'requires an email adress' in str(exception_info.value)

        params['is_test_student'] = True
        params['full_name'] = settings.LTI_TEST_STUDENT_FULL_NAME
        User.objects.create(**params)

    def test_gdpr(self):
        entry = factory.UnlimitedEntry()
        user = entry.node.journal.authors.first().user
        user2 = factory.Student()
        admin = factory.Admin()

        # Test if users cant access other data
        api.get(self, 'users/GDPR', params={'pk': user2.pk}, user=user, status=403)

        # Test all the gdpr calls
        for _ in range(int(api_settings.DEFAULT_THROTTLE_RATES['gdpr'].split('/')[0])):
            api.get(self, 'users/GDPR', params={'pk': 0}, user=user)
        # Test timeout
        api.get(self, 'users/GDPR', params={'pk': 0}, user=user, status=429)

        # Test admin
        api.get(self, 'users/GDPR', params={'pk': user.pk}, user=admin)

        # Test no timeout for admin
        for _ in range(int(api_settings.DEFAULT_THROTTLE_RATES['gdpr'].split('/')[0])):
            api.get(self, 'users/GDPR', params={'pk': 0}, user=admin)
        api.get(self, 'users/GDPR', params={'pk': 0}, user=admin)

    def test_make_user(self):
        # Create test student
        test_student = creation_factory.make_user(
            username='test_student_username',
            password='',
            full_name=settings.LTI_TEST_STUDENT_FULL_NAME,
            is_test_student=True
        )
        assert test_student.is_test_student, 'Test student should be flagged accordingly'
        assert not test_student.has_usable_password(), 'Test student should have no usable password'
        with pytest.raises(ValidationError):
            assert creation_factory.make_user(
                username='test_student_username', password='', full_name='Not test student', is_test_student=True), \
                'Test user\'s full name is expected to match Test student'

        test_student.email = 'newvalid@email.com'
        test_student.full_name = 'new full name'
        test_student.save()
        assert test_student.email == 'newvalid@email.com' and test_student.full_name == 'new full name', \
            'After creation a test student should be able to update their full name and email address'

        # A test student should remain a test student
        with pytest.raises(ValidationError):
            test_student.is_test_student = False
            test_student.save()

    def test_password_validation(self):
        # We require a special character
        with pytest.raises(ValidationError):
            validators.validate_password('SomePassword')
        # Underscore qualifies as special character
        validators.validate_password('Some_Password')

    def test_can_view(self):
        journal = factory.GroupJournal()
        user1 = journal.authors.first().user
        ap2 = factory.AssignmentParticipation(assignment=journal.assignment)
        user2 = ap2.user
        journal.add_author(ap2)
        user3 = factory.AssignmentParticipation(assignment=journal.assignment).user

        assert user1.can_view(user2) and user2.can_view(user1), 'Users in same journal should be able to see each other'
        assert not user3.can_view(user1), 'Users in different journals should not be able to see each other'
        assert user1.can_view(journal.assignment.courses.first().author), \
            'Student should be able to see supervisor'
        assert journal.assignment.courses.first().author.can_view(user1), \
            'Supervisor should be able to see its students'
        assert not factory.Teacher().can_view(user1), 'Non supervisor should not be able to see its students'
        assert user1.can_view(user1), 'Non supervisor should not be able to see its students'

    # TODO: Test download, upload and set_profile_picture
