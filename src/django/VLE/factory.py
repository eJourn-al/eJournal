"""
factory.py.

The factory has all kinds of functions to create entries in the database.
Sometimes this also supports extra functionallity like adding courses to assignments.
"""
import requests
from django.conf import settings
from django.db import transaction

import VLE.models
import VLE.validators as validators


def make_user(username, password=None, email=None, lti_id=None, profile_picture=settings.DEFAULT_PROFILE_PICTURE,
              is_superuser=False, is_teacher=False, full_name=None, verified_email=False, is_staff=False,
              is_test_student=False, is_active=True, save=True):
    """Create a user.

    Arguments:
    username -- username (is the user came from the UvA canvas, this will be its studentID)
    password -- password of the user to login
    email -- mail of the user (default: none)
    lti_id -- to link the user to canvas (default: none)
    profile_picture -- profile picture of the user (default: none)
    is_superuser -- if the user needs all permissions, set this true (default: False)
    """
    user = VLE.models.User(
        username=username, email=email, lti_id=lti_id, is_superuser=is_superuser, is_teacher=is_teacher,
        verified_email=verified_email, is_staff=is_staff, full_name=full_name, profile_picture=profile_picture,
        is_test_student=is_test_student, is_active=is_active)

    if is_test_student or not is_active:
        user.set_unusable_password()
    else:
        validators.validate_password(password)
        user.set_password(password)

    user.full_clean()

    if save:
        user.save()
    return user


def make_participation(user=None, course=None, role=None, groups=None, notify_user=True):
    """Create a participation.

    Arguments:
    user -- user that participates
    course -- course the user participates in
    role -- role the user has on the course
    groups -- groups the user belongs to
    """
    participation = VLE.models.Participation(user=user, course=course, role=role)
    participation.save(notify_user=notify_user)
    if groups:
        participation.set_groups(groups)

    return participation


def make_course(name, abbrev, startdate=None, enddate=None, author=None, active_lti_id=None):
    """Create a course.

    Arguments:
    name -- name of the course
    abbrev -- abbreviation of the course
    startdate -- startdate of the course
    author -- author of the course, this will also get the teacher role as participation
    active_lti_id -- (optional) lti_id, this links an eJournal course to a VLE course, only the active id receives
        grade passback.
    """
    course = VLE.models.Course(name=name, abbreviation=abbrev, startdate=startdate, enddate=enddate,
                               author=author, active_lti_id=active_lti_id)
    course.save()

    if course.has_lti_link():
        make_lti_groups(course)

    # Student, TA and Teacher role are created on course creation as is saves check for lti.
    make_role_student('Student', course)
    make_role_ta('TA', course)
    role = make_role_teacher('Teacher', course)
    if author is not None:
        make_participation(author, course, role)
    return course


def make_course_group(name, course, lti_id=None):
    """Make a new course group.

    Arguments:
    name -- name of course group
    course -- course the group belongs to
    lti_id -- potential lti_id, this is to link the canvas course to the VLE course.
    """
    if name is None:
        return None
    course_group = VLE.models.Group(name=name, course=course, lti_id=lti_id)
    course_group.save()
    return course_group


@transaction.atomic
def make_assignment(
    name,
    description,
    author=None,
    is_published=False,
    points_possible=10,
    unlock_date=None,
    due_date=None,
    lock_date=None,
    courses=[],
    active_lti_id=None,
    is_group_assignment=False,
    remove_grade_upon_leaving_group=False,
    can_set_journal_name=False,
    can_set_journal_image=False,
    can_lock_journal=False,
):
    """
    Arguments:
    name -- name of assignment
    description -- description of the assignment
    author -- author of assignment
    courseIDs -- ID of the courses the assignment belongs to
    courses -- courses it belongs to
    active_lti_id -- (optional) lti_id, this links an eJournal course to a VLE course, only the active id receives
        grade passback.
    """
    format = VLE.models.Format.objects.create()

    assignment = VLE.models.Assignment.objects.create(
        name=name,
        description=description,
        author=author,
        is_published=is_published,
        points_possible=points_possible,
        unlock_date=unlock_date,
        due_date=due_date,
        lock_date=lock_date,
        format=format,
        active_lti_id=active_lti_id,
        is_group_assignment=is_group_assignment,
        remove_grade_upon_leaving_group=remove_grade_upon_leaving_group,
        can_set_journal_name=can_set_journal_name,
        can_set_journal_image=can_set_journal_image,
        can_lock_journal=can_lock_journal,
    )

    setup_default_assignment_layout(assignment)

    for course in courses:
        assignment.add_course(course)

    return assignment


