import time
from urllib import parse

import jwt
import oauth2
from django.conf import settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from VLE.models import User

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


def gen_jwt_params(params={}, user=None):
    """Generates valid JWT parameters.

    Params can overwrite all results, including timestamp, nonce and signature to produce an invalid request."""
    req = BASE_PARAMS.copy()

    if user:
        req = {
            **req,
            **{
                'roles': settings.ROLES['Teacher'][0] if user.is_teacher else settings.ROLES['Student'][0],
                'user_id': user.lti_id,
                'custom_username': user.username,
                'custom_user_email': user.email,
                'custom_user_full_name': user.full_name,
            },
        }

    req['oauth_timestamp'] = str(int(time.time()))
    req['oauth_nonce'] = str(oauth2.generate_nonce())

    req = {**req, **params}

    if 'oauth_signature' in params:
        req['oauth_signature'] = req['oauth_signature']
    else:
        req['oauth_signature'] = get_signature(req)

    return {'jwt_params': encode_lti_params(req)}


def get_new_lti_id():
    user = User.objects.exclude(lti_1p0_id=None).latest('lti_1p0_id')
    return '1' if not (user or user.lti_1p0_id) else '{}{}'.format(user.lti_1p0_id, 1)


def get_access_token(user):
    return str(TokenObtainPairSerializer.get_token(user).access_token)


def lti_launch_response_to_access_token(response):
    return dict(parse.parse_qsl(parse.urlsplit(response.url).query))['jwt_access']
