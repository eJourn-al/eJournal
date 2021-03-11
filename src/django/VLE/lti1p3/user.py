from django.utils import timezone

import VLE.lti1p3 as lti
from VLE.models import Course, Instance, Participation, Role, User


def _get_username(message_launch_data):
    # Get the customly provided username. This is used for login at the LMS
    # If that doesn't exist, get the sourcedid and use that for login purposes as it is often the same
    if lti.claims.CUSTOM in message_launch_data:
        return message_launch_data.get(lti.claims.CUSTOM).get('username')

    return message_launch_data.get(
        # NOTE: this used when called from names_role_service
        'lis_person_sourcedid',
        # NOTE: this is used when called from an individual lti launch
        message_launch_data.get(lti.claims.LIS).get('person_sourcedid')
    )


def _get_profile_picture(message_launch_data, user=None):
    """Get the profile picture that is set in the message launch.

    If that is the default, return the users profile picture instead.
    If no user is set, return None."""
    if message_launch_data.get('picture') == \
       Instance.objects.get(pk=1).default_lms_profile_picture:
        return user.profile_picture if user else None

    return message_launch_data.get('picture')


def create_with_launch_data(message_launch_data, password=None, course=None):
    is_test_student = lti.utils.is_test_student_launch(message_launch_data)
    user = User(
        username=_get_username(message_launch_data),
        full_name=message_launch_data['name'],
        email=message_launch_data.get('email', None),
        verified_email='email' in message_launch_data,
        lti_id=message_launch_data['sub'],
        is_teacher=lti.utils.is_teacher_launch(message_launch_data),
        is_test_student=is_test_student,
        profile_picture=_get_profile_picture(message_launch_data)
    )
    if password and not is_test_student:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.full_clean()
    user.save()

    get_or_create_participation_with_launch_data(user, message_launch_data, course=course)

    return user


def get_and_update_user_with_launch_data(message_launch_data):
    """Get and update the user connected to the LTI launch data.

    If no user is found, it will return None."""
    try:
        user = get_with_launch_data(message_launch_data)
        return update_with_launch_data(user, message_launch_data)
    except User.DoesNotExist:
        return None


def get_with_launch_data(message_launch_data):
    # TODO LTI: check why username was necessary
    return User.objects.get(lti_id=message_launch_data['sub'])


def update_with_launch_data(user, message_launch_data, course=None):
    """Update user with data from the LTI launch."""
    # TODO LTI: add to the correct group
    user.full_name = message_launch_data.get('name', user.full_name)
    user.username = _get_username(message_launch_data)
    user.email = message_launch_data.get('email', user.email)
    user.verified_email = True
    user.lti_id = message_launch_data.get('sub', user.lti_id)
    user.is_teacher = lti.utils.is_teacher_launch(message_launch_data)
    user.profile_picture = _get_profile_picture(message_launch_data)

    user.last_login = timezone.now()
    user.save()

    get_or_create_participation_with_launch_data(user, message_launch_data, course=course)

    return user


def get_or_create_participation_with_launch_data(user, message_launch_data, course=None):
    if not course:
        course = Course.objects.filter(active_lti_id=message_launch_data.get(lti.claims.COURSE)['id']).first()
        if not course:
            return None

    participation = Participation.objects.filter(user=user, course=course).first()
    if participation:
        return participation

    role_name = lti.roles.to_ejournal_role(message_launch_data.get(lti.claims.ROLES, []))

    return Participation.objects.create(
        user=user,
        course=course,
        role=Role.objects.get(course=course, name=role_name),
    )
