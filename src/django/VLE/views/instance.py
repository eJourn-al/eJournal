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

    def get_permissions(self):
        if self.request.path == '/instance/0/' and self.request.method == 'GET':
            return [AllowAny()]
        else:
            return [permission() for permission in self.permission_classes]
