"""
factory.py.

The factory has all kinds of functions to create entries in the database.
Sometimes this also supports extra functionallity like adding courses to assignments.
"""
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

import VLE.validators as validators
from VLE.models import (Assignment, AssignmentParticipation, Comment, Content, Course, Entry, Field, Format, Grade,
                        Group, Journal, Node, Participation, PresetNode, Role, Template, User)
from VLE.utils.error_handling import VLEBadRequest


def make_user(username, password=None, email=None, lti_id=None, profile_picture=settings.DEFAULT_PROFILE_PICTURE,
              is_superuser=False, is_teacher=False, full_name=None, verified_email=False, is_staff=False,
              is_test_student=False):
    """Create a user.

    Arguments:
    username -- username (is the user came from the UvA canvas, this will be its studentID)
    password -- password of the user to login
    email -- mail of the user (default: none)
    lti_id -- to link the user to canvas (default: none)
    profile_picture -- profile picture of the user (default: none)
    is_superuser -- if the user needs all permissions, set this true (default: False)
    """
    user = User(
        username=username, email=email, lti_id=lti_id, is_superuser=is_superuser, is_teacher=is_teacher,
        verified_email=verified_email, is_staff=is_staff, full_name=full_name, profile_picture=profile_picture,
        is_test_student=is_test_student)

    if is_test_student:
        user.set_unusable_password()
    else:
        validators.validate_password(password)
        user.set_password(password)

    user.full_clean()
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
    participation = Participation(user=user, course=course, role=role)
    participation.save(notify_user=notify_user)
    if groups:
        participation.groups.set(groups)
        participation.save()

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
    course = Course(name=name, abbreviation=abbrev, startdate=startdate, enddate=enddate,
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
    course_group = Group(name=name, course=course, lti_id=lti_id)
    course_group.save()
    return course_group


def make_assignment(name, description, author=None, format=None, active_lti_id=None,
                    points_possible=10, is_published=None, unlock_date=None, due_date=None,
                    lock_date=None, courses=[], is_group_assignment=False,
                    can_set_journal_name=False, can_set_journal_image=False, can_lock_journal=False,
                    remove_grade_upon_leaving_group=False):
    """Make a new assignment.

    Arguments:
    name -- name of assignment
    description -- description of the assignment
    author -- author of assignment
    format -- format of assignment
    courseIDs -- ID of the courses the assignment belongs to
    courses -- courses it belongs to
    active_lti_id -- (optional) lti_id, this links an eJournal course to a VLE course, only the active id receives
        grade passback.

    On success, returns a new assignment.
    """
    if format is None:
        if due_date:
            format = make_default_format(due_date, points_possible)
        else:
            format = make_default_format(timezone.now() + timedelta(days=365), points_possible)

    assign = Assignment(name=name, description=description, author=author, format=format,
                        is_group_assignment=is_group_assignment, active_lti_id=active_lti_id,
                        can_set_journal_name=can_set_journal_name, can_set_journal_image=can_set_journal_image,
                        can_lock_journal=can_lock_journal,
                        remove_grade_upon_leaving_group=remove_grade_upon_leaving_group)
    if points_possible is not None:
        assign.points_possible = points_possible
    if is_published is not None:
        assign.is_published = is_published
    if unlock_date is not None:
        if len(unlock_date.split(' ')) > 2:
            unlock_date = unlock_date[:-1-len(unlock_date.split(' ')[2])]
        assign.unlock_date = unlock_date
    if due_date is not None:
        if len(due_date.split(' ')) > 2:
            due_date = due_date[:-1-len(due_date.split(' ')[2])]
        assign.due_date = due_date
    if lock_date is not None:
        if len(lock_date.split(' ')) > 2:
            lock_date = lock_date[:-1-len(lock_date.split(' ')[2])]
        assign.lock_date = lock_date
    assign.save()

    for course in courses:
        assign.add_course(course)

    return assign


def make_lti_groups(course):
    groups = requests.get(settings.GROUP_API.format(course.active_lti_id)).json()
    if isinstance(groups, list):
        for group in groups:
            try:
                name = group['Name']
                lti_id = int(group['CanvasSectionID'])
                if not Group.objects.filter(course=course, lti_id=lti_id).exists():
                    make_course_group(name, course, lti_id)
            except (ValueError, KeyError):
                continue


def make_default_format(due_date=None, points_possible=10):
    format = Format()
    format.save()
    template = make_entry_template('Entry', format)
    make_field(template, 'Content', 0, Field.RICH_TEXT, True)
    if due_date and points_possible and int(points_possible) > 0:
        make_progress_node(format, due_date, points_possible)
    return format


def make_progress_node(format, due_date, target):
    """Make a progress node.

    Arguments:
    format -- format the node belongs to.
    due_date -- due_date of the node.
    """
    node = PresetNode(type=Node.PROGRESS, due_date=due_date, target=target, format=format)
    node.save()
    return node


def make_entrydeadline_node(format, due_date, template, unlock_date=None, lock_date=None):
    """Make entry deadline.

    Arguments:
    format -- format of the entry deadline.
    unlock_date -- unlock date of the entry deadline.
    due_date -- due date of the entry deadline.
    lock_date -- lock date of the entry deadline.
    template -- template of the entrydeadline.
    """
    node = PresetNode(type=Node.ENTRYDEADLINE, unlock_date=unlock_date, due_date=due_date,
                      lock_date=lock_date, forced_template=template, format=format)
    node.save()

    return node


def make_node(journal, entry=None, type=Node.ENTRY, preset=None):
    """Make a node.

    Arguments:
    journal -- journal the node belongs to.
    entry -- entry the node belongs to.
    """
    return Node.objects.get_or_create(type=type, entry=entry, preset=preset, journal=journal)[0]


def make_journal(assignment, author=None, author_limit=None):
    """Make a new journal.

    First creates all nodes defined by the format.
    The deadlines and templates are the same object
    as those in the format, so any changes should
    be reflected in the Nodes as well.
    """
    if assignment.is_group_assignment:
        if author is not None:
            raise VLEBadRequest('Group journals should not be initialized with an author')
        journal = Journal.objects.create(assignment=assignment, author_limit=author_limit)

    else:
        if author_limit is not None:
            raise VLEBadRequest('Non group-journals should not be initialized with an author_limit')
        if Journal.all_objects.filter(assignment=assignment, authors__user=author).exists():
            return Journal.all_objects.get(assignment=assignment, authors__user=author)

        ap = AssignmentParticipation.objects.filter(assignment=assignment, user=author).first()
        if ap is None:
            ap = AssignmentParticipation.objects.create(assignment=assignment, user=author)
            journal = Journal.all_objects.get(assignment=assignment, authors__in=[ap])
        else:
            journal = Journal.objects.create(assignment=assignment)
            journal.add_author(ap)

    return journal


def make_assignment_participation(assignment, author):
    """Make a new assignment participation."""
    return AssignmentParticipation.objects.create(assignment=assignment, user=author)


def make_entry(template, author, node):
    entry = Entry.objects.create(template=template, author=author, node=node)
    entry.node.entry = entry
    entry.node.save()
    return entry


def make_entry_template(name, format, preset_only=False):
    """Make an entry template."""
    entry_template = Template(name=name, format=format, preset_only=preset_only)
    entry_template.save()
    return entry_template


def make_field(template, title, loc, type=Field.TEXT, required=True, description=None, options=None):
    """Make a field."""
    field = Field(type=type,
                  title=title,
                  location=loc,
                  template=template,
                  required=required,
                  description=description,
                  options=options)
    field.save()
    return field


def make_content(entry, data, field=None):
    """Make content."""
    content = Content(field=field, entry=entry, data=data)
    content.save()
    return content


def make_role_default_no_perms(name, course, *args, **kwargs):
    """Make a role with all permissions set to false.

    Arguments:
    name -- name of the role (needs to be unique)
    can_... -- permission
    """
    permissions = {permission: kwargs.get(permission, False) for permission in Role.PERMISSIONS}
    role = Role.objects.create(
        name=name,
        course=course,
        **permissions
    )
    return role


def make_role_default_all_perms(name, course, *args, **kwargs):
    """Makes a role with all permissions set to true."""
    permissions = {permission: kwargs.get(permission, True) for permission in Role.PERMISSIONS}
    role = Role.objects.create(
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
    return Comment.objects.create(
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
    grade = Grade.objects.create(
        entry=entry,
        author=User.objects.get(pk=author),
        grade=grade,
        published=published
    )

    entry.grade = grade
    entry.save()

    return grade
