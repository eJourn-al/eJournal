import json

import requests
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
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
    # TODO LTI: do not continuesly re-request integration. Appearently you can extand expeiration date
    # Everytime someone uses FBF, the expiration date gets postponed by 1 hour
    instance = Instance.objects.get_or_create(pk=1)[0]
    action, pk = request.query_params['state'].split('-')

    resp = requests.post(instance.auth_token_url, data={
        'grant_type': 'authorization_code',
        'code': request.query_params['code'],
        'client_id': instance.api_client_id,
        'client_secret': instance.api_client_secret,
        'redirect_uri': settings.API_URL + '/lms/authenticate/'
    })
    response = json.loads(resp.content)
    access_token = response['access_token']

    if action == 'SYNC_GROUPS':
        lti.groups.sync_groups(access_token, course_id=pk)
        return HttpResponse(get_template('succes_tab.html').render(request=request))
    else:
        return HttpResponse(get_template('wrong_tab.html').render(request=request))
