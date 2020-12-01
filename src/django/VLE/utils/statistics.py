"""
Utility functions in relation to generic statistics
"""

import VLE.models


def get_user_lists_with_scopes(assignment, user, course=None):
    """Get lists of users in [assignment] in different scopes connected to [user].
    Allows for setting [course] to limit the users retrieved to only being from that course.

    Args:
        - assignment: Assignment of which stats are desired
        - user: Educator requesting stats
        - course: Course for which stats are specifically requested

    Returns:
        dict:
            - all: All users which are participants of [assignment].
            - own: Subset of all with which [user] shares a group.
            Note: If [course] is set, all lists are limited to only users that participate in [course]

    Note:
        The assumption that all of of [course] participation users have APs in a linked assignment is False on
        production. Otherwise p_all could simply be `course.participation_set.all()`
    """
    if course is None:
        shared_courses = assignment.courses.filter(users=user)
    else:
        shared_courses = VLE.models.Course.objects.filter(pk=course.pk, users=user)

    return {
        'all': assignment.get_all_users(courses=shared_courses, user=user),
        'own': assignment.get_users_in_own_groups(courses=shared_courses, user=user)
    }
