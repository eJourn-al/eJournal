"""
admin.py.

In this file are all the admin api requests.
"""
from django.core.paginator import Paginator
from rest_framework import viewsets
from rest_framework.decorators import action
from sentry_sdk import capture_message

import VLE.factory as factory
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Instance, User
from VLE.serializers import InstanceSerializer, UserOverviewSerializer
from VLE.tasks import send_invite_email


class AdminView(viewsets.ViewSet):
    """Admin view.

    This class creates the following api paths:
    TODO
    """
    @action(methods=['post'], detail=False)
    def invite_users(self, request):
        """Invite new users to eJournal.

        This will create accounts for the invited users, which they can activate through an invite link.

        Arguments:
        TODO
        """
        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to invite new users.')

        users, = utils.required_params(request.data, 'users')

        # Ensure a username and email are specified for all users to be invited.
        if any([not user['full_name'] for user in users]):
            return response.bad_request('Please specify a full name for all users.')
        if any([not user['username'] for user in users]):
            return response.bad_request('Please specify a username for all users.')
        if any([not user['email'] for user in users]):
            return response.bad_request('Please specify an email for all users.')

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
                                  .values_list('username', flat=True).distinct())
        if existing_usernames:
            return response.bad_request({'existing_usernames': existing_usernames})
        existing_emails = list(User.objects.filter(email__in=[user['email'] for user in users])
                               .values_list('email', flat=True).distinct())
        if existing_emails:
            return response.bad_request({'existing_emails': existing_emails})
        invalid_emails = [user['email'] for user in users]
        if existing_emails:
            return response.bad_request({'existing_emails': existing_emails})

        created_user_ids = []
        try:
            for user in users:
                created_user = factory.make_user(username=user['username'], email=user['email'],
                                                 full_name=user['full_name'], is_teacher=user['is_teacher'],
                                                 is_active=False)
                created_user_ids.append(created_user.id)
                print(created_user_ids)
        except Exception as exception:
            capture_message('Something went wrong while inviting users: {}'.format(exception), level='error')
            for user in created_user_ids:
                User.objects.filter(pk__in=created_user_ids).delete()
        else:
            for user_id in created_user_ids:
                send_invite_email.delay(user_id)

        return response.success()

    @action(methods=['post'], detail=False)
    def update_instance(self, request):
        """Update instance details.

        Arguments:
        request -- request data
            data -- the new data for the instance

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- User not allowed to edit instance
            bad_request -- when there is invalid data in the request
        On success:
            success -- with the new instance details
        """
        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to edit instance details.')

        instance = Instance.objects.get_or_create(pk=1)[0]

        req_data = request.data
        serializer = InstanceSerializer(instance, data=req_data, partial=True)
        if not serializer.is_valid():
            return response.bad_request()
        serializer.save()

        return response.success({'instance': serializer.data})

    @action(methods=['post'], detail=False)
    def get_all_users(self, request):
        """Get all users on the instance.

        TODO: paginate (since the user count can be thousands)

        Arguments:
        TODO
        """
        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to get all users.')

        users = UserOverviewSerializer(User.objects.all().order_by('full_name'), context={'user': request.user},
            many=True).data
        return response.success({'users': users})

    @action(methods=['post'], detail=True)
    def remove_user(self, request, pk):
        """Remove a specific user.

        Arguments:
        TODO
        """
        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to remove users.')
        if str(request.user.pk) == pk:
            return response.forbidden('You are not allowed to delete your own account.')

        try:
            User.objects.get(pk=pk).delete()
        except User.DoesNotExist:
            return response.not_found('User to delete does not exist.')

        return response.success()

    @action(methods=['post'], detail=True)
    def update_teacher_status(self, request, pk):
        """Make a specific user a teacher or remove their teacher status.

        This allows the user to create new courses, in which they will automatically receive the teacher role.

        Arguments:
        TODO
        """
        if not request.user.is_superuser:
            return response.forbidden('You are not allowed to manage teachers.')

        is_teacher, = utils.required_typed_params(request.data, (bool, 'is_teacher'))

        try:
            user = User.objects.get(pk=pk)
            user.is_teacher = is_teacher
            user.save()
        except User.DoesNotExist:
            return response.not_found('User to update teacher status of does not exist.')

        return response.success()
