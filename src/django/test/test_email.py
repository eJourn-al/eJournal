import test.factory as factory
from test.utils import api

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.test import TestCase

import VLE.models


class EmailAPITest(TestCase):
    def setUp(self):
        self.student = factory.Student()
        self.not_verified = factory.Student(verified_email=False)
        self.valid_pass = 'New_v4lid_pass!'

    def test_forgot_password(self):
        # Test if no/invalid params crashes
        api.post(self, 'forgot_password', status=404)
        api.post(self, 'forgot_password', params={'username': 'invalid_username'}, status=404)
        api.post(self, 'forgot_password', params={'email': 'invalid_email'}, status=404)

        # Test valid parameters
        resp = api.post(self, 'forgot_password', params={'username': self.student.username})
        assert 'An email was sent' in resp['description'], \
            'You should be able to get forgot password mail with only a username'
        resp = api.post(self, 'forgot_password', params={'email': self.student.email})
        assert 'An email was sent' in resp['description'], \
            'You should be able to get forgot password mail with only an email'
        resp = api.post(self, 'forgot_password', params={'email': self.student.email}, user=self.student)
        assert 'An email was sent' in resp['description'], \
            'You should be able to get forgot password mail while logged in'

    def test_recover_password(self):
        api.post(self, 'recover_password', status=400)
        # Test invalid token
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'recovery_token': 'invalid_token',
                'new_password': self.valid_pass},
            status=400)
        # Test invalid password
        token = PasswordResetTokenGenerator().make_token(self.student)
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'recovery_token': token,
                'new_password': 'new_invalid_pass'},
            status=400)
        # Test invalid username
        api.post(
            self, 'recover_password',
            params={
                'username': factory.Student().username,
                'recovery_token': token,
                'new_password': self.valid_pass},
            status=400)

        # Test everything valid
        api.post(
            self, 'recover_password',
            params={
                'username': self.student.username,
                'recovery_token': token,
                'new_password': self.valid_pass})

    def test_verify_email(self):
        api.post(self, 'verify_email', status=400)
        # Test invalid token
        api.post(self, 'verify_email',
                 params={'username': self.not_verified.username, 'token': 'invalid_token'}, status=400)
        # Test invalid username
        token = PasswordResetTokenGenerator().make_token(self.not_verified)
        api.post(self, 'verify_email', params={'username': factory.Student().username, 'token': token}, status=400)

        # Test everything valid
        resp = api.post(self, 'verify_email', params={'username': self.not_verified.username, 'token': token})
        assert VLE.models.User.objects.get(pk=self.not_verified.pk).verified_email
        assert 'Success' in resp['description']
        # Test already verified
        token = PasswordResetTokenGenerator().make_token(self.student)
        resp = api.post(self, 'verify_email', params={'username': self.student.username, 'token': token})
        assert 'already verified' in resp['description']

    def test_request_email_verification(self):
        api.post(self, 'request_email_verification', status=401)

        resp = api.post(self, 'request_email_verification', user=self.student)
        assert 'already verified' in resp['description']

        resp = api.post(self, 'request_email_verification', user=self.not_verified)
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
