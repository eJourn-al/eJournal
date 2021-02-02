
from rest_framework import viewsets

import VLE.factory as factory
import VLE.permissions as permissions
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Assignment, Course, Role, User
from VLE.serializers import RoleSerializer
from VLE.utils.error_handling import VLEMissingRequiredKey, VLEParamWrongType


class RoleView(viewsets.ViewSet):
    # TODO: Make RoleView REST
    def list(self, request):
        """Get course roles.

        Arguments:
        request -- request data
            course_id -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not in the course
            forbidden -- when the user is unauthorized to edit its roles
        On success:
            success -- list of all the roles in the course

        """
        course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
        course = Course.objects.get(pk=course_id)

        # TODO: P Is this the right permission
        request.user.check_permission('can_edit_course_roles', course)

        roles = Role.objects.filter(course=course)
        serializer = RoleSerializer(roles, many=True)
        return response.success({'roles': serializer.data})

    def retrieve(self, request, pk=0):
        """Get the permissions of a user connected to a course / assignment.

        Arguments:
        request -- the request that was sent
            course_id -- course ID
            assignment_id -- assignment ID
        pk -- user ID (0 = logged in user)

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course is not found
            forbidden -- when the user is not in the course
        On success:
            success -- with a list of the permissions

        """
        if int(pk) == 0:
            pk = request.user.id
        user = User.objects.get(pk=pk)

        # Return course permissions if course_id is set
        try:
            course_id, = utils.required_typed_params(request.query_params, (int, 'course_id'))
            course = Course.objects.get(pk=course_id)

            request.user.check_participation(course)

            if user != request.user:
                # TODO: P Is this the right permission
                request.user.check_permission('can_edit_course_roles', course)

            return response.success({'role': permissions.serialize_course_permissions(request.user, course)})
        # Return assignment permissions if assignment_id is set
        except (VLEMissingRequiredKey, VLEParamWrongType):
            assignment_id, = utils.required_typed_params(request.query_params, (int, 'assignment_id'))
            assignment = Assignment.objects.get(pk=assignment_id)

            request.user.check_can_view(assignment)

            if user != request.user:
                # TODO: P Add a permission for this
                request.user.check_permission('can_view_all_journals', course)

            # Returns keyerror if course_id nor assignment_id is set
            return response.success({'role': permissions.serialize_assignment_permissions(request.user, assignment)})

    def create(self, request):
        """Create course role.

        Arguments:
        request -- request data
            course_id -- course ID
            name -- role name
            permissions -- permissions to change (default everything is false)

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not in the course
            forbidden -- when the user is unauthorized to edit its roles
        On success:
            success -- newly created course

        """
        course_id, name = utils.required_params(request.data, 'course_id', 'name')
        permissions, = utils.optional_typed_params(request.data, (dict, 'permissions'))
        if permissions is None:
            permissions = dict()
        course = Course.objects.get(pk=course_id)

        # TODO: P Is this the right permission
        request.user.check_permission('can_edit_course_roles', course)

        for permission in permissions:
            if permission not in Role.PERMISSIONS:
                return response.bad_request('Invalid permission was supplied.')
        if Role.objects.filter(name=name, course=course).exists():
            return response.bad_request('A role with this name already exists.')

        role = factory.make_role_default_no_perms(name, course, **permissions)

        serializer = RoleSerializer(role, many=False, context={'user': request.user})
        return response.created({'role': serializer.data})

    def partial_update(self, request, pk):
        """Updates course roles.

        Arguments:
        request -- request data
            roles -- each role of the course that needs to be updated
        pk -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not in the course
            forbidden -- when the user is unauthorized to edit its roles
            bad_request -- if
        On success:
            success -- list of all the roles in the course

        """
        course = Course.objects.get(pk=pk)

        request.user.check_permission('can_edit_course_roles', course)

        roles_response = []
        roles, = utils.required_params(request.data, 'roles')
        for new_role in roles:
            try:
                role = Role.objects.get(name=new_role['name'], course=course)
            except Role.DoesNotExist:
                role = factory.make_role_default_no_perms(new_role['name'], course)

            serializer = RoleSerializer(role, data=new_role, partial=True)
            if not serializer.is_valid():
                return response.bad_request()
            serializer.save()

            roles_response.append(serializer.data)
        return response.success({'roles': roles_response})

    def destroy(self, request, pk):
        """Delete course role.

        Arguments:
        request -- request data
            name -- role name
        pk -- course ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- when the user is not in the course
            forbidden -- when the user is unauthorized to edit its roles
        On success:
            success -- newly created course

        """
        name, = utils.required_typed_params(request.query_params, (str, 'name'))
        course = Course.objects.get(pk=pk)

        # Users can only delete course roles with can_edit_course_roles
        request.user.check_permission('can_edit_course_roles', course)

        if name in ['Student', 'TA', 'Teacher']:
            return response.bad_request('Default roles "Student", "TA" and "Teacher" cannot be deleted.')

        Role.objects.get(name=name, course=pk).delete()
        return response.success(description='Successfully deleted role from course.')
