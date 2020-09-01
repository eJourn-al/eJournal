import enum

from django.conf import settings
from django.db.models import Q
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch
from pylti1p3.service_connector import ServiceConnector

from VLE import factory
from VLE.lti1p3 import claims, roles
from VLE.models import Assignment, Course, Instance, User


class LTI_STATES(enum.Enum):
    """VUE ENTRY STATE."""
    NOT_SETUP = '-1'

    NO_USER = '0'

    NO_COURSE = '1'
    NO_ASSIGNMENT = '2'
    FINISH_TEACHER = '3'
    FINISH_STUDENT = '4'


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
        return SectionsService(connector, sections_service)


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
        launch_id, request, settings.TOOL_CONF, launch_data_storage=DjangoCacheDataStorage())


def get_launch_state(message_launch_data):
    user = User.objects.filter(
        Q(username=message_launch_data.get(claims.CUSTOM).get('username')) |
        Q(lti_id=message_launch_data['sub'])
    ).first()
    course = Course.objects.filter(active_lti_id=message_launch_data.get(claims.COURSE)['id']).first()
    assignment = Assignment.objects.filter(active_lti_id=message_launch_data.get(claims.ASSIGNMENT)['id']).first()

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
