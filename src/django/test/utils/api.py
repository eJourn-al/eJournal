"""
utils.py

Helpter function for the test enviroment.
"""

import json
import test.factory.user as userfactory

import VLE.utils.generic_utils as utils

from django.urls import reverse


def format_url(obj, url, params, function):
    # set primary key if its not a create, when no pk is supplied, default to 0
    if function != obj.client.post:
        pk = params.pop('pk', None)
        if pk is not None:
            s = url.split('/')
            s.insert(1, str(pk))
            url = '/'.join(s)

    # add / to from and back
    if url[0] != '/':
        url = '/' + url
    if url[-1] != '/':
        url += '/'

    # add params to the url if it cant have a body
    if function in [obj.client.get, obj.client.delete]:
        url += '?'
        for key, value in params.items():
            url += '{}={}&'.format(key, value)
        # Remove last & or ? when there are no params
        url = url[:-1]

    return url


def login(obj, user, password=userfactory.DEFAULT_PASSWORD, status=200):
    """Login using username and password.

    Arguments:
    user -- user to login as, this is generated by the setup_user from generic_utils
    status -- status it checks for after login (default 200)

    Returns the loggin in user.
    """
    return post(obj, reverse('token_obtain_pair'),
                params={'username': user.username, 'password': password}, status=status)


def test_rest(obj, url, create_params=None, delete_params=None, update_params=None, get_params=None,
              get_is_create=True, user=None, password=userfactory.DEFAULT_PASSWORD,
              create_status=201, get_status=200, delete_status=200, get_status_when_unauthorized=401):
    # Create the object that is given
    create_object = create(obj, url, params=create_params, user=user, password=password, status=create_status)
    if create_status != 201:
        return
    create_object.pop('description', None)
    pk, = utils.required_typed_params(list(create_object.values())[0], (int, 'id'))

    # Get that same object
    if get_params is None:
        get_params = dict()
    get(obj, url, params={'pk': pk, **get_params}, status=get_status_when_unauthorized)
    get_object = get(obj, url, params={'pk': pk, **get_params}, user=user, password=password, status=get_status)
    get_object.pop('description', None)

    # Check if the created object is the same as the one it got
    if get_is_create and get_status == 200:
        assert create_object == get_object, 'Created object does not equal the get result.'

    # Update the object
    if update_params is not None:
        if not isinstance(update_params, list):
            update_params = [update_params]

        for to_update in update_params:
            changes, status = utils.optional_params(to_update, 'changes', 'status')
            if changes is None and status is None:
                changes = to_update
            if status is None:
                status = 200
            changes['pk'] = pk
            update_object = update(obj, url, params=changes, user=user, password=password, status=status)
            update_object.pop('description', None)

    # Delete the object
    if delete_params is None:
        delete_params = dict()
    delete(obj, url, params={'pk': pk, **delete_params}, user=user, password=password, status=delete_status)


def get(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=200, access=None):
    return call(obj, obj.client.get, url,
                params=params, user=user, password=password, status=status, access=access)


def get_list(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=200, access=None):
    return call(obj, obj.client.get, url,
                params=params, user=user, password=password, status=status, access=access)


def create(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=201, access=None):
    return call(obj, obj.client.post, url,
                params=params, user=user, password=password, status=status, access=access)


def post(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=200,
         content_type='application/json', access=None):
    return call(obj, obj.client.post, url,
                params=params, user=user, password=password, status=status, content_type=content_type, access=access)


def update(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=200,
           content_type='application/json', access=None):
    return call(obj, obj.client.patch, url,
                params=params, user=user, password=password, status=status, content_type=content_type, access=access)


def patch(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=200,
          content_type='application/json', access=None):
    return call(obj, obj.client.patch, url,
                params=params, user=user, password=password, status=status, content_type=content_type)


def delete(obj, url, params=None, user=None, password=userfactory.DEFAULT_PASSWORD, status=200, access=None):
    return call(obj, obj.client.delete, url,
                params=params, user=user, password=password, status=status, access=access)


def call(obj, function, url, params=None,
         user=None, password=userfactory.DEFAULT_PASSWORD,
         status=200, status_when_unauthorized=401,
         content_type='application/json', access=None):
    # Set params to an empty dictionary when its None this cant be done in the parameters themself as that can give
    # unwanted results when calling the function multiple times
    if params is None:
        params = dict()
    params = params.copy()

    url = format_url(obj, url, params, function)

    if user is None:
        if function in [obj.client.get, obj.client.delete]:
            response = function(url, content_type=content_type)
        else:
            if content_type != 'application/json':
                response = function(url, params)
            else:
                response = function(url, json.dumps(params), content_type=content_type)
    else:
        # A test student does not login via password
        if not access:
            logged_user = login(obj, user, password)
            access, = utils.required_params(logged_user, 'access')
        if function in [obj.client.get, obj.client.delete]:
            response = function(url, content_type=content_type, HTTP_AUTHORIZATION='Bearer ' + access)
        else:
            if content_type != 'application/json':
                response = function(url, params, HTTP_AUTHORIZATION='Bearer ' + access)
            else:
                response = function(url, json.dumps(params), content_type=content_type,
                                    HTTP_AUTHORIZATION='Bearer ' + access)
    try:
        result = response.json()
    except (AttributeError, ValueError):
        result = response

    assert response.status_code == status, \
        'Request status did not match the expected response. Expected {}, but got {}: {}'.format(status,
                                                                                                 response.status_code,
                                                                                                 result)
    return result
