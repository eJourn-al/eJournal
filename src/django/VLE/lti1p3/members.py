import json

from django.conf import settings
from pylti1p3.names_roles import NamesRolesProvisioningService
from pylti1p3.service_connector import ServiceConnector

import VLE.lti1p3 as lti
from VLE.models import Instance, User


def is_test_student(member_data):
    return (
        member_data.get('email', '') == ''
        and member_data.get('name', 'anonymous').lower() == 'Test Student'.lower()  # TODO: make instance variable
    )


def sync_members(course):
    # TODO LTI: make sure message_launch_data is not needed anymore
    instance = Instance.objects.get(pk=1)
    registration = settings.TOOL_CONF.find_registration(instance.iss, client_id=instance.lti_client_id)
    connector = ServiceConnector(registration)
    nrs = NamesRolesProvisioningService(connector, json.loads(course.names_role_service))

    members = nrs.get_members()
    # TODO LTI: remove test student if there is a new test student. PREV CODE:
    # if lti.utils.is_test_student(member):
    #     User.objects.filter(participation__course=course, is_test_student=True).exclude(pk=user.pk).delete()
    for member_data in members:
        # Transfer to launch_data standard so we can use the launch data functions
        member_data['sub'] = member_data['user_id']
        member_data[lti.claims.CUSTOM] = {
            'username': member_data['user_id']
        }
        member_data[lti.claims.ROLES] = member_data['roles']
        user = User.objects.filter(lti_id=member_data['sub']).first()
        if user:
            # TODO LTI: what to do if email already exists?
            lti.user.get_or_create_participation_with_launch_data(user, member_data, course=course)
        else:
            lti.user.create_with_launch_data(member_data, course=course)
