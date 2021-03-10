import json

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.models import Course, User
from VLE.utils.error_handling import VLEBadRequest


def create_with_launch_data(message_launch_data):
    course = factory.make_course(
        name=message_launch_data.get(lti.claims.COURSE)['title'],
        abbreviation=message_launch_data.get(lti.claims.COURSE)['label'],
        startdate=message_launch_data.get(lti.claims.CUSTOM).get('course_start'),
        enddate=message_launch_data.get(lti.claims.CUSTOM).get('course_end'),
        author=User.objects.filter(lti_id=message_launch_data['sub']).first(),
        active_lti_id=message_launch_data.get(lti.claims.COURSE)['id'],
        names_role_service=json.dumps(message_launch_data.get(lti.claims.NAMESROLES))
    )

    lti.members.sync_members(course)
    return course


def get_and_update_course_with_launch_data(message_launch_data):
    """Get and update the course connected to the LTI launch data.

    If no course is found, it will return None."""
    try:
        course = get_with_launch_data(message_launch_data)
        return update_with_launch_data(course, message_launch_data)
    except Course.DoesNotExist:
        return None


def get_with_launch_data(message_launch_data):
    return Course.objects.get(active_lti_id=message_launch_data.get(lti.claims.COURSE)['id'])


def update_with_launch_data(course, message_launch_data):
    """Update course with data from the LTI launch."""
    # TODO LTI: check if it is possible to update the description / title on the Canvas side
    # when it is updated in eJournal
    # course.name = message_launch_data.get(lti.claims.COURSE)['title']
    # course.description = message_launch_data.get(lti.claims.COURSE)['description']
    if course.active_lti_id and course.active_lti_id != message_launch_data.get(lti.claims.COURSE)['id']:
        raise VLEBadRequest('Course already linked to LMS.')
    if not course.active_lti_id:
        course.active_lti_id = message_launch_data.get(lti.claims.COURSE)['id']
        # Only sync members on first launch
        # TODO LTI: add sync members btn on eJournal to sync later added users
    lti.members.sync_members(course)
    course.startdate = message_launch_data.get(lti.claims.CUSTOM).get('course_start', course.startdate)
    course.enddate = message_launch_data.get(lti.claims.CUSTOM).get('course_end', course.enddate)
    course.names_role_service = json.dumps(message_launch_data.get(lti.claims.NAMESROLES))
    course.save()

    return course
