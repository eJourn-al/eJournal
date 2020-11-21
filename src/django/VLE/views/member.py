"""
member.py.

In this file are all the group member api requests.
"""
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from VLE.models import Group, Participation
from VLE.serializers import ParticipationSerializer, UserSerializer


class MemberView(viewsets.ViewSet):

    def list(self, request):
        group_id, = utils.required_typed_params(request.query_params, (int, 'group_id'))
        group = Group.objects.get(pk=group_id)

        request.user.check_permission('can_edit_course_user_group', group.course)

        serializer = ParticipationSerializer(
            ParticipationSerializer.setup_eager_loading(Participation.objects.filter(groups=group)),
            context={'course': group.course, 'user': request.user},
            many=True
        )
        return response.success({'members': serializer.data})

    def create(self, request):
        group_id, user_id = utils.required_typed_params(request.data, (int, 'group_id'), (int, 'user_id'))
        group = Group.objects.get(pk=group_id)
        member = Participation.objects.get(user=user_id, course=group.course)

        request.user.check_permission('can_edit_course_user_group', group.course)

        member.groups.add(group)
        member.save()
        users = UserSerializer(
            group.course.users, context={'course': group.course, 'user': request.user}, many=True).data
        return response.created({'participants': users})

    def destroy(self, request, pk):
        user_id, = utils.required_typed_params(request.query_params, (int, 'user_id'))
        group = Group.objects.get(pk=pk)
        member = Participation.objects.get(user=user_id, course=group.course)

        request.user.check_permission('can_edit_course_user_group', group.course)

        member.groups.remove(group)
        member.save()
        return response.success(description='Removed {} from {}.'.format(member.user.full_name, group.name))
