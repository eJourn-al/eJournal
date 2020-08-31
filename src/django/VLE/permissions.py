"""
permissions.py.

All the permission functions.
"""
from django.db.models import Q

import VLE.models
from VLE.utils.error_handling import VLEProgrammingError


def has_general_permission(user, permission):
    """Check if the user has the needed "global" permission.

    Arguments:
    user -- user that did the request.
    permission -- the permission string to check.

    Raises VLEProgrammingError when the passed permission is not a "General Permission".
    """
    if permission not in VLE.models.Role.GENERAL_PERMISSIONS:
        raise VLEProgrammingError("Permission " + permission + " is not a general level permission.")

    if user.is_superuser:
        return True

    # If the user is a teacher, he is allowed to create courses on the platform.
    if user.is_teacher and permission == 'can_add_course':
        return True

    return False


def has_course_permission(user, permission, course):
    """Check if the user has the needed permission in the given course.

    Arguments:
    user -- user that did the request.
    course -- course used to check against.
    permission -- the permission string to check.

    Raises VLEProgrammingError when the passed permission is not a "Course Permission".
    Raises VLEParticipationError when the user is not participating in the course.
    """
    if permission not in VLE.models.Role.COURSE_PERMISSIONS:
        raise VLEProgrammingError("Permission " + permission + " is not a course level permission.")

    if user.is_superuser:
        return True

    return VLE.models.Role.objects.filter(
        **{permission: True},
        role__user=user, course=course).exists()


def has_assignment_permission(user, permission, assignment):
    """Check if the user has the needed permission in the given assignment.

    Arguments:
    user -- user that did the request.
    assignment -- assignment used to check against.
    permission -- the permission string to check.

    Raises VLEProgrammingError when the passed permission is not an "Assignment Permission".
    Raises VLEParticipationError when the user is not participating in the assignment.
    """

    if permission not in VLE.models.Role.ASSIGNMENT_PERMISSIONS:
        raise VLEProgrammingError("Permission " + permission + " is not an assignment level permission.")

    if user.is_superuser:
        if permission == 'can_have_journal':
            return False
        return True

    if permission == 'can_have_journal' and VLE.models.Role.objects.filter(can_view_all_journals=True,
       role__user=user, course__in=assignment.courses.all()).exists():
        return False

    return VLE.models.Role.objects.filter(
        **{permission: True},
        role__user=user, course__in=assignment.courses.all()).exists()


def is_user_supervisor_of(supervisor, user):
    """Checks whether the user is a participant in any of the assignments where the supervisor has the permission of
    can_view_course_users or where the supervisor is linked to the user through an assignment where the supervisor
    has the permission can_view_all_journals."""
    return VLE.models.Role.objects.filter(
        Q(can_view_all_journals=True) | Q(can_view_course_users=True),
        role__user=supervisor,
        course__in=VLE.models.Participation.objects.filter(user=user).values('course')).exists()


def get_supervisors_of(journal):
    return VLE.models.User.objects.filter(pk__in=VLE.models.Participation.objects.filter(
        role__can_view_all_journals=True,
        role__course__in=journal.assignment.courses.all()
    ).values('user')).distinct()


def can_edit(user, obj):
    if isinstance(obj, VLE.models.Entry):
        return _can_edit_entry(user, obj)

    return False


def _can_edit_entry(user, entry):
    user.check_permission('can_have_journal', entry.node.journal.assignment)

    if (
        not entry.node.journal.authors.filter(user=user).exists() or
        entry.node.journal.assignment.is_locked() or
        entry.is_graded() or
        entry.is_locked() or
        len(entry.node.journal.needs_lti_link) > 0
    ):
        return False

    return True


def serialize_general_permissions(user):
    return {key: has_general_permission(user, key) for key in VLE.models.Role.GENERAL_PERMISSIONS}


def serialize_course_permissions(user, course):
    return {key: has_course_permission(user, key, course) for key in VLE.models.Role.COURSE_PERMISSIONS}


def serialize_assignment_permissions(user, assignment):
    return {key: has_assignment_permission(user, key, assignment) for key in VLE.models.Role.ASSIGNMENT_PERMISSIONS}
