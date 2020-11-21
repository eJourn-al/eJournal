"""
course.py.

In this file are all the course api requests.
"""
from rest_framework import viewsets
from rest_framework.decorators import action

import VLE.factory as factory
import VLE.serializers as serialize
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Course


class CourseView(viewsets.ViewSet):
    serializer_class = serialize.CourseSerializer

    def list(self, request):
        """Get the courses that the user participates in.

        Arguments:
        request -- request data

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
        On success:
            success -- with the course data
        """
        get_all, = utils.optional_params(request.query_params, 'get_all')
        if request.user.is_superuser and get_all:
            queryset = Course.objects.all()
        else:
            queryset = request.user.participations.all()
        serializer = self.serializer_class(queryset, many=True)
        return response.success({'courses': serializer.data})

    def create(self, request):
        """Create a new course.

        Arguments:
        request -- request data
            name -- name of the course
            abbreviation -- abbreviation of the course
            startdate -- (optional) date when the course starts
            enddate -- (optional) date when the course ends
            lti_id -- (optional) lti_id to link the course to

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- when the user has no permission to create new courses
        On success:
            success -- with the course data
        """
        request.user.check_permission('can_add_course')

        name, abbr = utils.required_params(request.data, 'name', 'abbreviation')
        startdate, enddate, active_lti_id = utils.optional_params(request.data, 'startdate', 'enddate', 'lti_id')

        course = factory.make_course(name, abbr, startdate, enddate, request.user, active_lti_id=active_lti_id)

        serializer = self.serializer_class(course, many=False)
        return response.created({'course': serializer.data})

    def retrieve(self, request, pk=None):
        """Get the course data from the course ID.

        Arguments:
        request -- request data
        pk -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not in the course
        On success:
            success -- with the course data
        """
        course = Course.objects.get(pk=pk)

        request.user.check_participation(course)

        serializer = self.serializer_class(course, many=False)
        return response.success({'course': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """Update an existing course.

        Arguments:
        request -- request data
            data -- the new data for the course
        pk -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not in the course
            unauthorized -- when the user is unauthorized to edit the course
            bad_request -- when there is invalid data in the request
        On success:
            success -- with the new course data
        """
        course_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        course = Course.objects.get(pk=course_id)

        request.user.check_permission('can_edit_course_details', course)

        if 'lti_id' in request.data:
            if course.active_lti_id:
                return response.bad_request('Course already linked to LMS.')
            course.active_lti_id = request.data.pop('lti_id')
            course.save()

        request.data['startdate'], request.data['enddate'] = utils.optional_params(request.data, 'startdate', 'enddate')
        serializer = self.serializer_class(course, data=request.data, partial=True)
        if not serializer.is_valid():
            return response.bad_request()
        serializer.save()
        return response.success({'course': serializer.data})

    def destroy(self, request, *args, **kwargs):
        """Delete an existing course.

        Arguments:
        request -- request data
        pk -- course ID

        Returns:
        On failure:
            not found -- when the course does not exist
            unauthorized -- when the user is not logged in
            forbidden -- when the user is not in the course
        On success:
            success -- with a message that the course was deleted
        """
        course_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        course = Course.objects.get(pk=course_id)

        request.user.check_permission('can_delete_course', course)

        for assignment in course.assignment_set.all():
            if assignment.courses.count() == 1:
                request.user.check_permission('can_delete_assignment', course)
                assignment.delete()
            else:
                if assignment.active_lti_id:
                    new_lti_connected_course = assignment.courses.exclude(
                        pk=course.pk).exclude(active_lti_id=None).order_by('-startdate').first()
                    assignment.lti_id_set.remove(assignment.active_lti_id)
                    if new_lti_connected_course:
                        assignment.active_lti_id = assignment.get_lti_id_from_course(new_lti_connected_course)
                    else:
                        assignment.active_lti_id = None
                    assignment.save()

        course.delete()
        return response.success(description='Successfully deleted course.')

    @action(methods=['get'], detail=False)
    def linkable(self, request):
        """Get linkable courses.

        Gets all courses that the current user either participates in or is allowed to edit the course details of.
        A user can then link this course to Canvas.

        Arguments:
        request -- request data

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not in the course
        On success:
            success -- with a message that the course was deleted
        """
        if not (request.user.is_teacher or request.user.is_superuser):
            return response.forbidden("You are not allowed to get linkable courses.")

        unlinked_courses = Course.objects.filter(participation__user=request.user.id,
                                                 participation__role__can_edit_course_details=True,
                                                 participation__role__can_add_assignment=True,
                                                 active_lti_id=None)
        serializer = serialize.CourseSerializer(unlinked_courses, many=True)
        return response.success({'courses': serializer.data})
