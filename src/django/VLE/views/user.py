"""
user.py.

In this file are all the user api requests.
"""

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from sentry_sdk import capture_exception

import VLE.factory as factory
import VLE.lti_launch as lti_launch
import VLE.permissions as permissions
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.validators as validators
from VLE.models import Entry, FileContext, Instance, Journal, Node, User
from VLE.serializers import EntrySerializer, OwnUserSerializer, UserSerializer
from VLE.tasks import send_email_verification_link, send_invite_emails
from VLE.utils import file_handling
from VLE.utils.authentication import set_sentry_user_scope
from VLE.utils.pagination import ExtendedPageNumberPagination
from VLE.views import lti


def get_lti_params(request, *keys):
    jwt_params, = utils.optional_params(request.data, 'jwt_params')
    if jwt_params:
        lti_params = lti.decode_lti_params(jwt_params)
    else:
        lti_params = {'empty': ''}
    if 'custom_user_image' in lti_params and \
       Instance.objects.get_or_create(pk=1)[0].default_lms_profile_picture in lti_params['custom_user_image']:
        lti_params['custom_user_image'] = settings.DEFAULT_PROFILE_PICTURE
    values = utils.optional_params(lti_params, *keys)
    values.append(any(role in lti_launch.roles_to_list(lti_params) for role in settings.ROLES['Teacher']))
    return values


class LoginView(TokenObtainPairView):
    def post(self, request):
        result = super(LoginView, self).post(request)
        if result.status_code == 200:
            username, = utils.required_params(request.data, 'username')
            user = User.objects.filter(username=username)
            set_sentry_user_scope(user.first())
            user.update(last_login=timezone.now())
        return result


class UserResultsSetPagination(ExtendedPageNumberPagination):
    page_size = 100
    max_page_size = 1000


