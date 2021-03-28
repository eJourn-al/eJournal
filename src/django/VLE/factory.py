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
    participation = VLE.models.Participation.objects.get_or_create(user=user, course=course, role=role)[0]
    if groups:
        participation.set_groups(groups)

    return participation


def make_course(*args, **kwargs):
    """Create a course."""
    course = VLE.models.Course.objects.create(**kwargs)

    if settings.LTI10 in course.lti_versions and \
       VLE.models.Instance.objects.get(pk=1).lms_name == VLE.models.Instance.CANVAS:
        make_lti_groups(course)

    # Student, TA and Teacher role are created on course creation as is saves check for lti.
    make_role_student('Student', course)
    make_role_ta('TA', course)
    role = make_role_teacher('Teacher', course)
    if kwargs.get('author'):
        make_participation(kwargs.get('author'), course, role)
    return course


def make_course_group(name, course, lms_id=None):
    """Make a new course group.

    Arguments:
    name -- name of course group
    course -- course the group belongs to
    lms_id -- potential lms_id, this is to link the canvas course to the VLE course.
    """
    if name is None:
        return None
    course_group = VLE.models.Group(name=name, course=course, lms_id=lms_id)
    course_group.save()
    return course_group


def make_assignment(*args, **kwargs):
    """Make a new assignment."""
    format = kwargs.get('format', None)
    if format is None:
        format = VLE.models.Format.objects.create()

    courses = kwargs.pop('courses', [])
    assignment = VLE.models.Assignment.objects.create(
        format=format,
        **kwargs,
    )

    setup_default_assignment_layout(assignment)

    for course in courses:
        assignment.add_course(course)

    return assignment


def get_lti_groups_with_name(course):
    """Get a mapping of group LTI id to group name using the DN API"""

    # TODO EXPANSION: If the instance is not specificly the UvA, do not execute this request

    # It requires lms id to be set
    if settings.LTI10 not in course.lti_versions:
        return []

    dn_groups = requests.get(settings.GROUP_API.format(course.lms_id)).json()
    lti_groups = {}
    if isinstance(dn_groups, list):
        for group in dn_groups:
            try:
                lti_groups[int(group['CanvasSectionID'])] = group['Name']
            except (ValueError, KeyError):
                continue

    return lti_groups


def make_lti_groups(course):
    for lms_id, name in get_lti_groups_with_name(course).items():
        if not VLE.models.Group.objects.filter(course=course, lms_id=lms_id).exists():
            make_course_group(name, course, lms_id)
        else:
            VLE.models.Group.objects.filter(course=course, lms_id=lms_id).update(name=name)


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
    """NOTE: Only called for single entry creation (not bulk, e.g. teacher entries)"""
    if not template.chain.allow_custom_categories or category_ids is None:
        category_ids = list(template.categories.values_list('pk', flat=True))

    if not template.chain.allow_custom_title:
        title = None

    with transaction.atomic():
        entry = VLE.models.Entry.objects.create(template=template, author=author, node=node, title=title)
        entry_category_links = [
            VLE.models.EntryCategoryLink(entry=entry, category_id=id, author=author)
            for id in category_ids
        ]
        VLE.models.EntryCategoryLink.objects.bulk_create(entry_category_links)

        entry.node.entry = entry
        entry.node.save()

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


def make_grade(entry, author, grade, published=False):
    """Make a new grade record for an entry.

    Make a grade record for an entry based on its ID.
    Arguments:
    entry -- entry that the grade belongs to
    author -- uID of the author of the grade
    grade -- the new grade
    published -- publishment state of the grade
    """
    return VLE.models.Grade.objects.create(
        entry=entry,
        author=VLE.models.User.objects.get(pk=author),
        grade=grade,
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
