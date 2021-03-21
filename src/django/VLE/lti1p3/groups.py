import json

import VLE.lti1p3 as lti
from VLE.lms_api import utils
from VLE.models import Course, Group, Instance, Participation


def sync_groups(access_token, course_id):
    instance = Instance.objects.get(pk=1)
    course = Course.objects.get(pk=course_id)
    url = f'{instance.lms_url}/api/v1/courses/{course.lms_id}/sections'
    groups = json.loads(utils.api_request(url, access_token).content)
    print(json.dumps(groups, indent=4))
    group_lms_ids = set(group['id'] for group in groups)

    # Get all existing groups passed by lms that are also in the course
    existing_group_lms_ids = set(Group.objects.filter(
        lms_id__in=group_lms_ids,
        course=course
    ).values_list('lms_id', flat=True))
    print(existing_group_lms_ids)
    # Get all to-be-created groups
    # non_existing_group_ids = group_lms_ids - existing_group_lms_ids

    # Create new groups
    new_groups = []
    for group in groups:
        if str(group['id']) in existing_group_lms_ids:
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
            print(student)

            student.create_or_update(
                update_kwargs={'course': course},
                create_kwargs={'course': course},
            )
            if student.username not in existing_student_usernames:
                students_to_add.append(student)
        print([
            student.username
            for student in students_to_add
        ])
        print(Participation.objects.filter(user__username__in=[
                student.username
                for student in students_to_add
            ]))
        group.participation_set.add(
            *Participation.objects.filter(user__username__in=[
                student.username
                for student in students_to_add
            ])
        )

    # TODO LTI: pagination
    return {
        'sections': groups,
    }
