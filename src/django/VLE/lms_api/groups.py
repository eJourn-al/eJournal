import json

import sentry_sdk

import VLE.lti1p3 as lti
from VLE.lms_api import utils
from VLE.models import Course, Group, Instance, Participation
from VLE.utils.error_handling import VLEMissingRequiredKey


def sync_groups(access_token, course_id):
    instance = Instance.objects.get_or_create(pk=1)[0]
    course = Course.objects.get(pk=course_id)
    url = f'{instance.lms_url}/api/v1/courses/{course.lms_id}/sections'
    groups = json.loads(utils.api_request(url, access_token, params={
        'include[]': ['students', 'total_students'],
    }).content)
    group_lms_ids = set(group['id'] for group in groups)

    # Get all existing groups passed by lms that are also in the course
    existing_group_lms_ids = set(Group.objects.filter(
        lms_id__in=group_lms_ids,
        course=course
    ).values_list('lms_id', flat=True))

    # Create new groups and update the name of existing groups
    new_groups = []
    update_name_groups = {}
    for group in groups:
        if str(group['id']) in existing_group_lms_ids:
            update_name_groups[str(group['id'])] = group['name']
            continue  # Group already exists, ignore creation
        new_groups.append(
            Group(
                name=group['name'],
                course=course,
                lms_id=str(group['id']),
            )
        )
    Group.objects.bulk_create(new_groups)
    update_groups = Group.objects.filter(lms_id__in=update_name_groups.keys())
    print(update_name_groups, update_groups)
    for group in update_groups:
        group.name = update_name_groups[group.lms_id]
    Group.objects.bulk_update(update_groups, ['name'])

    for group, students in zip(
        Group.objects.filter(lms_id__in=[g['id'] for g in groups]),
        [g['students'] or [] for g in groups]
    ):
        existing_student_usernames = group.participation_set.values_list('user__username', flat=True)
        students_to_add = []
        for student in students:
            try:
                student = lti.user.CanvasAPIUserData(student)

                student.create_or_update(
                    update_kwargs={'course': course},
                    create_kwargs={'course': course},
                )
                if student.username not in existing_student_usernames:
                    students_to_add.append(student)
            except VLEMissingRequiredKey as exception:
                with sentry_sdk.push_scope() as scope:
                    scope.level = 'info'
                    try:
                        scope.set_context('user', student.as_dict())
                    except Exception:
                        pass
                    sentry_sdk.capture_exception(exception)

        group.participation_set.add(
            *Participation.objects.filter(user__username__in=[
                student.username
                for student in students_to_add
            ])
        )

    return {
        'sections': groups,
    }
