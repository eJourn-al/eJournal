import json
import test.factory as factory
from test.utils import api

from django.conf import settings
from django.test import TestCase

import VLE.utils.responses


class UtilsTest(TestCase):
    def test_code_version_in_utils_json_response(self):
        json_resp = VLE.utils.responses.json_response()
        assert json.loads(json_resp.content)['code_version'] == settings.CODE_VERSION

    def test_code_version_in_responses(self):
        student = factory.Student()
        student2 = factory.Student()

        resp = api.get(self, 'users', params={'pk': student.pk}, user=student)
        assert resp['code_version'] == settings.CODE_VERSION, 'Code version is serialized on success'

        resp = api.get(self, 'users', params={'pk': student2.pk}, user=student, status=403)
        assert resp['code_version'] == settings.CODE_VERSION, 'Code version is serialized on error'

        resp = api.post(self, 'forgot_password', params={'identifier': student.username})
        assert resp['code_version'] == settings.CODE_VERSION, 'Code version is also serialized for anom users'
