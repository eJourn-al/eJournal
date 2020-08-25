"""
user.py.

In this file are all the user api requests.
"""
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Preferences
from VLE.serializers import PreferencesSerializer


class PreferencesView(viewsets.ViewSet):
    def retrieve(self, request, pk):
        """Get the preferences of the requested user.

        Arguments:
        request -- request data
        pk -- user ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the user doesn't exist
        On success:
            success -- with the preferences data
        """
        pk = int(pk)
        if not (request.user.pk == pk or request.user.is_superuser):
            return response.forbidden('You are not allowed to view this users preferences.')

        preferences = Preferences.objects.get(user=pk)
        serializer = PreferencesSerializer(preferences)

        return response.success({'preferences': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """Update the preferences of a user.

        Arguments:
        request -- request data
        pk -- user ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            forbidden -- when the user is not superuser or pk is not the same as the logged in user
            not found -- when the user doesnt exist
            bad request -- when the data is invalid
        On success:
            success -- with the updated preferences
        """
        pk, = utils.required_typed_params(kwargs, (int, 'pk'))
        if not (request.user.pk == pk or request.user.is_superuser):
            return response.forbidden('You are not allowed to change this users preferences.')

        preferences = Preferences.objects.get(user=pk)
        serializer = PreferencesSerializer(preferences, data=request.data, partial=True)

        if not serializer.is_valid():
            return response.bad_request('Invalid preference data provided.')

        serializer.save()

        return response.success({'preferences': serializer.data}, description="Updated preferences.")
