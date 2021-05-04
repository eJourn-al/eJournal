from django.conf import settings
from django.contrib.auth.hashers import is_password_usable
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.datastructures import MultiValueDictKeyError
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoOIDCLogin
from pylti1p3.deep_link_resource import DeepLinkResource
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import VLE.lti as lti
from VLE.models import Instance, Journal
from VLE.utils.error_handling import VLEBadRequest
from VLE.utils.generic_utils import build_url


class eDeepLinkResource(DeepLinkResource):
    _scope = None

    def set_scope(self, scope):
        self._scope = scope

    def to_dict(self):
        dic = super().to_dict()
        dic['scope'] = self._scope
        return dic


def handle_no_user_connected_to_launch_data(launch_data, launch_id):
    response_data = {
        'launch_state': lti.utils.LTI_STATES.NO_USER.value,
        'launch_id': launch_id,
        'username_already_exists': bool(launch_data.user.find_in_db()),
        'name': launch_data.user.full_name or launch_data.user.username,
    }
    if launch_data.course.find_in_db():
        response_data['course_id'] = launch_data.course.find_in_db().pk
    if launch_data.assignment.find_in_db():
        response_data['assignment_id'] = launch_data.assignment.find_in_db().pk
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


def handle_no_course_connected_to_launch_data(launch_data, launch_id, user):
    refresh = TokenObtainPairSerializer.get_token(user)
    response_data = {
        'launch_state':
            lti.utils.LTI_STATES.NO_COURSE.value if launch_data.course.author == user else
            lti.utils.LTI_STATES.NOT_SETUP.value,
        'launch_id': launch_id,
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
    }
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


def handle_no_assignment_connected_to_launch_data(launch_data, launch_id, user, course):
    refresh = TokenObtainPairSerializer.get_token(user)
    response_data = {
        'launch_state':
            lti.utils.LTI_STATES.NO_ASSIGNMENT.value if launch_data.course.author == user else
            lti.utils.LTI_STATES.NOT_SETUP.value,
        'launch_id': launch_id,
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
        'course_id': course.id,
    }
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


def handle_all_connected_to_launch_data(launch_data, launch_id, user, course, assignment, journal, request):
    refresh = TokenObtainPairSerializer.get_token(user)
    response_data = {
        'launch_state':
            lti.utils.LTI_STATES.FINISH_TEACHER.value if launch_data.user.role_name == 'Teacher' else
            lti.utils.LTI_STATES.FINISH_STUDENT.value,
        'launch_id': launch_id,
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
        'course_id': course.id,
        'assignment_id': assignment.id,
        'left_journal': request.query_params.get('left_journal', False),
    }
    # Go directly to journal if it is a submission url, i.e. the gradebook or student launch
    if 'submission' in request.query_params:
        response_data['journal_id'] = request.query_params['submission']
    elif journal:
        response_data['journal_id'] = journal.pk

    # TODO LTI: send grade back to LTI if newly connected user / new grade url & sourcedid

    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


@api_view(['GET'])
@permission_classes((AllowAny, ))
def launch_configuration(request):
    if Instance.objects.get_or_create(pk=1)[0].lms_name == Instance.CANVAS:
        return JsonResponse({
            'title': 'eJournal',
            'scopes': [
                'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
                'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem.readonly',
                'https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly',
                'https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly',
                'https://purl.imsglobal.org/spec/lti-ags/scope/score',
                'https://canvas.instructure.com/lti/public_jwk/scope/update',
                'https://canvas.instructure.com/lti/data_services/scope/create',
                'https://canvas.instructure.com/lti/data_services/scope/show',
                'https://canvas.instructure.com/lti/data_services/scope/update',
                'https://canvas.instructure.com/lti/data_services/scope/list',
                'https://canvas.instructure.com/lti/data_services/scope/destroy',
                'https://canvas.instructure.com/lti/data_services/scope/list_event_types',
                'https://canvas.instructure.com/lti/feature_flags/scope/show',
                'https://canvas.instructure.com/lti/account_lookup/scope/show'
            ],
            'extensions': [
                {
                    'platform': 'canvas.instructure.com',
                    'settings': {
                        'platform': 'canvas.instructure.com',
                        'placements': [
                            {
                                'placement': 'assignment_selection',
                                'message_type': 'LtiDeepLinkingRequest',
                                'target_link_uri': settings.LTI_LAUNCH_URL,
                            }
                        ]
                    },
                    'privacy_level': 'public'
                }
            ],
            'public_jwk': {},
            'description': 'eJournal development',
            'custom_fields': {
                'username': '$User.username',  # NOTE: username is duplicate of $User.login_id
                'course_id': '$Canvas.course.id',
                'course_name': '$Canvas.course.name',
                'course_start': '$Canvas.course.startAt',
                'section_ids': '$Canvas.course.sectionIds',
                'group_context_id': '$Canvas.group.contextIds',
                'assignment_id': '$Canvas.assignment.id',
                'assignment_lti_id': '$com.instructure.Assignment.lti.id',
                'assignment_unlock': '$Canvas.assignment.unlockAt',
                'assignment_due': '$Canvas.assignment.dueAt',
                'assignment_lock': '$Canvas.assignment.lockAt',
                'assignment_points': '$Canvas.assignment.pointsPossible',
                'assignment_publish': '$Canvas.assignment.published'
            },
            'public_jwk_url': 'https://www.ejournal.app/jwk.json',
            'target_link_uri': settings.LTI_LAUNCH_URL,
            'oidc_initiation_url': settings.LTI_LOGIN_URL
        })
    else:
        return None  # LTI TODO: responses.bad_request('No LMS was selected')


