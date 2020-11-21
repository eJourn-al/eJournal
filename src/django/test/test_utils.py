import datetime
import json
import test.factory as factory
import test.utils.performance
from test.utils import api

from django.conf import settings
from django.db import connections
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import VLE.models
import VLE.utils.responses
from VLE.serializers import UserSerializer, prefetched_objects
from VLE.utils.error_handling import VLEProgrammingError
from VLE.utils.generic_utils import get_sorted_nodes


class UtilsTest(TestCase):
    def test_code_version_in_utils_json_response(self):
        json_resp = VLE.utils.responses.json_response()
        assert json.loads(json_resp.content)['code_version'] == settings.CODE_VERSION

    def test_code_version_in_responses(self):
        student = factory.Student()
        student2 = factory.Student()

        resp = api.get(self, 'users', params={'pk': student.pk}, user=student)
        assert resp['code_version'] == settings.CODE_VERSION, 'Code version is serialized on success'

        resp = api.get(self, 'users', params={'pk': student2.pk}, user=student, status=403)
        assert resp['code_version'] == settings.CODE_VERSION, 'Code version is serialized on error'

        resp = api.post(self, 'forgot_password', params={'identifier': student.username})
        assert resp['code_version'] == settings.CODE_VERSION, 'Code version is also serialized for anom users'

    def test_get_sorted_nodes(self):
        journal = factory.Journal(entries__n=0)
        progress_preset = factory.ProgressPresetNode(
            format=journal.assignment.format, due_date=timezone.now() + datetime.timedelta(weeks=1))
        unlimited_entry = factory.UnlimitedEntry(node__journal=journal)
        preset_entry = factory.PresetEntry(node__journal=journal)
        preset_entry.node.preset.due_date = timezone.now() - datetime.timedelta(days=1)
        preset_entry.node.preset.save()

        with self.assertNumQueries(1):
            list(get_sorted_nodes(journal))

        nodes = get_sorted_nodes(journal)
        assert nodes.get(preset=progress_preset).sort_due_date == progress_preset.due_date, \
            'Preset timeline nodes should be ordered by their due date'
        assert nodes.get(preset=progress_preset) == nodes.last()

        assert nodes.get(entry=unlimited_entry).sort_due_date == unlimited_entry.creation_date, \
            'Unlimited entry nodes should be ordered by their respective entry creation date'

        assert nodes.get(entry=preset_entry).sort_due_date == preset_entry.node.preset.due_date, \
            'Preset deadline nodes (even filled in) should be ordered by their preset due date'
        assert nodes.get(entry=preset_entry) == nodes.first()

    def test_assert_num_queries_less_than(self):
        entry = factory.UnlimitedEntry()

        with test.utils.performance.assert_num_queries_less_than(2):
            list(VLE.models.Entry.objects.filter(pk=entry.pk))

        with self.assertRaises(AssertionError):
            with test.utils.performance.assert_num_queries_less_than(2):
                list(VLE.models.Entry.objects.filter(pk=entry.pk).prefetch_related('content_set'))

    def test_query_context_manager(self):
        def check_context_query_count(context, value):
            assert len(context.captured_queries) == value
            assert context.final_queries - context.initial_queries == value

        entry = factory.UnlimitedEntry()

        with CaptureQueriesContext(connections['default']) as context:
            VLE.models.Entry.objects.count()
        check_context_query_count(context, 1)

        with CaptureQueriesContext(connections['default']) as context:
            list(VLE.models.Entry.objects.filter(pk=entry.pk).prefetch_related('content_set'))
        check_context_query_count(context, 2)

    def test_queries_invariant_to_db_size(self):
        test.utils.performance.queries_invariant_to_db_size(
            VLE.models.Journal.objects.count,
            [factory.Journal]
        )

        def variant_example():
            for j in VLE.models.Journal.objects.all():  # query invariant to number of journals
                j.author  # each access triggers query (without prefetch)

        with self.assertRaises(AssertionError):
            test.utils.performance.queries_invariant_to_db_size(
                variant_example,
                [factory.Journal]
            )

    def test_extended_model_serializer(self):
        user = factory.Student()
        user2 = factory.Student()

        # Context is enforced for the serializer (instance, read)
        with self.assertRaises(VLEProgrammingError):
            UserSerializer(user).data
        # Context is enforced for the serializer (bulk, read)
        with self.assertRaises(VLEProgrammingError):
            UserSerializer(VLE.models.User.objects.filter(pk__in=[user.pk, user2.pk]), many=True).data

        # Context is enforced for the serializer (instance, update)
        with self.assertRaises(VLEProgrammingError):
            serializer = UserSerializer(user, data={'full_name': 'new name'}, partial=True)
            serializer.is_valid()
            serializer.save()
        # Context enforcement is not implemented for the serializer (bulk, update)
        with self.assertRaises(VLEProgrammingError):
            serializer = UserSerializer([user, user2], data={'full_name': 'new name'}, partial=True)
            serializer.is_valid()
            serializer.save()

        # Context is enforced for the serializer (instance, create)
        with self.assertRaises(VLEProgrammingError):
            serializer = UserSerializer(data={'full_name': 'new name'}, partial=True)
            serializer.is_valid()
            serializer.save()
        # Context is enforced for the serializer (bulk, create)
        with self.assertRaises(VLEProgrammingError):
            serializer = UserSerializer(data=[{'full_name': 'new name'}], many=True, partial=True)
            serializer.is_valid()
            serializer.save()

    def test_prefetched_objects(self):
        group = factory.Group()
        participation = factory.Participation()

        instance = VLE.models.Participation.objects.filter(pk=participation.pk).prefetch_related('groups').get()
        value, prefetched = prefetched_objects(instance, 'groups')
        assert not prefetched

        participation.groups.add(group)

        instance = VLE.models.Participation.objects.filter(pk=participation.pk).prefetch_related('groups').get()
        value, prefetched = prefetched_objects(instance, 'groups')
        assert prefetched
        assert value[0] == group
