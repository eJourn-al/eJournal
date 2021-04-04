import enum
import json

import oauth2
import sentry_sdk
from dateutil import parser
from django.conf import settings
from django.db.models import Q
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch
from pylti1p3.exception import LtiException

import VLE.lti1p3 as lti
from VLE.utils.error_handling import VLEMissingRequiredKey

# TODO lti: check if SectionsService import is working correctly


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(DatetimeEncoder, obj).default(obj)
        except TypeError:
            return str(obj)


class OAuthRequestValidater(object):
    """OAuth request validater class for Django Requests"""

    def __init__(self, key, secret):
        """
        Constructor which creates a consumer object with the given key and
        secret.
        """
        super(OAuthRequestValidater, self).__init__()
        self.consumer_key = key
        self.consumer_secret = secret

        self.oauth_server = oauth2.Server()
        signature_method = oauth2.SignatureMethod_HMAC_SHA1()
        self.oauth_server.add_signature_method(signature_method)
        self.oauth_consumer = oauth2.Consumer(self.consumer_key, self.consumer_secret)

    def parse_request(self, request):
        """
        Parses a django request to return the method, url, header and post data.
        """
        return request.method, request.build_absolute_uri(), request.META, request.POST.dict()

    def is_valid(self, request):
        """
        Checks if the signature of the given request is valid based on the
        consumers secret en key
        """
        method, url, head, param = self.parse_request(request)
        # print(method, url, head, param)
        oauth_request = oauth2.Request.from_request(method, url, headers=head, parameters=param)
        # print(oauth_request)
        self.oauth_server.verify_request(oauth_request, self.oauth_consumer, {})

    @classmethod
    def check_signature(cls, key, secret, request):
        """Validate OAuth request using the python-oauth2 library.

        https://github.com/simplegeo/python-oauth2.
        """
        validator = OAuthRequestValidater(key, secret)
        validator.is_valid(request)


class LTI_STATES(enum.Enum):
    """VUE ENTRY STATE."""
    NOT_SETUP = '-1'

    NO_USER = '0'

    NO_COURSE = '1'
    NO_ASSIGNMENT = '2'
    FINISH_TEACHER = '3'
    FINISH_STUDENT = '4'


class PreparedData(object):
    '''PreparedData

    This class can be used to prepare received data from other sources (e.g. LTI).

    Attributes to set:
        model - model that the data is preparing for
        data - the raw data
        create_keys - model keys to set during creation
        update_keys - model keys to set during update
        find_keys - model keys to use to find the model from database
    '''
    _db_obj = None

    def __init__(self, data):
        self.data = data

    def to_datetime(self, string):
        if not string:
            return None
        return parser.parse(string)

    def to_float(self, string):
        if not string:
            return None
        return float(string)

    def to_str(self, string):
        if not string:
            return None
        return str(string)

    def to_bool(self, string):
        if not string:
            return None
        return bool(string)

    def get_required(self, obj, key):
        if key not in obj:
            raise VLEMissingRequiredKey(key)
        return obj[key]

    def create_dict(self, debug=False):
        if not debug:
            return {
                key: getattr(self, key)
                for key in self.create_keys
            }

        dic = {}
        for key in self.create_keys:
            try:
                dic[key] = getattr(self, key)
            except VLEMissingRequiredKey:
                dic[key] = 'MISSING REQUIRED KEY'

        return dic

    def update_dict(self, debug=False):
        if not debug:
            return {
                key: getattr(self, key)
                for key in self.update_keys
            }

        dic = {}
        for key in self.update_keys:
            try:
                dic[key] = getattr(self, key)
            except VLEMissingRequiredKey:
                dic[key] = 'MISSING REQUIRED KEY'

        return dic

    @property
    def find_or_qry(self):
        qry = Q()
        for key in self.find_keys:
            if getattr(self, key) is not None:
                qry.add(Q(**{key: getattr(self, key)}), Q.OR)

        return qry

    @property
    def find_and_qry(self):
        qry = Q()
        for key in self.find_keys:
            qry.add(Q(**{key: getattr(self, key)}), Q.AND)

        return qry

    def find_in_db(self, force_from_db=False):
        if self._db_obj and not force_from_db:
            return self._db_obj

        # Dont search in DB when there are only none values to find the model
        if not self.find_or_qry:
            return None

        # QUESTION LTI: what to do for this? Now it selects the first one
        if self.model.objects.filter(self.find_or_qry).count() > 1:
            with sentry_sdk.push_scope() as scope:
                scope.level = 'warning'
                try:
                    scope.set_context('data', self.asdict())
                except Exception:
                    pass
                sentry_sdk.capture_message(
                    f'During data preperation, multiple {self.model.__name__} instances were found in the database.',
                )

        # Store in model, so it is cached later on
        self._db_obj = self.model.objects.filter(self.find_or_qry).first()

        return self._db_obj

    def create(self):
        return NotImplemented

    def update(self, obj=None):
        return NotImplemented

    def create_or_update(
        self,
        find_args=[], find_kwargs={},
        update_args=[], update_kwargs={},
        create_args=[], create_kwargs={},
    ):
        obj = self.find_in_db(*find_args, **find_kwargs)
        if obj:
            return self.update(*update_args, obj=obj, **update_kwargs)

        return self.create(*create_args, **create_kwargs)

    def asdict(self, debug=False):
        try:
            in_db = bool(self.find_in_db())
        except VLEMissingRequiredKey:
            in_db = 'UNKNOWN'

        dic = {
            **self.create_dict(debug=debug),
            **self.update_dict(debug=debug),
            'create_keys': self.create_keys,
            'update_keys': self.update_keys,
            'find_keys': self.find_keys,
            'in_database': in_db,
        }
        if debug:
            dic['debug_keys'] = {
                key: getattr(self, key)
                for key in self.debug_keys
            }

        return dic

    def __str__(self):
        return json.dumps(self.asdict(debug=True), sort_keys=False, indent=4, cls=DatetimeEncoder)


