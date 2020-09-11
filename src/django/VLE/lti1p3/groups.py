import json

from VLE.lms_api import utils
from VLE.models import Instance


def sync_groups(access_token):
    instance = Instance.objects.get(pk=1)
    url = instance.lms_url + '/api/v1/courses/1/sections'
    sections = utils.api_request(url, access_token).content
    url = instance.lms_url + '/api/v1/courses/1/users'
    users = utils.api_request(url, access_token).content
    # TODO LTI: pagination

    return {
        'sections': json.loads(sections),
        'users': json.loads(users),
    }
