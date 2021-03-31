from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.datastructures import MultiValueDictKeyError
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoOIDCLogin
from pylti1p3.deep_link_resource import DeepLinkResource
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import VLE.lti1p3 as lti
from VLE.models import Instance, Journal, User
from VLE.utils.error_handling import VLEBadRequest
from VLE.utils.generic_utils import build_url


class eDeepLinkResource(DeepLinkResource):
    _scope = None

    def set_scope(self, scope):
        self._scope = scope

    def to_dict(self):
        dic = super().to_dict()
        dic = {
            'scope': self._scope,
            **dic,
        }
        return dic


def handle_no_user_connected_to_launch_data(launch_data, launch_id):
    username = launch_data.user.username
    if username:
        already_exists = User.objects.filter(username=username).exists()
    else:
        already_exists = False
    response_data = {
        'launch_state': lti.utils.LTI_STATES.NO_USER.value,
        'launch_id': launch_id,
        'username_already_exists': already_exists,
        'name': launch_data.user.full_name or launch_data.user.username,
        # TODO LTI: add journal & course & assignment id to this list
    }
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
            lti.utils.LTI_STATES.FINISH_TEACHER.value if user.is_teacher else lti.utils.LTI_STATES.FINISH_STUDENT.value,
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
        return None  # TODO LTI: responses.bad_request('No LMS was selected')


@api_view(['POST'])
@permission_classes((AllowAny, ))
def launch(request):
    try:
        message_launch = lti.utils.eDjangoMessageLaunch(
            request, settings.TOOL_CONF, launch_data_storage=DjangoCacheDataStorage())
        launch_id = message_launch.get_launch_id()

        if message_launch.lti_version == settings.LTI13 and message_launch.is_deep_link_launch():
            launch_url = request.build_absolute_uri(reverse('lti_launch'))
            resource = eDeepLinkResource()
            resource.set_url(launch_url)
            resource.set_scope('*')

            html = message_launch.get_deep_link().output_response_form([resource])

            return HttpResponse(html)

        launch_data = message_launch.get_launch_data()
        print(launch_data)

        user = launch_data.user.find_in_db()
        if user:
            user = launch_data.user.update()
        elif launch_data.user.is_test_student and not launch_data.user.find_in_db():
            # NOTE: This will also delete older test students
            user = launch_data.user.create()

        # TODO LTI: change to is initialized user or not (cuz lti_id can be set with the roles service)
        # TODO LTI: also add the check for user alsready exists, but needs to set a password anyway
        # TODO LTI: also also check if user already exists with valid password, but it has never accessed it through
        # LTI, and it needs to verify the password
        if not user:
            return handle_no_user_connected_to_launch_data(launch_data, launch_id)
        print('LTI user:', user)

        course = launch_data.course.find_in_db()
        if course:
            course = launch_data.course.update()
        if not course:
            return handle_no_course_connected_to_launch_data(launch_data, launch_id, user)
        print('LTI course:', course)

        assignment = launch_data.assignment.find_in_db()
        if assignment:
            # QUESTION: before:
            # When an assignment is linked to multiple courses through the LMS, it would update to the
            # variables set by the last visited LMS assignment.
            # now:
            # I now changed it to only update it, if the assignment is also the actual active lti assignment.
            # Is this a good change?
            if assignment.active_lti_id == launch_data.assignment.active_lti_id:
                assignment = launch_data.assignment.update()
        if not assignment:
            return handle_no_assignment_connected_to_launch_data(launch_data, launch_id, user, course)
        print('LTI assignment:', assignment)

        journal = Journal.objects.filter(authors__user=user, assignment=assignment).first()
        if journal:
            author = journal.authors.get(user=user)
            # TODO LTI: only update if sth actually changed
            if launch_data.lti_version == settings.LTI10 and \
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
