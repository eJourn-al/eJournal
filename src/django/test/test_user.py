import re
import test.factory as factory
import test.factory.user as user_factory
from test.utils import api
from test.utils.lti import gen_jwt_params
from test.utils.performance import QueryContext

import pytest
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.settings import api_settings

import VLE.factory as creation_factory
import VLE.permissions as permissions
import VLE.validators as validators
from VLE.models import Instance, Preferences, Role, User
from VLE.serializers import UserSerializer, prefetched_objects


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
        assert user.preferences.new_grade_notifications == Preferences.PUSH, \
            'Generating a user also generates preferences, set to default'

        user = factory.Student(preferences__new_grade_notifications=Preferences.OFF)
        assert user.preferences.new_grade_notifications == Preferences.OFF, \
            'User factory supports deep syntax for preferences'

    def test_rest(self):
        api.test_rest(self, 'users',
                      create_params=self.create_params, get_is_create=False,
                      update_params={'username': 'test2'},
                      user=factory.Admin())

    def test_get_user(self):
        journal = factory.Journal()
        student = journal.authors.first().user
        admin = factory.Admin()
        teacher = journal.assignment.courses.first().author

        # Test get all users
        api.get(self, 'users', user=student, status=403)
        resp = api.get(self, 'users', user=admin)['results']
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

    def test_list_paginated(self):
        admin = factory.Admin()

        def test_serialized_fields():
            expected_keys = [
                'id',
                'username',
                'full_name',
                'email',
                'is_teacher',
                'is_active',
            ]

            resp = api.get(self, 'users', user=admin)

            assert len(resp['results'][0]) == len(expected_keys)
            assert all(getattr(admin, key) == resp['results'][0][key] for key in expected_keys)
            assert resp['code_version'] == settings.CODE_VERSION, \
                'Code version is also serialized for paginated responses'
            assert resp['count'] == User.objects.count()

        def test_search_vector():
            user_a = factory.Student(username='aaa')
            data = api.get(self, 'users', params={'filter': 'aa'}, user=admin)['results']
            assert len(data) == 1 and data[0]['id'] == user_a.pk, 'Username is part of the search vector'

            user_b = factory.Student(email='b@b.b')
            data = api.get(self, 'users', params={'filter': user_b.email}, user=admin)['results']
            assert len(data) == 1 and data[0]['id'] == user_b.pk, 'Email is part of the search vector'
            data = api.get(self, 'users', params={'filter': 'b@'}, user=admin)['results']
            assert len(data) == 1 and data[0]['id'] == user_b.pk, 'Partial, special char (@) no issues'

            user_c = factory.Student(full_name='c c')
            data = api.get(self, 'users', params={'filter': 'c c'}, user=admin)['results']
            assert len(data) == 1 and data[0]['id'] == user_c.pk, 'Full name is part of the search vector'

            user_a_full_name = factory.Student(full_name='aa')
            data = api.get(self, 'users', params={'filter': 'aa'}, user=admin)['results']
            assert len(data) == 2 and all(dat['id'] in [user_a.pk, user_a_full_name.pk] for dat in data)

        def test_page_param():
            resp = api.get(self, 'users', params={'page': 1, 'page_size': 1}, user=admin)
            assert len(resp['results']) == 1

            resp = api.get(self, 'users', params={'page': 1, 'page_size': 2}, user=admin)
            assert len(resp['results']) == 2

            factory.Student(full_name='a')
            factory.Student(full_name='ab')
            all_users = User.objects.all().order_by('full_name')

            resp = api.get(self, 'users', params={'page': 1, 'page_size': 1, 'order_by': 'full_name'}, user=admin)
            assert resp['results'][0]['id'] == all_users[0].pk

            resp = api.get(self, 'users', params={'page': 2, 'page_size': 1, 'order_by': 'full_name'}, user=admin)
            assert resp['results'][0]['id'] == all_users[1].pk

        def test_order_by():
            users = User.objects.all().order_by('full_name')

            data = api.get(self, 'users', params={'order_by': ''}, user=admin)['results']
            data[0]['id'] == users[0].pk, 'Empty string order_by values default to order_by full_name'

            data = api.get(self, 'users', params={'order_by': 'full_name'}, user=admin)['results']
            assert all(dat['id'] == user.pk for dat, user in zip(data, users))

            data_desc = api.get(self, 'users', params={'order_by': '-full_name'}, user=admin)['results']
            data.reverse()
            assert data == data_desc

        test_serialized_fields()
        test_search_vector()
        test_page_param()
        test_order_by()

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
        jwt_params['custom_user_image'] = 'https://canvas.uva.nl/' + \
            Instance.objects.get_or_create(pk=1)[0].default_lms_profile_picture
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
        assert user.is_test_student, 'A user created via LTI parameters without email should be flagged as test student'

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

        # Test to delete own user (not possible, should still exist)
        api.delete(self, 'users', params={'pk': user.pk}, user=user, status=403)
        api.get(self, 'users', params={'pk': user.pk}, user=admin)

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
            full_name='Test student',
            password='',
            is_test_student=True
        )
        assert test_student.is_test_student, 'Test student should be flagged accordingly'
        assert not test_student.has_usable_password(), 'Test student should have no usable password'

        # Test student should have no email on creation.
        with pytest.raises(ValidationError):
            creation_factory.make_user(
                email='test_student_should_have_no_email_on@creation.com',
                username='test_student_username2',
                password='',
                full_name='Test student',
                is_test_student=True,
            )

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

    def test_user_serializer(self):
        group = factory.Group()
        group2 = factory.Group(course=group.course)
        student = factory.Student()
        student2 = factory.Student()
        p = factory.Participation(user=student, course=group.course, role=group.course.role_set.get(name='Student'))
        p.groups.add(group, group2)
        factory.Participation(user=student2, course=group.course, role=group.course.role_set.get(name='Student'))
        p3 = factory.Participation(course=group.course, role=group.course.role_set.get(name='Student'))
        student3 = p3.user

        # Fairly best case (not all checks are exhausted)
        student_permission_queries = 5
        teacher_permission_queries = 2

        # Student perspective
        with QueryContext() as context_pre:
            UserSerializer(
                group.course.users.filter(pk__in=[student2.pk]),
                many=True,
                context={'user': student, 'course': group.course}
            ).data
        with QueryContext() as context_post:
            UserSerializer(
                group.course.users.filter(pk__in=[student2.pk, student3.pk]),
                many=True,
                context={'user': student, 'course': group.course}
            ).data
        assert len(context_post) - len(context_pre) <= student_permission_queries

        # Teacher perspective
        with QueryContext() as context_pre:
            UserSerializer(
                group.course.users.filter(pk__in=[student2.pk]),
                many=True,
                context={'user': group.course.author, 'course': group.course}
            ).data
        with QueryContext() as context_post:
            UserSerializer(
                group.course.users.filter(pk__in=[student2.pk, student3.pk]),
                many=True,
                context={'user': group.course.author, 'course': group.course}
            ).data
        assert len(context_post) - len(context_pre) <= teacher_permission_queries

    def test_annotate_course_role(self):
        c1 = factory.Course()
        c2 = factory.Course()
        p1 = factory.Participation(course=c1, role__name='role p1 c1 user')
        user = p1.user
        p2 = factory.Participation(course=c1, role__name='role p2 c1 user2')
        user2 = p2.user

        # Ensure user has multiple course participations (for query count check)
        factory.Participation(course=c2, user=user, role=Role.objects.get(name='Student', course=c2))

        assert user.participations.count() == 2

        with self.assertNumQueries(1):
            user = User.objects.filter(pk=user.pk).annotate_course_role(c1).get()
        assert user.role_name == p1.role.name

        with self.assertNumQueries(1):
            users = list(User.objects.filter(participation__course=c1).annotate_course_role(c1))

        assert user in users
        assert user2 in users
        for u in users:
            if u == user:
                assert u.role_name == p1.role.name, 'Annotation is correct'
            if u == user2:
                assert u.role_name == p2.role.name

        user = User.objects.filter(pk=user2.pk).annotate_course_role(c2).get()
        assert user.role_name is None, 'If the user is not part of the provided course, annotations yield None'

    def test_prefetch_course_groups(self):
        course = factory.Course()
        group = factory.Group(course=course)
        p1 = factory.Participation(course=course)
        user = p1.user
        p1.groups.add(group)
        p2 = factory.Participation(course=course)
        user2 = p2.user
        p2.groups.add(group)

        with self.assertNumQueries(3):  # Select user, 2 prefetches
            qry = User.objects.filter(pk__in=[user.pk, user2.pk]).prefetch_course_groups(course)

            for user in qry:
                values, prefetched = prefetched_objects(user, 'participation_set')
                participation = values[0]  # Test is setup so there no need to check if prefetched with alternative qry
                assert list(participation.groups.all()) == [group], 'All groups are prefetched for all users'

    @override_settings(EMAIL_BACKEND='anymail.backends.test.EmailBackend', CELERY_TASK_ALWAYS_EAGER=True)
    def test_invite_invalid_users(self):
        admin = factory.Admin()
        pre_invite_user_count = User.objects.count()
        users = [{
            'full_name': user.full_name,
            'username': user.username,
            'email': user.email,
        } for user in [factory.Student.build() for _ in range(7)]]

        users[0]['full_name'] = ''
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert 'Please specify a full name for all users. No invites sent.' in resp['description']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

        users[0]['username'] = ''
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert 'Please specify a username for all users. No invites sent.' in resp['description']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

        users[0]['email'] = ''
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert 'Please specify an email for all users. No invites sent.' in resp['description']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

        users[0]['username'] = users[1]['username']
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert users[0]['username'] in resp['description']['duplicate_usernames']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

        users[0]['email'] = users[1]['email']
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert users[0]['email'] in resp['description']['duplicate_emails']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

        # Username and email should be unique and case-insensitive.
        # All-uppercase versions of existing values should thus not be accepted.
        users[0]['username'] = User.objects.all().first().username.upper()
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert users[0]['username'].lower() in resp['description']['existing_usernames']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

        users[0]['email'] = User.objects.all().first().email.upper()
        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=400)
        assert users[0]['email'].lower() in resp['description']['existing_emails']
        del users[0]
        assert User.objects.count() == pre_invite_user_count, 'No accounts should be created if some user is invalid'

    @override_settings(EMAIL_BACKEND='anymail.backends.test.EmailBackend', CELERY_TASK_ALWAYS_EAGER=True)
    def test_invite_valid_users(self):
        admin = factory.Admin()
        pre_invite_user_count = User.objects.count()
        pre_invite_teacher_count = User.objects.filter(is_teacher=True).count()
        users = [{
            'full_name': user.full_name,
            'username': user.username,
            'email': user.email,
        } for user in [factory.Student.build() for _ in range(3)]]

        # Add excess whitespace to some user details.
        users[-1]['full_name'] = users[-1]['full_name'] + '   '
        users[-1]['username'] = users[-1]['username'] + '   '
        users[-1]['email'] = users[-1]['email'] + '   '

        resp = api.post(self, 'users/invite_users', params={'users': users}, user=admin)
        assert 'Successfully invited 3 users.' in resp['description']
        assert User.objects.count() == pre_invite_user_count + 3
        assert User.objects.filter(is_teacher=True).count() == pre_invite_teacher_count
        assert not User.objects.last().full_name.endswith(' '), 'Whitespace should be removed from full names'
        assert not User.objects.last().username.endswith(' '), 'Whitespace should be removed from usernames'
        assert not User.objects.last().email.endswith(' '), 'Whitespace should be removed from emails'
        assert all(Preferences.objects.filter(user__username=users[i]['username'].strip()).exists()
                   for i in range(len(users))), 'All users should have preferences initialised after invitation'

        assert len(mail.outbox) == 3, 'Invite email should be sent to all invited users'
        assert all(mail.outbox[i].to == [users[i]['email'].strip()] for i in range(len(users))), \
            'Email should be sent to the mail adress of each invited user'
        assert all(users[i]['full_name'].strip() in mail.outbox[i].body for i in range(len(users))), \
            'Invited user should be greeted by their full name'
        assert all(f'{settings.BASELINK}/SetPassword/{users[i]["username"].strip()}/'
                   in mail.outbox[i].alternatives[0][0] for i in range(len(users))), \
            'Recovery token link should be in email'

        # The recovery link should contain an indication that this is a new user, which is not part of the token
        # itself.
        for i in range(len(users)):
            token = re.search(r'SetPassword\/(.*)\/([^"]*)\?new_user=true',
                              mail.outbox[i].alternatives[0][0]).group(0).split('/')[-1][:-len('?new_user=true')]
            assert PasswordResetTokenGenerator().check_token(User.objects.get(username=users[i]['username'].strip()),
                                                             token), \
                'Token for each user should be valid and new user should be indicated in URL'

        resp = api.post(self, 'users/invite_users', params={'users': [{
            'full_name': 'Invited Teacher Name',
            'username': 'invitedteacherusername',
            'email': 'invitedteacher@ejournal.app',
            'is_teacher': True,
        }]}, user=admin)
        assert 'Successfully invited 1 users.' in resp['description']
        assert User.objects.count() == pre_invite_user_count + 4
        assert User.objects.filter(is_teacher=True).count() == pre_invite_teacher_count + 1

        assert User.objects.filter(is_active=False).count() == 4, 'Invited user accounts are not yet active'

        # Non-superusers may never invite new users.
        admin.is_superuser = False
        admin.save()
        api.post(self, 'users/invite_users', params={'users': users}, user=admin, status=403)
