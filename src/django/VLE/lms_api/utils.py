import json

import jwt
import requests
import sentry_sdk
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

import VLE.utils.responses as response
from pylti1p3.exception import LtiException
from VLE.lms_api import groups
from VLE.models import Instance, User
from VLE.utils.generic_utils import build_url


def decode_params(jwt_params):
    return jwt.decode(jwt_params, settings.SECRET_KEY, algorithms=['HS256'])


def encode_params(jwt_params):
    return jwt.encode(jwt_params, settings.SECRET_KEY, algorithm='HS256').decode('utf-8')


def redirect_access_token_retrieval(user, action, identifier):
    instance = Instance.objects.get_or_create(pk=1)[0]
    return response.success({'redirect_uri': build_url(
        instance.lms_url,
        'login/oauth2/auth',
        {
            'response_type': 'code',
            'redirect_uri': build_url(settings.API_URL, 'lms/authenticate/'),
            'scope': settings.CANVAS_API_SCOPES,
            'client_id': instance.api_client_id,
            'state': encode_params({
                'user_pk': user.pk,
                'action': action,
                'identifier': identifier
            })
        }
    )})


def do_lms_api_action(user, action, identifier):
    '''Do the API call with the LMS according to the params.

    Before calling the API, it first checks (and possibly requests) the acces token of the user
    Only after it has an access token, it will perform the API call.

    user - user performing the API call
    action - API action that the user wants to perform
    identifier - identifier of the action (e.g. course id to track for which course it is)
    '''
    if not user.access_token:
        return redirect_access_token_retrieval(user, action, identifier)

    try:
        lms_actions = {
            settings.CANVAS_API_ACTIONS['SYNC_GROUPS']: groups.sync_groups,
        }

        lms_actions[action](user.access_token, identifier)
        return HttpResponse(get_template('succes_tab.html').render())
    except Exception as exception:
        # Reset Access token because if something went wrong, invalid access token could be the cause
        user.access_token = None
        user.save()
        with sentry_sdk.push_scope() as scope:
            scope.level = 'warning'
            sentry_sdk.capture_exception(exception)
        return HttpResponse(get_template('wrong_tab.html').render())


@api_view(['GET'])
@permission_classes((AllowAny, ))
def lms_authenticate(request):
    """User authorized us to retrieve data.

    Insire request params:
        status: this specifies the data to retrieve and the context to retrieve it with
        code: code used to retrieve the access_token
    """
    instance = Instance.objects.get_or_create(pk=1)[0]
    state = decode_params(request.query_params['state'])

    resp = requests.post(instance.auth_token_url, data={
        'grant_type': 'authorization_code',
        'code': request.query_params['code'],
        'client_id': instance.api_client_id,
        'client_secret': instance.api_client_secret,
        'redirect_uri': settings.API_URL + '/lms/authenticate/'
    })
    response = json.loads(resp.content)
    access_token = response['access_token']

    user = User.objects.get(pk=state['user_pk'])
    user.access_token = access_token
    user.save()

    return do_lms_api_action(user, state['action'], state['identifier'])


def api_request(url, access_token, params=None, data=None, is_post=False, content_type='application/json'):
    headers = {
        'Authorization': 'Bearer ' + access_token,
    }

    if is_post:
        headers['Content-Type'] = content_type
        post_data = str(data) if data else None
        r = requests.post(url, data=post_data, headers=headers)
    else:
        r = requests.get(url, params=params, headers=headers)

    if r.status_code not in (200, 201):
        raise LtiException('HTTP response [%s]: %s - %s' % (url, str(r.status_code), r.text))

    return r
