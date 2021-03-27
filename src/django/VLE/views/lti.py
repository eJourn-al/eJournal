import enum

import jwt
from django.conf import settings
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoOIDCLogin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

import VLE.lti_launch as lti
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import User
from VLE.utils.error_handling import VLEMissingRequiredKey


class LTI_STATES(enum.Enum):
    """VUE ENTRY STATE."""
    LACKING_PERMISSION_TO_SETUP_ASSIGNMENT = '-4'
    LACKING_PERMISSION_TO_SETUP_COURSE = '-3'

    KEY_ERR = '-2'
    BAD_AUTH = '-1'

    NO_USER = '0'
    LOGGED_IN = '1'

    NO_COURSE = '0'
    NO_ASSIGN = '1'
    NEW_COURSE = '2'
    NEW_ASSIGN = '3'
    FINISH_T = '4'
    FINISH_S = '5'


def decode_lti_params(jwt_params):
    return jwt.decode(jwt_params, settings.SECRET_KEY, algorithms=['HS256'])


def encode_lti_params(jwt_params):
    return jwt.encode(jwt_params, settings.SECRET_KEY, algorithm='HS256').decode('utf-8')


def get_new_course_response(lti_params, role):
    """Generate course information for the teacher to setup the course with.

    This only works when the lti user is a teacher of that course.
    """
    if 'Teacher' not in role:
        return response.success({'params': {
            'state': LTI_STATES.LACKING_PERMISSION_TO_SETUP_COURSE.value,
            'lti_cName': lti_params['custom_course_name'],
            'lti_aName': lti_params['custom_assignment_title'],
        }})

    try:
        return response.success({'params': {
            'state': LTI_STATES.NEW_COURSE.value,
            'lti_cName': lti_params['custom_course_name'],
            'lti_abbr': lti_params.get('context_label', ''),
            'lti_cID': lti_params['custom_course_id'],
            'lti_course_start': lti_params['custom_course_start'],
            'lti_aName': lti_params['custom_assignment_title'],
            'lti_aID': lti_params['custom_assignment_id'],
            'lti_aUnlock': lti_params['custom_assignment_unlock'],
            'lti_aDue': lti_params['custom_assignment_due'],
            'lti_aLock': lti_params['custom_assignment_lock'],
            'lti_points_possible': lti_params['custom_assignment_points'],
            'lti_aPublished': lti_params['custom_assignment_publish'],
        }})
    except KeyError as err:
        raise VLEMissingRequiredKey(err.args[0])


def get_new_assignment_response(lti_params, course, role):
    """Generate assignment information for the teacher to setup the assignment with.

    This only works when the lti user is a teacher of that assignment.
    """
    if 'Teacher' not in role:
        return response.success({'params': {
            'state': LTI_STATES.LACKING_PERMISSION_TO_SETUP_ASSIGNMENT.value,
            'lti_cName': lti_params['custom_course_name'],
            'lti_aName': lti_params['custom_assignment_title'],
        }})

    try:
        return response.success({'params': {
            'state': LTI_STATES.NEW_ASSIGN.value,
            'cID': course.pk,
            'lti_aName': lti_params['custom_assignment_title'],
            'lti_aID': lti_params['custom_assignment_id'],
            'lti_aUnlock': lti_params['custom_assignment_unlock'],
            'lti_aDue': lti_params['custom_assignment_due'],
            'lti_aLock': lti_params['custom_assignment_lock'],
            'lti_points_possible': lti_params['custom_assignment_points'],
            'lti_aPublished': lti_params['custom_assignment_publish'],
        }})
    except KeyError as err:
        raise VLEMissingRequiredKey(err.args[0])


def get_finish_state(user, assignment, lti_params):
    if user.has_permission('can_view_all_journals', assignment):
        return LTI_STATES.FINISH_T.value
    else:
        return LTI_STATES.FINISH_S.value


@api_view(['POST'])
def get_lti_params_from_jwt(request):
    """Handle the controlflow for course/assignment create, connect and select.

    Returns the data needed for the correct entry place.
    """
    user = request.user
    jwt_params, = utils.required_params(request.data, 'jwt_params')
    lti_params = decode_lti_params(jwt_params)
    if user != User.objects.get(lti_id=lti_params['user_id']):
        return response.forbidden(
            "The user specified that should be logged in according to the request is not the logged in user.")

    role = lti.roles_to_lti_roles(lti_params)
    # convert LTI param for True to python True
    lti_params['custom_assignment_publish'] = lti_params.get('custom_assignment_publish', 'false') == 'true'

    # If the course is already created, update that course, else return new course variables
    course = lti.update_lti_course_if_exists(lti_params, user, role)
    if course is None:
        return get_new_course_response(lti_params, role)

    # If the assignment is already created, update that assignment, else return new assignment variables
    assignment = lti.update_lti_assignment_if_exists(lti_params)
    if assignment is None:
        return get_new_assignment_response(lti_params, course, role)

    # Select a journal
    if user.has_permission('can_have_journal', assignment):
        journal = lti.select_create_journal(lti_params, user, assignment)

    return response.success(payload={'params': {
        'state': get_finish_state(user, assignment, lti_params),
        'cID': course.pk,
        'aID': assignment.pk,
        'jID': journal.pk if user.has_permission('can_have_journal', assignment) and journal else None,
    }})


# TODO LTI: check if this needs to be removed or not
@api_view(['POST'])
@permission_classes((AllowAny, ))
def update_lti_groups(request):
    user = request.user
    jwt_params, = utils.required_params(request.data, 'jwt_params')
    lti_params = decode_lti_params(jwt_params)
    if user != User.objects.get(lti_id=lti_params['user_id']):
        return response.forbidden(
            "The user specified that should be logged in according to the request is not the logged in user.")

    role = lti.roles_to_list(lti_params)
    course = lti.update_lti_course_if_exists(lti_params, user, role)
    if course:
        return response.success()
    else:
        return response.bad_request('Course not found.')


def get_launch_url(request):
    target_link_uri = request.POST.get('target_link_uri', request.GET.get('target_link_uri'))
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')
    return target_link_uri


@api_view(['POST', 'GET'])
@permission_classes((AllowAny, ))
def lti_login(request):
    oidc_login = DjangoOIDCLogin(request, settings.TOOL_CONF, launch_data_storage=DjangoCacheDataStorage())
    target_link_uri = get_launch_url(request)
    a = oidc_login\
        .enable_check_cookies()\
        .redirect(target_link_uri)
    return a
