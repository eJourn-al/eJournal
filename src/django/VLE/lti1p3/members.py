import json

from django.conf import settings
from pylti1p3.names_roles import NamesRolesProvisioningService
from pylti1p3.service_connector import ServiceConnector

import VLE.lti1p3 as lti
from VLE.models import Instance


def is_test_student(member_data):
    return (
        member_data.get('email', '') == ''
        and member_data.get('name', 'anonymous').lower() == 'Test Student'.lower()  # TODO: make instance variable
    )


def sync_members(course):
    # TODO LTI: move this to a background task & notify user that students are loading in the background
    # This may take some time: updating / creating all users. Say that to frontend

    if not course.names_role_service:  # LTI 1.0 courses cannot sync like this
        return

    instance = Instance.objects.get_or_create(pk=1)[0]
    registration = settings.TOOL_CONF.find_registration(instance.iss, client_id=instance.lti_client_id)
    connector = ServiceConnector(registration)
    nrs = NamesRolesProvisioningService(connector, json.loads(course.names_role_service))

    members = nrs.get_members()

    print(json.dumps(members, indent=4, sort_keys=True))

    for member_data in members:
        # QUESTION: we can also exclude 'Inactive' members. Is that preferred?
        # if member.get('status', 'Active') == 'Inactive':
        #     continue
        lti.user.NRSUserData(member_data).create_or_update(
            update_kwargs={'course': course},
            create_kwargs={'course': course},
        )
