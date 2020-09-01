from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from pylti1p3.contrib.django import DjangoCacheDataStorage
from pylti1p3.deep_link_resource import DeepLinkResource
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import VLE.lti1p3 as lti
from VLE.lti1p3 import assignment, course, members, user, utils
from VLE.models import Assignment, Course, Instance, Journal, User
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


def check_and_handle_test_student(user, message_launch_data):
    """Creates a test user if no user is proved and lauch is with test student"""
    if user or not lti.utils.is_test_student_launch(message_launch_data):
        return user

    course = Course.objects.filter(active_lti_id=message_launch_data.get(lti.claims.COURSE)['id']).first()
    if course:
        User.objects.filter(participation__course=course, is_test_student=True).delete()
    # TODO: remove all previous test students in course
    return lti.user.create_with_launch_data(message_launch_data)


def handle_no_user_connected_to_launch_data(message_launch_data, launch_id):
    username = message_launch_data.get(lti.claims.CUSTOM)['username']
    already_exists = User.objects.filter(username=username).exists()
    response_data = {
        'launch_state': lti.utils.LTI_STATES.NO_USER.value,
        'launch_id': launch_id,
        'username_already_exists': already_exists,
        'name': message_launch_data.get('name', username),
    }
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


def handle_no_course_connected_to_launch_data(message_launch_data, launch_id, user):
    refresh = TokenObtainPairSerializer.get_token(user)
    response_data = {
        'launch_state':
            lti.utils.LTI_STATES.NO_COURSE.value if user.is_teacher else lti.utils.LTI_STATES.NOT_SETUP.value,
        'launch_id': launch_id,
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
    }
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


def handle_no_assignment_connected_to_launch_data(message_launch_data, launch_id, user, course):
    refresh = TokenObtainPairSerializer.get_token(user)
    response_data = {
        'launch_state':
            lti.utils.LTI_STATES.NO_ASSIGNMENT.value if user.is_teacher else lti.utils.LTI_STATES.NOT_SETUP.value,
        'launch_id': launch_id,
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
        'course_id': course.id,
    }
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


def handle_all_connected_to_launch_data(message_launch_data, launch_id, user, course, assignment, journal, request):
    refresh = TokenObtainPairSerializer.get_token(user)
    response_data = {
        'launch_state':
            lti.utils.LTI_STATES.FINISH_TEACHER.value if user.is_teacher else lti.utils.LTI_STATES.FINISH_STUDENT.value,
        'launch_id': launch_id,
        'jwt_access': str(refresh.access_token),
        'jwt_refresh': str(refresh),
        'course_id': course.id,
        'assignment_id': assignment.id,
        # Go directly to journal if it is a submission url, i.e. the gradebook or student launch
        'journal_id': request.query_params.get('submission', journal.pk if journal else ''),
    }
    return redirect(build_url(settings.BASELINK, 'LtiLogin', response_data))


@api_view(['POST', 'GET'])
@permission_classes((AllowAny, ))
def lti_launch(request):
    if request.method == 'POST':
        api_scopes_authorized = False
        message_launch = lti.utils.ExtendedDjangoMessageLaunch(
            request, settings.TOOL_CONF, launch_data_storage=DjangoCacheDataStorage())
        launch_id = message_launch.get_launch_id()
    else:
        # Path after authorization
        # TODO LTI: throw error if status does not exist
        api_scopes_authorized = True
        launch_id = request.query_params['state']
        message_launch = lti.utils.get_launch_from_id(launch_id, request)

    message_launch_data = message_launch.get_launch_data()

    # Check if it is an initial assignment setup
    if message_launch.is_deep_link_launch():
        # TODO LTI: find out how we can detect if we already are authorized to access these scopes, if not, request them, else go directly to HttpResponse
        # if not api_scopes_authorized:
        #     return redirect("http://canvas.docker/login/oauth2/auth?response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1:8000/lti/launch/&scope=url%3AGET%7C%2Fapi%2Fv1%2Fcourses%2F%3Acourse_id%2Fsections&client_id=10000000000002&state={}".format(launch_id))

        launch_url = request.build_absolute_uri(reverse('lti_launch'))
        resource = eDeepLinkResource()
        resource.set_url(launch_url)
        resource.set_scope('*')

        html = message_launch.get_deep_link().output_response_form([resource])

        return HttpResponse(html)

    try:
        user = lti.user.get_and_update_user_with_launch_data(message_launch_data)
        user = check_and_handle_test_student(user, message_launch_data)
        # TODO LTI: change to is initialized user or not (cuz lti_id can be set with the roles service)
        if not user:
            return handle_no_user_connected_to_launch_data(message_launch_data, launch_id)

        course = lti.course.get_and_update_course_with_launch_data(message_launch_data)
        if not course:
            return handle_no_course_connected_to_launch_data(message_launch_data, launch_id, user)

        assignment = lti.assignment.get_and_update_assignment_with_launch_data(message_launch_data)
        if not assignment:
            return handle_no_assignment_connected_to_launch_data(message_launch_data, launch_id, user, course)

        journal = Journal.objects.filter(authors__user=user, assignment=assignment).first()
        return handle_all_connected_to_launch_data(
            message_launch_data, launch_id, user, course, assignment, journal, request)

    except KeyError as err:
        raise VLEBadRequest(
            '{} is missing. Please contact the system administrator or support@ejournal.app'.format(err.args[0]))
