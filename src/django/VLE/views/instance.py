"""
instance.py.

In this file are all the instance api requests.
"""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

import VLE.utils.responses as response
from VLE.models import Instance
from VLE.serializers import InstanceSerializer


class InstanceView(viewsets.ViewSet):
    """Instance view.

    This class creates the following api paths:
    GET /instance/0 -- gets the instance information
    PATCH /instance/0 -- partially update the instance infromation
    """
    def retrieve(self, request, pk=0):
        """Get all instance details."""
        instance = Instance.objects.get_or_create(pk=1)[0]

        return response.success({'instance': InstanceSerializer(instance).data})

    def partial_update(self, request, *args, **kwargs):
        """Update instance details.

        Arguments:
        request -- request data
            data -- the new data for the journal

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

    def get_permissions(self):
        if self.request.path == '/instance/0/' and self.request.method == 'GET':
            return [AllowAny()]
        else:
            return [permission() for permission in self.permission_classes]
