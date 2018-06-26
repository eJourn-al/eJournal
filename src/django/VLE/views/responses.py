"""
responses.py

"""
from django.http import JsonResponse


def success(message='success', payload={}):
    """Return a success response header.

    Arguments:
    payload -- payload to deliver on success
    """
    return response(200, message, payload=payload)


def created(message='success', payload={}):
    """Return a created response header.

    Arguments:
    payload -- payload to deliver after creation
    """
    return response(201, message, payload=payload)


def no_content(description=''):
    """Return a no content header.

    Arguments:
    description -- header description (usable for example in the front end)
    """

    return response(204, '204 No content', description=description)


def bad_request(description=''):
    """Return a bad request response header.

    Arguments:
    description -- header description (usable for example in the front end)
    """
    return response(400, '400 Bad Request', description=description)


def unauthorized(description=''):
    """Return an unauthorized response header.

    Arguments:
    description -- header description (usable for example in the front end)
    """
    return response(401, '401 Authentication Error', description=description)


def forbidden(description=''):
    """Return a forbidden response header.

    Arguments:
    description -- header description (usable for example in the front end)
    """
    return response(403, '403 Forbidden', description=description)


def not_found(description=''):
    """Return a not found response header.

    Arguments:
    description -- header description (usable for example in the front end)
    """
    return response(404, '404 Not Found', description=description)


def response(status, message, description='', payload={}):
    """Return a generic response header with customizable fields.

    Arguments:
    status -- HTTP status number
    message -- response message
    description -- header description (usable for example in the front end)
    payload -- payload to deliver
    """
    return JsonResponse({'result': message, 'description': description, **payload}, status=status)


def keyerror(*keys):
    """Generate a JsonResponse when the JSON has keyerror(s)."""
    if len(keys) == 1:
        return bad_request('Field {0} is required but is missing.'.format(keys))
    else:
        return bad_request('Fields {0} are required but one or more are missing.'.format(keys))