"""
common.py.

In this file are all the extra api requests.
This includes:
    /names/ -- to get the names belonging to the ids
"""
from rest_framework.decorators import api_view

import VLE.utils.responses as response
from VLE.models import Assignment, Course, Journal


@api_view(['GET'])
def names(request, course_id, assignment_id, journal_id):
    """Get names of course, assignment, journal.

    Arguments:
    request -- the request that was sent
        course_id -- optionally the course id
        assignment_id -- optionally the assignment id
        journal_id -- optionally the journal id

    Returns a json string containing the names of the set fields.
    course_id populates 'course', assignment_id populates 'assignment', tID populates
    'template' and journal_id populates 'journal' with the users' name.
    """
    result = {}
    if course_id:
        course = Course.objects.get(pk=course_id)
        request.user.check_can_view(course)
        result['course'] = course.name

    if assignment_id:
        assignment = Assignment.objects.get(pk=assignment_id)
        request.user.check_can_view(assignment)
        result['assignment'] = assignment.name

    if journal_id:
        journal = Journal.objects.get(pk=journal_id)
        request.user.check_can_view(journal)
        result['journal'] = journal.name

    return response.success({'names': result})
