import json

from dateutil.parser import parse
from django.conf import settings

import VLE.factory as factory
import VLE.lti1p3 as lti
from VLE.models import Assignment, Course, PresetNode


def create_with_launch_data(message_launch_data):
    return factory.make_assignment(
        name=message_launch_data.get(lti.claims.ASSIGNMENT)['title'],
        description=message_launch_data.get(lti.claims.ASSIGNMENT)['description'],
        author=lti.user.get_with_launch_data(message_launch_data),
        active_lti_id=message_launch_data.get(lti.claims.ASSIGNMENT)['id'],
        points_possible=message_launch_data.get(lti.claims.CUSTOM).get('assignment_points'),
        is_published=message_launch_data.get(lti.claims.CUSTOM).get('assignment_publish'),
        unlock_date=message_launch_data.get(lti.claims.CUSTOM).get('assignment_unlock'),
        due_date=message_launch_data.get(lti.claims.CUSTOM).get('assignment_due'),
        lock_date=message_launch_data.get(lti.claims.CUSTOM).get('assignment_lock'),
        courses=[Course.objects.get(active_lti_id=message_launch_data.get(lti.claims.COURSE).get('id'))],
        assignments_grades_service=json.dumps(message_launch_data.get(lti.claims.ASSIGNMENTSGRADES)),
    )


def get_and_update_assignment_with_launch_data(message_launch_data):
    """Get and update the assignment connected to the LTI launch data.

    If no assignment is found, it will return None."""
    try:
        assignment = get_with_launch_data(message_launch_data)
        return update_with_launch_data(assignment, message_launch_data)
    except Assignment.DoesNotExist:
        return None


def get_with_launch_data(message_launch_data):
    # We use the custom set variable here because in the gradebook the CONTEXT lti_id is different
    return Assignment.objects.get(active_lti_id=message_launch_data.get(lti.claims.CUSTOM)['assignment_lti_id'])


def update_with_launch_data(assignment, message_launch_data):
    """Update assignment with data from the LTI launch.

    This will not update:
    is_published when it is not able to (e.g. already contains entries)
    due/lock dates when it is not able to (e.g. already contains progress nodes later lock date)
    points_possible when it is not able to (e.g. already contains progress node with higher goal)"""
    assignment.points_possible = message_launch_data.get(lti.claims.CUSTOM).get(
        'assignment_points', assignment.points_possible)
    assignment.unlock_date = message_launch_data.get(lti.claims.CUSTOM).get(
        'assignment_unlock', assignment.unlock_date)
    # TODO LTI: check if it is possible to update the description / title on the Canvas side
    # when it is updated in eJournal
    # assignment.name = message_launch_data.get(lti.claims.ASSIGNMENT)['title']
    # assignment.description = message_launch_data.get(lti.claims.ASSIGNMENT)['description']
    new_due_date = message_launch_data.get(lti.claims.CUSTOM).get('assignment_due', assignment.due_date)
    new_lock_date = message_launch_data.get(lti.claims.CUSTOM).get('assignment_lock', assignment.lock_date)
    new_published_state = message_launch_data.get(lti.claims.CUSTOM).get('assignment_publish', True)
    nodes = PresetNode.objects.filter(format__assignment=assignment)

    # TODO LTI: check timezones
    # TODO future: make better use of timezones
    if (
        new_due_date
        and nodes.order_by('due_date').last().due_date.replace(tzinfo=settings.TZ_INFO) > parse(new_due_date)
    ):
        assignment.due_date = new_due_date
    if (
        new_lock_date
        and nodes.order_by('lock_date').last().lock_date.replace(tzinfo=settings.TZ_INFO) > parse(new_lock_date)
    ):
        assignment.lock_date = new_lock_date
    if new_published_state or assignment.can_be_unpublished():
        assignment.is_published = new_published_state
    assignment.save()
    return assignment
