import test.factory as factory
import test.factory.user as userfactory
from test.utils import api

from django.test import TestCase
from rest_framework.settings import api_settings


class UserAPITest(TestCase):
    def setUp(self):
        self.create_params = {
            'username': 'test', 'password': 'Pa$$word!', 'email': 'test@ejourn.al',
            'full_name': 'test user'
        }

    def test_rest(self):
        api.test_rest(self, 'users',
                      create_params=self.create_params, get_is_create=False,
                      update_params={'username': 'test2'},
                      user=factory.Admin())

    def test_get(self):
        student = factory.Student()
        admin = factory.Admin()

        # Test get all users
        api.get(self, 'users', user=student, status=403)
        get_resp = api.get(self, 'users', user=admin)['users']
        assert len(get_resp) == 2, 'Test if the admin got all the users'

        # Test get own user
        get_resp = api.get(self, 'users', params={'pk': 0}, user=student)['user']
        assert 'id' in get_resp, 'Test if the student got userdata'
        assert 'verified_email' in get_resp, 'Test if the student got all their userdata'

        # Check if a user cant see other users data
        api.get(self, 'users', params={'pk': admin.pk}, user=student, status=403)

        # TODO: test get user as supervisor
        # NOTE: verified_email should not be in get_resp

        # Test get user as admin
        get_resp = api.get(self, 'users', params={'pk': student.pk}, user=admin)['user']
        assert 'id' in get_resp, 'Test if the student got userdata'
        assert 'verified_email' in get_resp, 'Test if the student got all their userdata'

    def test_create(self):
        params = dict(self.create_params)

        # Test a valid creation
        resp = api.create(self, 'users', params=params)['user']
        assert 'id' in resp, 'Check if id is in resp'
        assert resp['username'] == params['username'], 'Check if the username is the same'

        # Test a creation with the same username and email
        resp = api.create(self, 'users', params=params, status=400)

        # Test a creation with the different username and same email
        params['username'] = 'test2'
        params['email'] = self.create_params['email']
        resp = api.create(self, 'users', params=params, status=400)

        # Test a creation with the same username and different email
        params['username'] = self.create_params['username']
        params['email'] = 'test2@ejourn.al'
        resp = api.create(self, 'users', params=params, status=400)

        # Test a creation with the different username and email
        params['username'] = 'test2'
        params['email'] = 'test2@ejourn.al'
        resp = api.create(self, 'users', params=params)['user']

        # TODO: test lti_user

    def test_update(self):
        user = factory.Student()
        user2 = factory.Student()
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

        # TODO: test lti_user

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

    def test_password(self):
        user = factory.Student()

        userfactory.DEFAULT_PASSWORD
        # Test with wrong password
        api.update(self, 'users/password', params={'old_password': 'test', 'new_password': 'test'},
                   user=user, status=400)

        # Test with invalid new password
        api.update(self, 'users/password',
                   params={'old_password': userfactory.DEFAULT_PASSWORD, 'new_password': 'test'},
                   user=user, status=400)

        # Test with valid new password
        api.update(self, 'users/password',
                   params={'old_password': userfactory.DEFAULT_PASSWORD, 'new_password': 'Pa$$word1'}, user=user)

    def test_gdpr(self):
        user = factory.Student()
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

    # TODO: Test download, upload and set_profile_picture
