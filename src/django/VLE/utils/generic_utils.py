"""
Utilities.

A library with useful functions.
"""
import base64
import re
from datetime import datetime
from mimetypes import guess_extension

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
    if value is None:
        return None

    if type == bool and value == 'false':
        return False
    elif type == datetime:
        if optional and value == '':
            return None
        return datetime.strptime(value, settings.ALLOWED_DATETIME_FORMAT)
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
        except ValueError as err:
            raise VLE.utils.error_handling.VLEParamWrongType(err)
        except KeyError:
            raise VLE.utils.error_handling.VLEMissingRequiredKey(key)

    return result


def optional_typed_params(data, *type_key_tuples):
    if type_key_tuples and not data:
        return [None] * len(type_key_tuples)

    result = []
    for type, key in type_key_tuples:
        try:
            if isinstance(data[key], list):
                result.append([cast_value(elem, type, optional=True) for elem in data[key]])
            else:
                result.append(cast_value(data[key], type, optional=True))
        except ValueError as err:
            raise VLE.utils.error_handling.VLEParamWrongType(err)
        except KeyError:
            result.append(None)

    return result


def base64ToContentFile(string, filename):
    matches = re.findall(r'data:(.*);base64,(.*)', string)[0]
    mimetype = matches[0]
    extension = guess_extension(mimetype)
    return ContentFile(base64.b64decode(matches[1]), name='{}{}'.format(filename, extension))