class UserView(viewsets.ViewSet):
    pagination = UserResultsSetPagination()

    def list(self, request):
        """
        Orderable and filterable paginated list of all users, only accessible by administrators.

        Query parameters:
            page (int): window of the query set to serialize.
            page_size (int): size of the window.
            order_by (str): order by argument, can be descending (-).
            filter (str): filter to apply to the query, performs a case insensitive search for the columns
                `full_name`, `username`, and `email`.

        Returns:
            Paginated response object, where `results` contain the serialized page data
        """
        if not request.user.is_superuser:
            return response.forbidden('Only administrators are allowed to request all user data.')

        order_by = request.query_params.get('order_by', 'full_name')
        order_by = order_by if order_by else 'full_name'

        users = User.objects.values(
            'username',
            'full_name',
            'email',
            'is_teacher',
            'is_active',
            'id',
        ).order_by(
            order_by,
        )

        if request.query_params.get('filter'):
            users = users.filter(
                Q(email__icontains=request.query_params.get('filter'))
                | Q(username__icontains=request.query_params.get('filter'))
                | Q(full_name__icontains=request.query_params.get('filter'))
            )

        page = self.pagination.paginate_queryset(users, request)
        return self.pagination.get_paginated_response(data=page)

    def retrieve(self, request, pk):
        """Get the user data of the requested user.

        Arguments:
        request -- request data
        pk -- user ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the user doesn't exists
        On success:
            success -- with the user data
        """
        if int(pk) == 0:
            pk = request.user.id

        user = User.objects.get(pk=pk)

        if request.user == user or request.user.is_superuser:
            data = OwnUserSerializer(user, context={'user': request.user}, many=False).data
        elif permissions.is_user_supervisor_of(request.user, user):
            data = {field: getattr(user, field) for field in UserSerializer.Meta.user_fields}
        else:
            return response.forbidden('You are not allowed to view this users information.')

        return response.success({'user': data})

    def create(self, request):
        """Create a new user.

        Arguments:
        request -- request data
            username -- username
            password -- password
            full_name -- full name
            email -- (optinal) email
            jwt_params -- (optinal) jwt params to get the lti information from
                user_id -- id of the user
                user_image -- user image
                roles -- role of the user

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            bad request -- when email/username/lti id already exists
            bad request -- when email/password is invalid
        On success:
            success -- with the newly created user data
        """

        lti_id, user_image, full_name, email, is_teacher = get_lti_params(
            request, 'user_id', 'custom_user_image', 'custom_user_full_name', 'custom_user_email')
        is_test_student = bool(lti_id) and not bool(email)

        if lti_id is None:
            # Check if instance allows standalone registration if user did not register through some LTI instance
            try:
                instance = Instance.objects.get(pk=1)
                if not instance.allow_standalone_registration:
                    return response.bad_request(('{} does not allow you to register through the website,' +
                                                ' please use an LTI instance.').format(instance.name))
            except Instance.DoesNotExist:
                pass

            full_name, email = utils.required_params(request.data, 'full_name', 'email')

        username, password = utils.required_params(request.data, 'username', 'password')

        if not is_test_student and email in ['', None]:
            return response.bad_request('No email address is provided.')
        if not is_test_student and full_name in ['', None]:
            return response.bad_request('No full name is provided.')
        if email and User.objects.filter(email=email).exists():
            return response.bad_request('User with this email already exists.')

        if User.objects.filter(username=username).exists():
            return response.bad_request('User with this username already exists.')

        if lti_id is not None and User.objects.filter(lti_id=lti_id).exists():
            return response.bad_request('User with this lti id already exists.')

        user = factory.make_user(username=username, email=email, lti_id=lti_id, full_name=full_name,
                                 is_teacher=is_teacher, verified_email=bool(lti_id) and bool(email), password=password,
                                 profile_picture=user_image if user_image else settings.DEFAULT_PROFILE_PICTURE,
                                 is_test_student=is_test_student)

        if lti_id is None:
            send_email_verification_link.delay(user.pk)

        return response.created({'user': OwnUserSerializer(user, context={'user': request.user}).data})

    def partial_update(self, request, *args, **kwargs):
        """Update an existing user.

        Arguments:
        request -- request data
            jwt_params -- jwt params to get the lti information from
                user_id -- id of the user
                user_image -- user image
                roles -- role of the user
        pk -- user ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- when the user is not superuser or pk is not the same as the logged in user
            not found -- when the user doesnt exists
            bad request -- when the data is invalid
        On success:
            success -- with the updated user
        """
        pk, = utils.required_typed_params(kwargs, (int, 'pk'))
        if pk == 0:
            pk = request.user.pk
        if not (request.user.pk == pk or request.user.is_superuser):
            return response.forbidden()

        user = User.objects.get(pk=pk)

        lti_id, user_email, user_full_name, user_image, is_teacher = get_lti_params(
            request, 'user_id', 'custom_user_email', 'custom_user_full_name', 'custom_user_image')

        # Superuser can update another user's teacher status.
        if request.user.is_superuser:
            is_teacher, = utils.optional_params(request.data, 'is_teacher')

        if user_image is not None:
            user.profile_picture = user_image
        if user_email:
            if User.objects.filter(email=user_email).exclude(pk=user.pk).exists():
                return response.bad_request(
                    '{} is taken by another account. Link to that account or contact support.'.format(user_email))

            user.email = user_email
            user.verified_email = True
        if user_full_name is not None:
            user.full_name = user_full_name
        if is_teacher is not None:
            user.is_teacher = is_teacher

        if lti_id is not None:
            if User.objects.filter(lti_id=lti_id).exists():
                return response.bad_request('User with this lti id already exists.')
            elif bool(lti_id) and not bool(user_email) or user.is_test_student:
                return response.forbidden('You are not allowed to link a test account to an existing account.')
            user.lti_id = lti_id

        user.save()
        if user.lti_id is not None:
            pp, = utils.optional_params(request.data, 'profile_picture')
            data = {'profile_picture': pp if pp else user.profile_picture}
        else:
            data = request.data
        serializer = OwnUserSerializer(user, data=data, context={'user': request.user}, partial=True)
        if not serializer.is_valid():
            return response.bad_request()
        serializer.save()
        return response.success({'user': serializer.data})

    def destroy(self, request, pk):
        """Delete a user.

        Arguments:
        request -- request data
        pk -- user ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the user does not exist
        On success:
            success -- deleted message
        """
        user = User.objects.get(pk=pk)

        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to delete a user.')

        # Deleting the last superuser should not be possible
        if user.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
            return response.bad_request('There is only 1 superuser left and therefore cannot be deleted.')

        user.delete()
        return response.success(description='Successfully deleted user.')

    @action(['patch'], detail=False)
    def password(self, request):
        """Change the password of a user.

        Arguments:
        request -- request data
            new_password -- new password of the user
            old_password -- current password of the user

        Returns
        On failure:
            unauthorized -- when the user is not logged in
            bad request -- when the password is invalid
        On success:
            success -- with a success description
        """
        new_password, old_password = utils.required_params(request.data, 'new_password', 'old_password')

        if not request.user.check_password(old_password):
            return response.bad_request('Wrong password.')

        if validators.validate_password(new_password):
            return response.bad_request(validators.validate_password(new_password))

        request.user.set_password(new_password)
        request.user.save()
        return response.success(description='Successfully changed the password.')

    @action(methods=['get'], detail=True)
    def GDPR(self, request, pk):
        """Get a zip file of all the userdata.

        Arguments:
        request -- request data
        pk -- user ID to download the files from

        Returns
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- when its not a superuser nor their own data
        On success:
            success -- a zip file of all the userdata with all their files
        """
        if int(pk) == 0:
            pk = request.user.id

        user = User.objects.get(pk=pk)

        # Check the right permissions to get this users data, either be the user of the data or be an admin.
        if not (request.user.is_superuser or request.user.id == pk):
            return response.forbidden('You are not allowed to view this user\'s data.')

        profile = OwnUserSerializer(user, context={'user': request.user}).data
        journals = Journal.objects.filter(authors__user=user).distinct()
        journal_dict = {}
        for journal in journals:
            # Select the nodes of this journal but only the ones with entries.
            entry_ids = Node.objects.filter(journal=journal).exclude(entry__isnull=True).values_list('entry', flat=True)
            # Serialize all entries and put them into the entries dictionary with the assignment name key.
            journal_dict.update({
                journal.assignment.name: EntrySerializer(
                    EntrySerializer.setup_eager_loading(
                        Entry.objects.filter(id__in=entry_ids)
                    ).prefetch_related(
                        'comment_set'  # Only GDPR serializes comments via this route.
                    ),
                    context={'user': request.user, 'comments': True},
                    many=True
                ).data
            })

        archive_path, archive_name = file_handling.compress_all_user_data(
            user,
            {'profile': profile, 'journals': journal_dict}
        )

        return response.file(archive_path, archive_name)

    @action(['post'], detail=False)
    def set_profile_picture(self, request):
        """Update user profile picture.

        Arguments:
        request -- request data
            file -- a base64 encoded image

        Returns
        On failure:
            unauthorized -- when the user is not logged in
            bad_request -- when the file is not valid
        On success:
            success -- a zip file of all the userdata with all their files
        """
        file_data, = utils.required_params(request.data, 'file')
        content_file = utils.base64ToContentFile(file_data, 'profile_picture')
        validators.validate_user_file(content_file, request.user)

        file = FileContext.objects.create(
            file=content_file,
            file_name=content_file.name,
            author=request.user,
            is_temp=False,
        )
        request.user.profile_picture = file.download_url(access_id=True)
        request.user.save()

        return response.created({'download_url': file.download_url(access_id=True)})

    def get_permissions(self):
        if self.request.path == '/users/' and self.request.method == 'POST':
            return [AllowAny()]
        else:
            return [permission() for permission in self.permission_classes]

    @action(methods=['post'], detail=False)
    def invite_users(self, request):
        """Invite new users to eJournal.

        This will create accounts for the invited users, which they can activate through an invite link sent via email.

        Arguments:
        request -- request data
            users -- all users to create
                full_name -- full name of a user
                username -- username of a user
                email -- email address of a user
                is_teacher -- whether the user is a teacher

        Returns
        On failure:
            forbidden -- when the user is not a superuser (thus not allowed to invite new users)
            bad_request -- when the provided user data is invalid, e.g.
                Some users are missing a full name, email or username
                Usernames or email addresses belong to existing users
        On success:
            success -- the users have been invited
        """
        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to invite new users.')

        users, = utils.required_params(request.data, 'users')

        # Ensure a full name, username and email are specified for all users to be invited.
        if any('full_name' not in user or not user['full_name'] or not user['full_name'].strip() for user in users):
            return response.bad_request('Please specify a full name for all users. No invites sent.')
        if any('username' not in user or not user['username'] or not user['username'].strip() for user in users):
            return response.bad_request('Please specify a username for all users. No invites sent.')
        if any('email' not in user or not user['email'] or not user['email'].strip() for user in users):
            return response.bad_request('Please specify an email for all users. No invites sent.')

        # Remove excess whitespace. Whitespace differences should not satisfy username or email uniqueness constraints.
        for user in users:
            user['full_name'] = ' '.join(user['full_name'].split())
            user['username'] = ' '.join(user['username'].split())
            user['email'] = ' '.join(user['email'].split())

        # Ensure the username and email for all users to be invited are unique.
        usernames = set()
        duplicate_usernames = [user['username'] for user in users if user['username'] in usernames or
                               usernames.add(user['username'])]
        if duplicate_usernames:
            return response.bad_request({'duplicate_usernames': duplicate_usernames})
        emails = set()
        duplicate_emails = [user['email'] for user in users if user['email'] in emails or
                            emails.add(user['email'])]
        if duplicate_emails:
            return response.bad_request({'duplicate_emails': duplicate_emails})

        # Ensure the username and email for all users to be invited do not belong to existing users.
        existing_usernames = list(User.objects.filter(username__in=[user['username'] for user in users])
                                  .values_list('username', flat=True))
        if existing_usernames:
            return response.bad_request({'existing_usernames': existing_usernames})
        existing_emails = list(User.objects.filter(email__in=[user['email'] for user in users])
                               .values_list('email', flat=True))
        if existing_emails:
            return response.bad_request({'existing_emails': existing_emails})

        created_user_ids = []
        try:
            users_to_create = [
                factory.make_user(
                    username=user['username'],
                    email=user['email'],
                    full_name=user['full_name'],
                    is_teacher='is_teacher' in user and user['is_teacher'],
                    is_active=False,
                    save=False
                )
                for user in users
            ]
            created_user_ids = [user.id for user in User.objects.bulk_create(users_to_create)]
            send_invite_emails.delay(created_user_ids)
        except Exception as e:
            capture_exception(e)
            return response.bad_request('An error occured while creating new users.')

        return response.success(description=f"Successfully invited {len(created_user_ids)} users.")
