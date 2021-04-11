import test.factory as factory
from test.utils import api

from django.test import TestCase


class InstanceAPITest(TestCase):

    def test_get(self):
        # Check if PK does not matter
        resp = api.get(self, 'instance', params={'pk': 0})
        assert resp['instance']['id'] == 1

        assert not resp['instance']['has_client_secret'], \
            'Client secret doesnt exist by default, and thus has_client_secret should be false'
        assert 'api_client_secret' not in resp['instance'], \
            'Serializer should not respond with the secret, because it is secret'

    def test_update(self):
        api.update(self, 'instance', params={'pk': 0}, user=factory.Teacher(), status=403)

        admin = factory.Admin()
        resp = api.update(self, 'instance', params={'pk': 0, 'name': 'B1'}, user=admin)
        assert resp['instance']['name'] == 'B1'
        new_secret = 'ASDLKJHGVREKJ EWIOUNCKIQJAWSDNIQKAJWD'
        resp = api.update(self, 'instance', params={
            'pk': 0,
            'name': 'B1',
            'api_client_secret': new_secret,
        }, user=admin)
        assert resp['instance']['has_client_secret'], 'Client secret should be set, and respond that it has one'

        resp = api.update(self, 'instance', params={
            'pk': 0,
            'name': 'B1',
        }, user=admin)
        assert 'api_client_secret' not in resp['instance'], \
            'Serializer should not respond with client secret, when secret is not passed in update function'
