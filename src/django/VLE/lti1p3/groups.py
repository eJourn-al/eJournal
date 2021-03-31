import json

import VLE.lti1p3 as lti
from VLE.lms_api import utils
from VLE.models import Course, Group, Instance, Participation


def sync_groups(access_token, course_id):
    instance = Instance.objects.get_or_create(pk=1)[0]
    course = Course.objects.get(pk=course_id)
    url = f'{instance.lms_url}/api/v1/courses/{course.lms_id}/sections'
    groups = json.loads(utils.api_request(url, access_token).content)
    group_lms_ids = set(group['id'] for group in groups)

    # Get all existing groups passed by lms that are also in the course
    existing_group_lms_ids = set(Group.objects.filter(
        lms_id__in=group_lms_ids,
        course=course
    ).values_list('lms_id', flat=True))

    # Create new groups
    new_groups = []
    for group in groups:
        if str(group['id']) in existing_group_lms_ids:
            # TODO LTI: update group names
            continue  # Group already exists, ignore creation
        new_groups.append(
            Group(
                name=group['name'],
                course=course,
                lms_id=group['id'],
            )
        )
    Group.objects.bulk_create(new_groups)

    for group, students in zip(
        Group.objects.filter(lms_id__in=[g['id'] for g in groups]),
        [g['students'] or [] for g in groups]
    ):
        existing_student_usernames = group.participation_set.values_list('user__username', flat=True)
        students_to_add = []
        for student in students:
            student = lti.user.CanvasAPIUserData(student)

            student.create_or_update(
                update_kwargs={'course': course},
                create_kwargs={'course': course},
            )
            if student.username not in existing_student_usernames:
                students_to_add.append(student)

        group.participation_set.add(
            *Participation.objects.filter(user__username__in=[
                student.username
                for student in students_to_add
            ])
        )

    return {
        'sections': groups,
    }
