from urllib.parse import urljoin

import oauth2
import sentry_sdk
from django.conf import settings

import VLE.factory as factory
import VLE.utils.generic_utils as utils
import VLE.utils.grading as grading
from VLE.models import Assignment, AssignmentParticipation, Course, Group, Instance, Journal, Participation, Role, User
from VLE.utils.authentication import set_sentry_user_scope


class OAuthRequestValidater(object):
    """OAuth request validater class for Django Requests"""

    def __init__(self, key, secret):
        """
        Constructor which creates a consumer object with the given key and
        secret.
        """
        super(OAuthRequestValidater, self).__init__()
        self.consumer_key = key
        self.consumer_secret = secret

        self.oauth_server = oauth2.Server()
        signature_method = oauth2.SignatureMethod_HMAC_SHA1()
        self.oauth_server.add_signature_method(signature_method)
        self.oauth_consumer = oauth2.Consumer(self.consumer_key, self.consumer_secret)

    def parse_request(self, request):
        """
        Parses a django request to return the method, url, header and post data.
        """
        return request.method, request.build_absolute_uri(), request.META, request.POST.dict()

    def is_valid(self, request):
        """
        Checks if the signature of the given request is valid based on the
        consumers secret en key
        """
        method, url, head, param = self.parse_request(request)
        oauth_request = oauth2.Request.from_request(method, url, headers=head, parameters=param)
        self.oauth_server.verify_request(oauth_request, self.oauth_consumer, {})

    @classmethod
    def check_signature(cls, key, secret, request):
        """Validate OAuth request using the python-oauth2 library.

        https://github.com/simplegeo/python-oauth2.
        """
        validator = OAuthRequestValidater(key, secret)
        validator.is_valid(request)


def roles_to_list(params):
    roles = list()
    if 'roles' in params:
        for role in params['roles'].split(','):
            roles.append(role.split('/')[-1].lower())
    return roles


def roles_to_lti_roles(lti_params):
    return [settings.LTI_ROLES[r] if r in settings.LTI_ROLES else r for r in roles_to_list(lti_params)]


def get_user_lti(request):
    """Check if a user with the lti_id exists"""
    lti_user_id = request['user_id']

    users = User.objects.filter(lti_id=lti_user_id)
    if users.exists():
        user = users.first()
        set_sentry_user_scope(user)
        if 'custom_user_image' in request and \
           Instance.objects.get_or_create(pk=1)[0].default_lms_profile_picture not in request['custom_user_image']:
            user.profile_picture = request['custom_user_image']
            user.save()

        # NOTE: Canvas can also provide Institution wide roles, we should use this in stead of just any teacher role
        if 'roles' in request and any(lti_role in roles_to_list(request) for lti_role in settings.ROLES['Teacher']):
            user.is_teacher = True
            user.save()
        return user
    return None


def create_lti_query_link(query):
    """
    Creates link to lti page with the given parameters

    Arguments
    query -- QueryDict of the query variables

    returns the link
    """
    return ''.join((urljoin(settings.BASELINK, '/LtiLogin'), '?', query.urlencode()))


def add_groups_if_not_exists(participation, group_ids):
    """Add the lti groups to a participant.

    This will only be done if there are no other groups already bound to the participant.
    """
    def get_name_from_lti_id(lti_id, group_names, i):
        if lti_id in group_names:
            return group_names[lti_id]
        elif lti_id.isnumeric() and int(lti_id) in group_names:
            return group_names[int(lti_id)]
        else:
            return 'Group {:d}'.format(n_groups + i + 1)

    # Get all existing groups passed by lti that are also in the course
    groups = Group.objects.filter(lti_id__in=group_ids, course=participation.course)
    # Get all to-be-created groups
    non_existing_group_ids = set(group_ids) - set(group.lti_id for group in groups)
    # Get the groups of the course which the user is not participating in
    non_participating_groups = groups.exclude(pk__in=participation.groups.all())

    # Create new groups
    if non_existing_group_ids:
        group_names = factory.get_lti_groups_with_name(participation.course)
        n_groups = Group.objects.filter(course=participation.course).count()

        new_groups = [
            Group(
                name=get_name_from_lti_id(lti_id, group_names, i),
                course=participation.course,
                lti_id=lti_id
            )
            for i, lti_id in enumerate(non_existing_group_ids)
        ]
        new_groups = Group.objects.bulk_create(new_groups)
    else:
        new_groups = []

    # Add missing newly-created and existing groups and update participation for computed fields
    if new_groups or non_participating_groups:
        participation.groups.add(*new_groups, *non_participating_groups)

    return participation.groups


