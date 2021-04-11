"""
group.py.

In this file are all the group api requests.
"""
from django.conf import settings
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action

import VLE.factory as factory
import VLE.lms_api as lms_api
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Course, Group, Instance, Journal, Participation
from VLE.serializers import GroupSerializer
from VLE.utils.error_handling import VLEPermissionError


def check_can_view_groups(user, course):
    if not (user.has_permission('can_view_course_users', course) or
            user.has_permission('can_edit_course_user_group', course) or
            user.has_permission('can_add_course_user_group', course) or
            user.has_permission('can_delete_course_user_group', course)):
        raise VLEPermissionError(message='You are not allowed to view the user groups of this course.')


class GroupView(viewsets.ViewSet):
    def list(self, request):
        """Get the groups from a course for the user.

        Arguments:
        request -- request data
            course_id -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exists
            forbidden -- when the user is not part of the course
        On success:
            success -- with the group data

        """
        course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
        assignment_id, = utils.optional_typed_params(request.query_params, (int, 'assignment_id'))

        course = Course.objects.get(pk=course_id)

        check_can_view_groups(request.user, course)

        if assignment_id:
            assignment = Assignment.objects.get(pk=assignment_id)
            journals = list(Journal.objects.filter(assignment=assignment).values_list('authors__user', flat=True))

            participations = Participation.objects.filter(
                user__in=journals,
                course=course
            ).exclude(user__is_test_student=True)

            groups = Group.objects.filter(
                course=course, participation__in=participations
            ).annotate(
                matched=Count('participation')
            ).exclude(
                matched=len(participations)
            )

            queryset = groups.distinct()
        else:
            queryset = Group.objects.filter(course=course)
        serializer = GroupSerializer(queryset, many=True, context={'user': request.user, 'course': course})

        return response.success({'groups': serializer.data})

    def create(self, request):
        """Create a new course group.

        Arguments:
        request -- the request that was send with
            name -- name of the course group
            course_id -- course ID of the course
            lti_id -- (optional) lti_id to link the course to

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- when the user has no permission to create new groups
        On success, with the course group.
        """
        name, course_id = utils.required_params(request.data, "name", "course_id")
        lti_id, = utils.optional_params(request.data, 'lti_id')

        course = Course.objects.get(pk=course_id)

        request.user.check_permission('can_add_course_user_group', course)

        if lti_id and Group.objects.filter(lti_id=lti_id, course=course).exists():
            return response.bad_request('Course group with the desired lti id already exists.')

        course_group = factory.make_course_group(name, course, lti_id)
        serializer = GroupSerializer(course_group, context={'user': request.user}, many=False)
        return response.created({'group': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """Update an existing course group.

        Arguments:
        request -- request data
            name -- group name
        pk -- group ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exists
            forbidden -- when the user is not in the course
            unauthorized -- when the user is unauthorized to edit the course
            bad_request -- when there is invalid data in the request
        On success:
            success -- with the new course data
        """
        name, = utils.required_params(request.data, 'name')

        group_id, = utils.required_typed_params(kwargs, (int, 'pk'))
        group = Group.objects.get(pk=group_id)
        course = group.course

        request.user.check_permission('can_edit_course_user_group', course)

        if not name:
            return response.bad_request('Group name is not allowed to be empty.')

        serializer = GroupSerializer(group, data={'name': name}, context={'user': request.user}, partial=True)
        if not serializer.is_valid():
            return response.bad_request()

        serializer.save()
        return response.success({'group': serializer.data})

    def destroy(self, request, pk):
        """Delete an existing course group.

        Arguments:
        request -- request data
        pk -- group ID

        Returns:
        On failure:
            not found -- when the course does not exists
            unauthorized -- when the user is not logged in
            forbidden -- when the user is not in the course
        On success:
            success -- with a message that the course group was deleted
        """
        group = Group.objects.get(pk=pk)

        request.user.check_permission('can_delete_course_user_group', group.course)

        group.delete()
        return response.success(description='Successfully deleted course group.')

    @action(['get'], detail=False)
    def datanose(self, request):
        course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
        course = Course.objects.get(pk=course_id)
        check_can_view_groups(request.user, course)

        if settings.LTI10 not in course.lti_versions:
            msg = 'This option is not available for this Course.'
            if settings.LTI13 in course.lti_versions and \
               Instance.objects.get_or_create(pk=1)[0].lms_name == Instance.CANVAS:
                msg += ' Try to sync with Canvas instead.'
            return response.bad_request(msg)

        factory.make_lti_groups(course)

        queryset = Group.objects.filter(course=course)
        serializer = GroupSerializer(queryset, many=True, context={'user': request.user, 'course': course})

        return response.success({'groups': serializer.data})

    @action(['get'], detail=False)
    def LMS(self, request):
        course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
        course = Course.objects.get(pk=course_id)
        check_can_view_groups(request.user, course)

        if settings.LTI13 not in course.lti_versions:
            msg = 'This option is not available for this Course.'
            # TODO EXPANSION: This is UvA specific, and should be removed when expanding
            if settings.LTI11 in course.lti_versions and \
               Instance.objects.get_or_create(pk=1)[0].lms_name == Instance.CANVAS:
                msg += ' Try to sync with DataNose instead.'
            return response.bad_request(msg)

        return lms_api.utils.do_lms_api_action(
            request.user,
            settings.CANVAS_API_ACTIONS['SYNC_GROUPS'],
            course_id,
        )

    @action(['get'], detail=False)
    def assigned_groups(self, request):
        course_id, assignment_id = utils.required_typed_params(
            request.query_params,
            (int, 'course_id'),
            (int, 'assignment_id'),
        )

        course = Course.objects.get(pk=course_id)
        assignment = Assignment.objects.get(pk=assignment_id)

        request.user.check_permission('can_edit_assignment', assignment)

        return response.success({
            'assigned_groups': GroupSerializer(assignment.assigned_groups.filter(course=course), many=True).data
        })
