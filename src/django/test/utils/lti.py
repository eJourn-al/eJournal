import time
from urllib import parse

import jwt
import oauth2
from django.conf import settings
from django.test import RequestFactory
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import VLE.lti1p3 as lti
from VLE.models import User, access_gen

BASE_PARAMS = {
    'oauth_consumer_key': str(settings.LTI_KEY),
    'oauth_signature_method': 'HMAC-SHA1',
    'oauth_version': '1.0',
    'context_label': 'aaaa',
    'lti_message_type': 'basic-lti-launch-request',
    'lti_version': 'LTI-1p0',
}


def encode_lti_params(jwt_params):
    return jwt.encode(jwt_params, settings.SECRET_KEY, algorithm='HS256').decode('utf-8')


def get_signature(request):
    oauth_request = oauth2.Request.from_request('POST', 'http://testserver/lti/launch', parameters=request)
    oauth_consumer = oauth2.Consumer(settings.LTI_KEY, settings.LTI_SECRET)
    return oauth2.SignatureMethod_HMAC_SHA1().sign(oauth_request, oauth_consumer, {}).decode('utf-8')


def create_request_body(user=None, course=None, assignment=None, is_teacher=False):
    request = BASE_PARAMS.copy()

    if user:
        request = {
            **request,
            'custom_username': user.username,
            'custom_user_full_name': user.full_name,
            'custom_user_image': user.profile_picture,
            'user_id': user.lti_1p0_id or access_gen(),
        }
    else:
        n = User.objects.count()
        request = {
            **request,
            'custom_username': f'user_{n}_{access_gen(size=10)}',
            'custom_user_full_name': f'Fullname User{n}',
            'custom_user_image': 'https://canvas.instructure.com/images/messages/avatar-50.png',
            'user_id': access_gen(),
            'custom_user_email': f'email{access_gen(size=10)}@ejournal.app'
        }

    if is_teacher:
        request['roles'] = 'urn:lti:instrole:ims/lis/Instructor'

    if course:
        assert course.lms_id, 'course needs to be an LTI course'
        request['custom_course_id'] = course.lms_id
        request['custom_course_name'] = course.name
        request['custom_course_start'] = course.startdate
        request['context_label'] = course.abbreviation
    else:
        request['custom_course_id'] = access_gen()
        request['custom_course_name'] = 'LTI course ' + access_gen(size=10)
        request['context_label'] = access_gen(size=3)
        request['custom_course_start'] = '2018-06-15 14:41:00 +0200'

    if assignment:
        assert assignment.active_lti_id, 'assignment needs to be an LTI assignment'
        request['custom_assignment_id'] = assignment.active_lti_id
        request['custom_assignment_title'] = assignment.name
        request['custom_assignment_unlock'] = assignment.unlock_date
        request['custom_assignment_due'] = assignment.due_date
        request['custom_assignment_lock'] = assignment.lock_date
        request['custom_assignment_points'] = assignment.points_possible
        request['custom_assignment_publish'] = ('false', 'true')[assignment.is_published]
    else:
        request['custom_assignment_id'] = access_gen()
        request['custom_assignment_title'] = 'LTI assignment ' + access_gen(size=10)
        request['custom_assignment_points'] = 10
        request['custom_assignment_publish'] = 'true'

    return request


def gen_jwt_params(params={}, user=None, course=None, assignment=None, is_teacher=False, to_launch_id=False):
    """Generates valid JWT parameters.

    Params can overwrite all results, including timestamp, nonce and signature to produce an invalid request."""
    req = create_request_body(user=user, course=course, assignment=assignment, is_teacher=is_teacher)

    req['oauth_timestamp'] = str(int(time.time()))
    req['oauth_nonce'] = str(oauth2.generate_nonce())

    req = {**req, **params}

    if 'oauth_signature' not in params:
        req['oauth_signature'] = get_signature(req)

    if not to_launch_id:
        return {'jwt_params': encode_lti_params(req)}

    request = RequestFactory().post('http://127.0.0.1:8000/lti/launch', req)
    resp = lti.launch.launch(request)
    return {'launch_id': resp.url.split('launch_id=')[-1].split('&')[0]}, req


def get_new_lti_id():
    user = User.objects.exclude(lti_1p0_id=None).latest('lti_1p0_id')
    return '1' if not (user or user.lti_1p0_id) else '{}{}'.format(user.lti_1p0_id, 1)


def get_access_token(user):
    return str(TokenObtainPairSerializer.get_token(user).access_token)


def lti_launch_response_to_access_token(response):
    return dict(parse.parse_qsl(parse.urlsplit(response.url).query))['jwt_access']
