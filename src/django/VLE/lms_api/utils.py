import requests
from pylti1p3.exception import LtiException


def api_request(url, access_token, data=None, is_post=False, content_type='application/json'):
    headers = {
        'Authorization': 'Bearer ' + access_token,
    }

    if is_post:
        headers['Content-Type'] = content_type
        post_data = str(data) if data else None
        r = requests.post(url, data=post_data, headers=headers)
    else:
        r = requests.get(url, params={
            # 'state[]': ['available'],
            'include[]': ['students', 'total_students'],
        }, headers=headers)

    if r.status_code not in (200, 201):
        raise LtiException('HTTP response [%s]: %s - %s' % (url, str(r.status_code), r.text))

    return r
