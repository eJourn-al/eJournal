"""
format.py.

In this file are all the Format api requests.
"""
from django.core.exceptions import ValidationError
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.utils.template as template_utils
from VLE.models import Assignment, Course, Field, Format, Group, PresetNode
from VLE.serializers import AssignmentFormatSerializer, FormatSerializer
from VLE.utils import file_handling


def _update_assigned_groups(assignment, course_id, requested_group_ids):
    """
    Updates an assignment's assigned groups based on the provided id list from the perspective of the provided
    course. Only groups associated with that course are added or removed.

    Args:
        assignment (:model:`VLE.assignment`): The assignment whose m2m field 'assigned_groups' should be updated.
        course_id (int):
        requested_group_ids ([int]): unvalidated, desired list of group ids the assignment should be assigned to.
    """
    db_group_ids = set(assignment.assigned_groups.values_list('pk', flat=True))
    db_assignment_course_group_ids = set(
        assignment.assigned_groups.filter(course_id=course_id).values_list('pk', flat=True))

    # Ensure the requested group ids are part of the provided course
    req_course_group_ids = set(Group.objects.filter(
        course_id=course_id, pk__in=requested_group_ids).values_list('pk', flat=True))

    group_ids_to_add = req_course_group_ids - db_assignment_course_group_ids
    group_ids_to_remove = db_assignment_course_group_ids - req_course_group_ids
    assigned_groups = (db_group_ids - group_ids_to_remove) | group_ids_to_add

    # Only update the DB if there is an actual difference
    if db_group_ids != assigned_groups:
        assignment.assigned_groups.set(assigned_groups)


class FormatView(viewsets.ViewSet):
    """Format view.

    This class creates the following api paths:
    GET /formats/ -- gets all the formats
    PATCH /formats/<pk> -- partially update an format
    """

    def retrieve(self, request, pk):
        """Get the format attached to an assignment.

        Arguments:
        request -- the request that was sent
        pk -- the assignment id

        Returns a json string containing the format as well as the
        corresponding assignment name and description.
        """
        assignment = Assignment.objects.get(pk=pk)
        course_id, = utils.optional_typed_params(request.query_params, (int, 'course_id'))
        course = None
        if course_id:
            course = Course.objects.get(pk=course_id)

        request.user.check_can_view(assignment)
        request.user.check_permission('can_edit_assignment', assignment)

        return response.success({
            'format': FormatSerializer(
                FormatSerializer.setup_eager_loading(Format.objects.filter(pk=assignment.format_id)).get()
            ).data,
            'assignment_details': AssignmentFormatSerializer(
                assignment,
                context={'user': request.user, 'course': course}
            ).data
        })

    def partial_update(self, request, pk):
        """Update an existing journal format.

        Arguments:
        request -- request data
            templates -- the list of templates to bind to the format
            presets -- the list of presets to bind to the format
            removed_presets -- presets to be removed
            removed_templates -- templates to be removed
        pk -- assignment ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the assignment does not exist
            forbidden -- User not allowed to edit this assignment
            unauthorized -- when the user is unauthorized to edit the assignment
            bad_request -- when there is invalid data in the request
        On success:
            success -- with the new assignment data
        """
        assignment_details, templates, presets, removed_templates, removed_presets = utils.required_params(
            request.data,
            'assignment_details',
            'templates',
            'presets',
            'removed_templates',
            'removed_presets'
        )
        assignment_details = {k: (None if v == '' else v) for k, v in assignment_details.items()} \
            if assignment_details else {}

        assignment = Assignment.objects.get(pk=pk)
        course = None

        request.user.check_permission('can_edit_assignment', assignment)

        if 'assigned_groups' in assignment_details:
            course_id, = utils.required_typed_params(request.data, (int, 'course_id'))
            if not Course.objects.filter(pk=course_id, assignment=assignment).exists():
                raise ValidationError('Provided course id is unrelated to the assignment')

            requested_group_ids = [group['id'] for group in assignment_details.pop('assigned_groups')]
            _update_assigned_groups(assignment, course_id, requested_group_ids)

        serializer = AssignmentFormatSerializer(
            assignment, data=assignment_details, context={'user': request.user, 'course': course}, partial=True)
        if not serializer.is_valid():
            return response.bad_request('Invalid assignment data.')
        serializer.save()

        new_ids = template_utils.update_templates(assignment.format, templates)
        utils.update_presets(request.user, assignment, presets, new_ids)

        utils.delete_presets(removed_presets)
        template_utils.delete_or_archive_templates(removed_templates)

        file_handling.establish_rich_text(author=request.user, rich_text=assignment.description, assignment=assignment)
        for field in Field.objects.filter(template__format=assignment.format):
            file_handling.establish_rich_text(author=request.user, rich_text=field.description, assignment=assignment)
        for node in PresetNode.objects.filter(format=assignment.format):
            file_handling.establish_rich_text(author=request.user, rich_text=node.description, assignment=assignment)

        return response.success({
            'format': FormatSerializer(
                FormatSerializer.setup_eager_loading(Format.objects.filter(pk=assignment.format_id)).get()
            ).data,
            'assignment_details': AssignmentFormatSerializer(
                assignment,
                context={'user': request.user, 'course': course}
            ).data
        })
