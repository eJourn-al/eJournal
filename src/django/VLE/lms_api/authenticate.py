import json

import requests
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

import VLE.lti1p3 as lti
from VLE.models import Instance


@api_view(['GET'])
@permission_classes((AllowAny, ))
def lms_authenticate(request):
    """User authorized us to retrieve data.

    Insire request params:
        status: this specifies the data to retrieve and the context to retrieve it with
        code: code used to retrieve the access_token
    """
    print(request)
    print(request.query_params)
    instance = Instance.objects.get(pk=1)
    resp = requests.post(instance.auth_token_url, data={
        'grant_type': 'authorization_code',
        'code': request.query_params['code'],
        'client_id': instance.api_client_id,
        'client_secret': instance.api_client_secret,
        'redirect_uri': settings.API_URL + '/lms/authenticate/'
    })
    response = json.loads(resp.content)
    access_token = response['access_token']

    # TODO LTI: return nice display that it is done, and you may close the tab.
    return JsonResponse(data=lti.groups.sync_groups(access_token))
