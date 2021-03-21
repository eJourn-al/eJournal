import enum
import json

from django.conf import settings
from django.db.models import Q
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch
from pylti1p3.service_connector import ServiceConnector

import VLE.lti1p3 as lti
# TODO lti: check if SectionsService import is working correctly
from VLE.lti1p3 import claims, roles
from VLE.models import Assignment, Course, User


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

    data
    create_keys
    update_keys


    '''
    @property
    def create_dict(self):
        return {
            key: getattr(self, key)
            for key in self.create_keys
        }

    @property
    def update_dict(self):
        return {
            key: getattr(self, key)
            for key in self.update_keys
        }

    def find_in_db(self):
        return NotImplemented

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

    def asdict(self):
        return {
            **self.create_dict,
            **self.update_dict,
            'create_keys': self.create_keys,
            'update_keys': self.update_keys,
        }

    def __str__(self):
        return json.dumps(self.asdict(), sort_keys=False, indent=4)


class eMessageLaunchData(object):
    def __init__(self, message_launch_data):
        self.raw_data = message_launch_data
        print(json.dumps(self.raw_data, sort_keys=False, indent=4))
        self.user = lti.user.Lti1p3UserData(message_launch_data)
        self.course = lti.course.Lti1p3CourseData(message_launch_data)
        self.assignment = lti.assignment.Lti1p3AssignmentData(message_launch_data)

    def __str__(self):
        user = self.user.asdict()
        course = self.course.asdict()
        if course['author']:
            course['author'] = course['author'].pk
        assignment = self.assignment.asdict()
        if assignment['courses']:
            assignment['courses'] = []
        if assignment['author']:
            assignment['author'] = assignment['author'].pk
        return json.dumps({
            'raw data': self.raw_data,
            'user': user,
            'course': course,
            'assignment': assignment,
        }, sort_keys=False, indent=4)


class ExtendedDjangoMessageLaunch(DjangoMessageLaunch):

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
        return super(ExtendedDjangoMessageLaunch, self).validate_nonce()

    def get_sections(self):
        """Fetches Canvas' specific sections service for the current launch."""
        connector = ServiceConnector(self._registration)
        sections_service = 'http://canvas.docker/api/v1/courses/{}/sections'.format(1)
        # TODO LTI: should be SectionsService
        return ServiceConnector(connector, sections_service)

    def get_launch_data(self, *args, **kwargs):
        return eMessageLaunchData(super().get_launch_data(*args, **kwargs))


def is_teacher_launch(message_launch_data):
    launch_roles = message_launch_data.get(claims.ROLES, [])
    return any(role in launch_roles for role in [roles.TEACHER, roles.ADMIN, roles.ADMIN_INST])


def is_test_student_launch(message_launch_data):
    return (
        message_launch_data.get('email', '') == ''
        and message_launch_data.get('name', '').lower() == 'Test Student'.lower()  # TODO: make instance variable
    )


def get_launch_data_from_id(launch_id, request):
    """Return the launch data that belongs to the launch ID"""
    return get_launch_from_id(launch_id, request).get_launch_data()


def get_launch_from_id(launch_id, request):
    """Return the launch that belongs to the launch ID"""
    return ExtendedDjangoMessageLaunch.from_cache(
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
