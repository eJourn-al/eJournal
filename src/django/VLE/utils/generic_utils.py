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


# START: API-POST functions
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


# TODO Category: Extract conversion logic and reuse in params funcs
def convert_data_to_expected_type(typed_field, data):
    type = typed_field.type
    key = typed_field.key

    if data[key] is None:
        return None

    try:
        if type == bool and data[key] == 'false':
            return False
        elif type == datetime.datetime:
            return datetime.strptime(data[key], settings.ALLOWED_DATETIME_FORMAT)
        else:
            return type(data[key])
    except ValueError as err:
        raise VLE.utils.error_handling.VLEParamWrongType(err)


def required_typed_params(post, *keys):
    if keys and not post:
        raise VLE.utils.error_handling.VLEMissingRequiredKey([key[1] for key in keys])

    result = []
    for func, key in keys:
        try:
            if post[key] == '':
                VLE.utils.error_handling.VLEMissingRequiredKey(key)
            if isinstance(post[key], list):
                result.append([func(elem) for elem in post[key]])
            elif post[key] is not None:
                if func == bool and post[key] == 'false':
                    result.append(False)
                elif func == datetime:
                    result.append(datetime.strptime(post[key], settings.ALLOWED_DATETIME_FORMAT))
                else:
                    result.append(func(post[key]))
            else:
                result.append(None)
        except ValueError as err:
            raise VLE.utils.error_handling.VLEParamWrongType(err)
        except KeyError:
            raise VLE.utils.error_handling.VLEMissingRequiredKey(key)

    return result


def optional_typed_params(post, *keys):
    if keys and not post:
        return [None] * len(keys)

    result = []
    for func, key in keys:
        if key and key in post and post[key] != '':
            try:
                if post[key] is not None:
                    if func == bool and post[key] == 'false':
                        result.append(False)
                    elif func == datetime:
                        result.append(datetime.strptime(post[key], settings.ALLOWED_DATETIME_FORMAT))
                    else:
                        result.append(func(post[key]))
                else:
                    result.append(None)
            except ValueError as err:
                raise VLE.utils.error_handling.VLEParamWrongType(err)
        else:
            result.append(None)

    return result
# END: API-POST functions


def base64ToContentFile(string, filename):
    matches = re.findall(r'data:(.*);base64,(.*)', string)[0]
    mimetype = matches[0]
    extension = guess_extension(mimetype)
    return ContentFile(base64.b64decode(matches[1]), name='{}{}'.format(filename, extension))