def get_lti_groups_with_name(course):
    """Get a mapping of group LTI id to group name using the DN API"""
    dn_groups = requests.get(settings.GROUP_API.format(course.active_lti_id)).json()
    lti_groups = {}
    if isinstance(dn_groups, list):
        for group in dn_groups:
            try:
                lti_groups[int(group['CanvasSectionID'])] = group['Name']
            except (ValueError, KeyError):
                continue
    return lti_groups


def make_lti_groups(course):
    groups = get_lti_groups_with_name(course)
    for lti_id, name in groups.items():
        if not VLE.models.Group.objects.filter(course=course, lti_id=lti_id).exists():
            make_course_group(name, course, lti_id)
        else:
            VLE.models.Group.objects.filter(course=course, lti_id=lti_id).update(name=name)


def setup_default_assignment_layout(assignment):
    template = VLE.models.Template.objects.create(
        name='Template',
        format=assignment.format,
    )

    VLE.models.Field.objects.create(
        template=template,
        title='',
        location=0,
        type=VLE.models.Field.RICH_TEXT,
        required=True,
    )


def make_node(journal, entry=None, type=VLE.models.Node.ENTRY, preset=None):
    """Make a node.

    Arguments:
    journal -- journal the node belongs to.
    entry -- entry the node belongs to.
    """
    return VLE.models.Node.objects.get_or_create(type=type, entry=entry, preset=preset, journal=journal)[0]


def make_entry(template, author, node, category_ids=None, title=None):
    params = {}

    if not template.chain.allow_custom_title:
        title = None

    if not template.chain.allow_custom_categories or category_ids is None:
        params['category_ids'] = list(template.categories.values_list('pk', flat=True))
    elif category_ids:
        params['category_ids'] = category_ids

    # NOTE: because we use a custom variable (category_ids) we have to call the save function seperatly
    entry = VLE.models.Entry(template=template, author=author, node=node, title=title)
    entry.save(**params)
    return entry


def make_content(entry, data, field=None):
    """Make content."""
    content = VLE.models.Content(field=field, entry=entry, data=data)
    content.save()
    return content


def make_role_default_no_perms(name, course, *args, **kwargs):
    """Make a role with all permissions set to false.

    Arguments:
    name -- name of the role (needs to be unique)
    can_... -- permission
    """
    permissions = {permission: kwargs.get(permission, False) for permission in VLE.models.Role.PERMISSIONS}
    role = VLE.models.Role.objects.create(
        name=name,
        course=course,
        **permissions
    )
    return role


def make_role_default_all_perms(name, course, *args, **kwargs):
    """Makes a role with all permissions set to true."""
    permissions = {permission: kwargs.get(permission, True) for permission in VLE.models.Role.PERMISSIONS}
    role = VLE.models.Role.objects.create(
        name=name,
        course=course,
        **permissions
    )
    return role


def make_role_student(name, course):
    """Make a default student role."""
    return make_role_default_no_perms(name, course, can_have_journal=True, can_comment=True)


def make_role_ta(name, course):
    """Make a default teacher assitant role."""
    return make_role_default_no_perms(name, course, can_view_course_users=True, can_edit_course_user_group=True,
                                      can_view_all_journals=True, can_grade=True, can_publish_grades=True,
                                      can_comment=True, can_view_unpublished_assignment=True, can_manage_journals=True)


def make_role_observer(name, course):
    """"Make a default observer role."""
    return make_role_default_no_perms(name, course, can_view_course_users=True,
                                      can_view_all_journals=True)


def make_role_teacher(name, course):
    """Make a default teacher role."""
    return make_role_default_all_perms(name, course, can_have_journal=False)


def make_comment(entry, author, text, published):
    """Make an Entry Comment.

    Make an Entry Comment for an entry based on its ID.
    With the author and the given text.
    Arguments:
    entry -- entry where the comment belongs to
    author -- author of the comment
    text -- content of the comment
    published -- publishment state of the comment
    """
    return VLE.models.Comment.objects.create(
        entry=entry,
        author=author,
        text=text,
        published=published
    )


def make_journal_image(file, journal, author):
    validators.validate_user_file(file, author)

    fc = VLE.models.FileContext.objects.create(
        file=file,
        file_name=file.name,
        author=author,
        journal=journal,
        is_temp=False,
    )
    journal.stored_image = fc.download_url(access_id=True)
    journal.save()