@api_view(['POST'])
@permission_classes((AllowAny, ))
def launch(request):
    try:
        message_launch = lti.utils.eDjangoMessageLaunch(
            request, settings.TOOL_CONF, launch_data_storage=DjangoCacheDataStorage())
        launch_id = message_launch.get_launch_id()

        if message_launch.lti_version == settings.LTI1P3 and message_launch.is_deep_link_launch():
            launch_url = request.build_absolute_uri(reverse('lti_launch'))
            resource = eDeepLinkResource()
            resource.set_url(launch_url)
            resource.set_scope('*')

            html = message_launch.get_deep_link().output_response_form([resource])

            return HttpResponse(html)

        launch_data = message_launch.get_launch_data()
        print(launch_data)

        user = launch_data.user.find_in_db()
        if launch_data.user.is_test_student and not user:
            # NOTE: This will also delete other test students of the same course
            user = launch_data.user.create()

        # NOTE: user should see no_user_connected in one of three scenario's:
        if (
            # - User does not exist on the platform yet
            not user or
            # - User is already create (e.g. through Canvas API) and now needs to set password
            (not user.is_test_student and is_password_usable(user.password)) or
            # - User already exists on the platform with a valid password but never accessed eJournal through an LMS
            #   Then he needs to verify that he knowns the password he set on eJournal
            #   NOTE: in the case where lti_1p3_id is already set, yet the user never accessed it through LMS
            #   we accept that the user is the real user, and he doesnt need to verify anything. This check was
            #   mostly to prevent cases where LMS user would have the same username as a different eJournal user
            (not user.lti_1p0_id and not user.lti_1p3_id)
        ):
            return handle_no_user_connected_to_launch_data(launch_data, launch_id)

        if user:
            user = launch_data.user.update()

        print('LTI user:', user)

        course = launch_data.course.find_in_db()
        if course:
            course = launch_data.course.update()
        else:
            return handle_no_course_connected_to_launch_data(launch_data, launch_id, user)
        print('LTI course:', course)

        assignment = launch_data.assignment.find_in_db()
        if assignment:
            # QUESTION LTI:
            # before:
            # When an assignment is linked to multiple courses through the LMS, it would update to the
            # variables set by the last visited LMS assignment.
            # now:
            # I now changed it to only update it, if the assignment is also the actual active lti assignment.
            # Is this a good change?
            if assignment.active_lti_id == launch_data.assignment.active_lti_id:
                assignment = launch_data.assignment.update()
        else:
            return handle_no_assignment_connected_to_launch_data(launch_data, launch_id, user, course)
        print('LTI assignment:', assignment)

        journal = Journal.objects.filter(authors__user=user, assignment=assignment).first()
        if journal:
            author = journal.authors.get(user=user)
            # TODO LTI: only update if sth actually changed
            if launch_data.lti_version == settings.LTI1P0 and \
               launch_data.assignment.active_lti_id == assignment.active_lti_id:
                author.grade_url = launch_data.user.grade_url
                author.sourcedid = launch_data.user.sourcedid
                author.save()
        print('LTI journal:', journal)
        return handle_all_connected_to_launch_data(
            launch_data, launch_id, user, course, assignment, journal, request)

    except (KeyError, MultiValueDictKeyError) as err:
        raise VLEBadRequest(
            '{} is missing. Please contact the system administrator or support@ejournal.app'.format(err.args[0]))


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
