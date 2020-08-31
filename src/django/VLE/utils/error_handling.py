from smtplib import SMTPAuthenticationError

import jwt
from django.core.exceptions import ObjectDoesNotExist, ValidationError

import VLE.utils.responses as response


class VLEBadRequest(Exception):
    def __init___(self, message='Your browser performed a bad request.'):
        super(VLEBadRequest, self).__init__(message)


class VLEMissingRequiredKey(KeyError):
    def __init__(self, err):
        if isinstance(err, KeyError):
            super(VLEMissingRequiredKey, self).__init__(err)
        elif isinstance(err, list) or isinstance(err, tuple):
            self.keys = err
        else:
            self.keys = [err]


class VLEParamWrongType(ValueError):
    pass


class VLEProgrammingError(Exception):
    pass


class VLEUnverifiedEmailError(Exception):
    def __init__(self, message='You need to verify your email address on your profile page first.'):
        super(VLEUnverifiedEmailError, self).__init__(message)


class VLEPermissionError(Exception):
    def __init__(self, permission=None, message=None):
        if message:
            super(VLEPermissionError, self).__init__(message)
        elif permission:
            super(VLEPermissionError, self).__init__('User does not have permission ' + permission)
        else:
            super(VLEPermissionError, self).__init__('User does not have the necessery permissions.')


class VLEParticipationError(Exception):
    def __init__(self, obj, logged_user):
        super(VLEParticipationError, self).__init__('User is not participating in ' + obj.to_string(logged_user))


class VLEMissingRequiredField(Exception):
    def __init__(self, field):
        self.field = field
        super(VLEMissingRequiredField, self).__init__('Missing required field: ' + field.to_string())


class LmsGradingResponseException(Exception):
    """Exception based on LMS error response whilest grading"""


class ErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Generic exception
        if isinstance(exception, VLEBadRequest):
            return response.bad_request(str(exception), exception=exception)

        # Django exceptions
        elif isinstance(exception, ObjectDoesNotExist):
            return response.not_found('{0} does not exist.'.format(str(exception).split()[0]), exception=exception)
        elif isinstance(exception, ValidationError):
            return response.validation_error(', '.join(exception.messages), exception=exception)

        # Variable exceptions
        elif isinstance(exception, VLEMissingRequiredKey):
            return response.key_error(exception.keys, exception=exception)
        elif isinstance(exception, VLEMissingRequiredField):
            return response.bad_request(str(exception), exception=exception)
        elif isinstance(exception, VLEParamWrongType):
            return response.value_error(str(exception), exception=exception)

        # Permission exceptions
        elif isinstance(exception, VLEParticipationError):
            return response.forbidden(str(exception), exception=exception)
        elif isinstance(exception, VLEPermissionError):
            return response.forbidden(str(exception), exception=exception)
        elif isinstance(exception, VLEUnverifiedEmailError):
            return response.forbidden(str(exception), exception=exception)

        # Programming exceptions
        elif isinstance(exception, VLEProgrammingError):
            return response.internal_server_error(str(exception), exception=exception)
        elif isinstance(exception, SMTPAuthenticationError):
            return response.internal_server_error(
                'Mailserver is not configured correctly, please contact a server admin.', exception=exception)

        # LTI exceptions
        elif isinstance(exception, jwt.exceptions.ExpiredSignatureError):
            return response.forbidden(
                'The LTI instance link has expired, 15 minutes have passed. Please try again.')
        elif isinstance(exception, jwt.exceptions.InvalidSignatureError):
            return response.unauthorized(
                'Invalid LTI parameters given. Please retry from your LTI instance or notify a server admin.',
                exception=exception)