class eMessageLaunchData(object):
    def __init__(self, message_launch_data, lti_version):
        self.raw_data = message_launch_data

        self.lti_version = lti_version

        if self.lti_version == settings.LTI13:
            self.user = lti.user.Lti1p3UserData(message_launch_data)
            self.course = lti.course.Lti1p3CourseData(message_launch_data)
            self.assignment = lti.assignment.Lti1p3AssignmentData(message_launch_data)
        else:
            self.user = lti.user.Lti1p0UserData(message_launch_data)
            self.course = lti.course.Lti1p0CourseData(message_launch_data)
            self.assignment = lti.assignment.Lti1p0AssignmentData(message_launch_data)

    def asdict(self):
        user = self.user.asdict()

        course = self.course.asdict()
        if course['author']:
            course['author'] = course['author'].pk

        assignment = self.assignment.asdict()
        if assignment['author']:
            assignment['author'] = assignment['author'].pk
        if hasattr(assignment, 'connected_course') and assignment['connected_course']:
            assignment['connected_course'] = assignment['connected_course'].pk

        return {
            'user': user,
            'course': course,
            'assignment': assignment,
        }

    def __str__(self):
        return json.dumps({
            'raw data': self.raw_data,
            **self.asdict(),
        }, sort_keys=False, indent=4, cls=DatetimeEncoder)


class eDjangoMessageLaunch(DjangoMessageLaunch):
    @property
    def lti_version(self):
        '''Get the LTI version of the launch.'''
        print(self._jwt.get('body', {}).get('lti_version'))
        print(self._request._request.POST.get('lti_version'))
        return (
            self._jwt.get('body', {}).get('lti_version') or  # Check if lti version is inside jwt body
            self._request._request.POST.get('lti_version') or  # Else, check if it might be in POST data
            settings.LTI13  # Else default to LTI 1.3 (which also does not include lti_version information)
        )

    def validate_1p0(self):
        # print('VALIDATING', self._request._request)
        secret = settings.LTI_SECRET
        key = settings.LTI_KEY
        try:
            OAuthRequestValidater.check_signature(key, secret, self._request._request)
        except (oauth2.Error, ValueError) as e:
            sentry_sdk.capture_exception(e)
            raise LtiException(str(e))

        self._validated = True

        return self

    def validate(self, *args, **kwargs):
        if self.lti_version == settings.LTI10:
            self._session_service.save_launch_data(self._launch_id, self._jwt['body'])
            return self.validate_1p0(*args, **kwargs)
        else:
            return super().validate(*args, **kwargs)

    def validate_nonce(self):
        """
        Probably it is bug on "https://lti-ri.imsglobal.org":
        site passes invalid "nonce" value during deep links launch.
        Because of this in case of iss == http://imsglobal.org just skip nonce validation.

        """
        iss = self.get_iss()
        deep_link_launch = self.is_deep_link_launch()
        if iss == "http://imsglobal.org" and deep_link_launch:
            return self
        return super(eDjangoMessageLaunch, self).validate_nonce()

    def get_launch_data(self, *args, **kwargs):
        if self.lti_version == settings.LTI10:
            if 'body' not in self._jwt:
                self.set_jwt({'body': self._request._request.POST})
            if not self._validated and self._auto_validation:
                self.validate()

        data = super().get_launch_data(*args, **kwargs)
        return eMessageLaunchData(data, lti_version=self.lti_version)

    @classmethod
    def from_cache(cls, launch_id, *args, **kwargs):
        obj = cls(*args, **kwargs)
        launch_data = obj.get_session_service().get_launch_data(launch_id)
        obj = obj.set_launch_id(launch_id)\
            .set_auto_validation(enable=False)\
            .set_jwt({'body': launch_data})

        if not launch_data:
            raise LtiException("Launch data not found")

        if launch_data.get('lti_version', settings.LTI13) == settings.LTI13:
            return obj.validate_registration()

        return obj


def get_launch_data_from_id(launch_id, request):
    """Return the launch data that belongs to the launch ID"""
    return get_launch_from_id(launch_id, request).get_launch_data()


def get_launch_from_id(launch_id, request):
    """Return the launch that belongs to the launch ID"""
    return eDjangoMessageLaunch.from_cache(
        launch_id, request, settings.TOOL_CONF, launch_data_storage=DjangoCacheDataStorage()
    )


def get_launch_state(launch_data):
    user = launch_data.user.find_in_db()
    course = launch_data.course.find_in_db()
    assignment = launch_data.assignment.find_in_db()

    if not user:
        return LTI_STATES.NO_USER.value

    if user.is_teacher:
        if not course:
            return LTI_STATES.NO_COURSE.value
        if not assignment:
            return LTI_STATES.NO_ASSIGNMENT.value
    else:
        if not course:
            return LTI_STATES.NOT_SETUP.value
        if not assignment:
            return LTI_STATES.NOT_SETUP.value

    if user.has_permission('can_view_all_journals', assignment):
        return LTI_STATES.FINISH_TEACHER.value
    else:
        return LTI_STATES.FINISH_STUDENT.value
