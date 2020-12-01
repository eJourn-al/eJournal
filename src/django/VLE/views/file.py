from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
import VLE.validators as validators
from VLE.models import FileContext
from VLE.serializers import FileSerializer


class FileView(viewsets.ViewSet):
    def retrieve(self, request, pk):
        """Get a FileContext file by ID"""
        access_id, = utils.optional_params(request.query_params, 'access_id')
        if access_id:
            file = FileContext.objects.get(pk=pk, access_id=access_id)
            return response.file(file, file.file_name)

        file = FileContext.objects.get(pk=pk)

        if file.is_temp and not request.user == file.author:
            return response.forbidden('You are not allowed to view this file.')

        if file.comment:
            request.user.check_can_view(file.comment)
        elif file.journal:
            request.user.check_can_view(file.journal)
        elif file.assignment:
            request.user.check_can_view(file.assignment)
        else:
            if not request.user.can_view(file.author):
                return response.forbidden('You are not allowed to view this file.')

        return response.file(file, file.file_name)

    def create(self, request):
        if not (request.FILES and 'file' in request.FILES):
            return response.bad_request('No accompanying file found in the request.')

        validators.validate_user_file(request.FILES['file'], request.user)

        file = FileContext.objects.create(
            file=request.FILES['file'],
            file_name=request.FILES['file'].name,
            author=request.user,
            is_temp=True,
            in_rich_text='in_rich_text' in request.POST
        )

        return response.created(FileSerializer(file, context={'user': request.user}).data)

    @action(['get'], detail=True)
    def access_id(self, request, pk):
        """Get a FileContext file by access_id"""
        file = FileContext.objects.get(access_id=pk)
        return response.file(file, file.file_name)

    def get_permissions(self):
        if utils.optional_params(self.request.query_params, 'access_id')[0] and self.request.method == 'GET':
            return [AllowAny()]
        else:
            return [permission() for permission in self.permission_classes]