def _make_lti_participation(user, course, lti_role):
    """Make the user a participant in the course.

    This function also adds the role if this is a valid role registered in our system.
    """
    for role in settings.ROLES:
        if role in lti_role:
            return factory.make_participation(
                user, course, Role.objects.get(name=role, course=course), notify_user=False)

    sentry_sdk.capture_message(f'Unrecognized LTI role encountered. User {user.pk}, roles {lti_role}', level='warning')

    return factory.make_participation(
        user, course, Role.objects.get(name='Student', course=course), notify_user=False)


def update_lti_course_if_exists(request, user, role):
    """Update a course with lti request.

    If no course exists, return None
    If it does exist:
    1. If the to be processed user is a test student, remove any other test students from the course, 1 max.
    2. Put the user in the course
    3. Add groups to the user
    """
    course_lti_id = request.get('custom_course_id', None)
    course = Course.objects.filter(active_lti_id=course_lti_id)
    if course_lti_id is None or not course.exists():
        return None

    # There can only be one actively linked course.
    course = course.first()

    # Can only have one active test student per course at a time.
    if user.is_test_student:
        User.objects.filter(participation__course=course, is_test_student=True).exclude(pk=user.pk).delete()

    # If the user not is a participant, add participation with possibly the role given by the LTI instance.
    if not user.is_participant(course):
        participation = _make_lti_participation(user, course, role)
    else:
        participation = Participation.objects.get(course=course, user=user)

    group_ids, = utils.optional_params(request, 'custom_section_id')
    if group_ids:
        add_groups_if_not_exists(participation, group_ids.split(','))

    return course


def update_lti_assignment_if_exists(request):
    """Update a course with lti request.

    If no course exists, return None
    If it does exist:
        Update the published state
    """
    assign_id = request['custom_assignment_id']
    assignment = Assignment.objects.filter(lti_id_set__contains=[assign_id])
    if not assignment.exists():
        return None

    # Assignment and lti_id_set values are unique together (no two assignments set contain the same lti id)
    assignment = assignment.first()

    # Only update is_published when needed, NOTE: this triggers the computedfields on all connected journals
    if 'custom_assignment_publish' in request and assignment.is_published != request['custom_assignment_publish']:
        assignment.is_published = request['custom_assignment_publish']
        assignment.save()
    return assignment


def select_create_journal(request, user, assignment):
    """
    Select or create the requested journal.
    """
    if assignment is None or user is None:
        return None

    author = AssignmentParticipation.objects.get_or_create(user=user, assignment=assignment)[0]
    journal = Journal.objects.filter(authors__user=user, assignment=assignment).first()
    # Update the grade_url and sourcedid only for the active LMS link.
    if assignment.active_lti_id != request['custom_assignment_id']:
        return journal

    # Only update if something is actually changed
    if (
        author.grade_url == request.get('lis_outcome_service_url') and
        author.sourcedid == request.get('lis_result_sourcedid')
    ):
        return journal

    author.grade_url = request.get('lis_outcome_service_url')
    author.sourcedid = request.get('lis_result_sourcedid')
    author.save()

    if journal:
        grading.task_author_status_to_LMS.delay(journal.pk, author.pk)
        journal = Journal.objects.get(pk=journal.pk)

    return journal
