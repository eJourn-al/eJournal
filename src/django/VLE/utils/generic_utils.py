"""
Utilities.

A library with useful functions.
"""
import base64
import re
import urllib
from datetime import datetime
from mimetypes import guess_extension

import dateutil.parser
from django.conf import settings
from django.core.files.base import ContentFile

import VLE.utils.error_handling


def required_params(post, *keys):
    """Get required post parameters, throwing KeyError if not present."""
    if keys and not post:
        raise VLE.utils.error_handling.VLEMissingRequiredKey(keys)

    result = []
    for key in keys:
        try:
            if post[key] == '':
                VLE.utils.error_handling.VLEMissingRequiredKey(key)
            result.append(post[key])
        except KeyError:
            raise VLE.utils.error_handling.VLEMissingRequiredKey(key)

    return result


def optional_params(post, *keys):
    """Get optional post parameters, filling them as None if not present."""
    if keys and not post:
        return [None] * len(keys)

    result = []
    for key in keys:
        if key in post and post[key] != '':
            result.append(post[key])
        else:
            result.append(None)
    return result


def cast_value(value, type, optional=False):
    if (
        value is None
        or optional and value == '' and type != str
    ):
        return None
    elif type == bool and value == 'false':
        return False
    elif type == bool and value == 'true':
        return True
    elif type == datetime:
        try:
            return datetime.strptime(value, settings.ALLOWED_DATETIME_FORMAT)
        except ValueError:
            # Not all incoming datetimes are regulated by us, e.g. LMS datetimes format can vary.
            return dateutil.parser.parse(value)
    else:
        return type(value)


def required_typed_params(data, *type_key_tuples):
    if type_key_tuples and not data:
        raise VLE.utils.error_handling.VLEMissingRequiredKey([tuple[1] for tuple in type_key_tuples])

    result = []
    for type, key in type_key_tuples:
        try:
            if data[key] == '':
                VLE.utils.error_handling.VLEMissingRequiredKey(key)
            if isinstance(data[key], list):
                result.append([cast_value(elem, type) for elem in data[key]])
            else:
                result.append(cast_value(data[key], type))
        except (ValueError, TypeError) as err:
            raise VLE.utils.error_handling.VLEParamWrongType(err)
        except KeyError:
            raise VLE.utils.error_handling.VLEMissingRequiredKey(key)

    return result


def optional_typed_params(data, *type_key_tuples):
    """Value can be None (data is '' or None) or missing (represented by None)"""
    if type_key_tuples and not data:
        return [None] * len(type_key_tuples)

    result = []
    for tuple_ in type_key_tuples:
        if len(tuple_) == 2:
            type_, key = tuple_
            default = None
        elif len(tuple_) == 3:
            type_, key, default = tuple_
        try:
            if isinstance(data[key], list):
                result.append([cast_value(elem, type_, optional=True) for elem in data[key]])
            else:
                result.append(cast_value(data[key], type_, optional=True))
        except (ValueError, TypeError) as err:
            raise VLE.utils.error_handling.VLEParamWrongType(err)
        except KeyError:
            result.append(default)

    return result
# END: API-POST functions


def get_value_from_dict(dic, key_list):
    '''Return a value from a dictionary by supplying a list of keys to interetly get the last value

    Example:
    get_value_from_dict({'a': 3}, ['a']) => 3
    get_value_from_dict({'a': [{}, {'b': 5}]}, ['a', 1, 'b']) => 5
    '''
    for key in key_list:
        dic = dic[key]
    return dic


def format_query_set_values_to_display(qry, key):
    qry_values = qry.values_list(key, flat=True)
    return ", ".join(map(lambda x: f'\"{x}\"', qry_values))


def base64ToContentFile(string, filename):
    matches = re.findall(r'data:(.*);base64,(.*)', string)[0]
    mimetype = matches[0]
    extension = guess_extension(mimetype)
    return ContentFile(base64.b64decode(matches[1]), name='{}{}'.format(filename, extension))


def build_url(baseurl, path, args_dict=None):
    url_parts = list(urllib.parse.urlparse(baseurl))
    url_parts[2] = path
    if args_dict is not None:
        url_parts[4] = urllib.parse.urlencode(args_dict)
    return urllib.parse.urlunparse(url_parts)
