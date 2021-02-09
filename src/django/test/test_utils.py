import json
import test.factory as factory
import test.utils.performance
from datetime import datetime, timedelta
from test.utils import api

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import VLE.models
import VLE.utils.generic_utils as utils
import VLE.utils.responses
from VLE.serializers import UserSerializer, prefetched_objects
from VLE.utils.error_handling import VLEParamWrongType, VLEProgrammingError
from VLE.validators import validate_youtube_url_with_video_id


class UtilsTest(TestCase):
    def test_cast_value(self):
        def test_cast_bool():
            data = {'false': 'false', 'true': 'true'}
            false, true = utils.required_typed_params(data, (bool, 'false'), (bool, 'true'))
            assert false is False, '"false" should be cast to "False"'
            assert true is True, '"true" should be cast to "True"'

            falls, normal_cast = utils.required_typed_params(
                {'falls': 'falss', 'normal_cast': '1'}, (bool, 'falls'), (bool, 'normal_cast'))
            assert falls is True, 'Any cast bool other than "true" or "false" should follow default truthy conversion'
            assert normal_cast is True, \
                'Any cast bool other than "true" or "false" should follow default truthy conversion'

        def test_cast_datetime():
            # When possible, datetimes are parsed according to our desired frontend format
            frontend_date_pickers_datetime_format = '2021-02-28T23:59:59'
            date, = utils.required_typed_params({'date': frontend_date_pickers_datetime_format}, (datetime, 'date'))
            assert date == datetime.strptime(frontend_date_pickers_datetime_format, settings.ALLOWED_DATETIME_FORMAT)

            # Sometimes incoming datetime formats are out of our hands, e.g. via LTI, parse the date as best we can
            uva_test_canvas_datetime_string = '2021-02-28 23:59'
            uva_test_canvas_datetime_format = '%Y-%m-%d %H:%M'
            date, = utils.required_typed_params({'date': uva_test_canvas_datetime_string}, (datetime, 'date'))
            assert date == datetime.strptime(uva_test_canvas_datetime_string, uva_test_canvas_datetime_format)

            # Raise wrong type on bogus date strings
            bogus_date = '21a-02-tt 14:10'
            self.assertRaises(VLEParamWrongType, utils.required_typed_params, {'date': bogus_date}, (datetime, 'date'))

            # Raise wrong type on requried empty date strings
            empty_required_date = ''
            self.assertRaises(
                VLEParamWrongType, utils.required_typed_params, {'date': empty_required_date}, (datetime, 'date'))

            # An optional empty date string is cast to None
            empty_optional_date = ''
            date, = utils.optional_typed_params({'date': empty_optional_date}, (datetime, 'date'))
            assert date is None

        test_cast_bool()
        test_cast_datetime()

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
        progress_points_preset = factory.ProgressPresetNode(
            format=journal.assignment.format,
            due_date=timezone.now() + timedelta(weeks=1),
        )
        unlimited_entry = factory.UnlimitedEntry(
            node__journal=journal,
            creation_date=timezone.now() - timedelta(days=2),
        )

        template = journal.assignment.format.template_set.first()
        deadline = factory.DeadlinePresetNode(format=journal.assignment.format, forced_template=template)
        deadline_node = journal.node_set.get(preset=deadline)
        preset_entry = factory.PresetEntry(
            node=deadline_node,
            creation_date=timezone.now() + timedelta(days=2),
        )
        preset_entry.node.preset.due_date = timezone.now() - timedelta(days=1)
        preset_entry.node.preset.save()

        with self.assertNumQueries(1):
            list(journal.get_sorted_nodes())

        nodes = journal.get_sorted_nodes()
        assert nodes.get(preset=progress_points_preset).sort_due_date == progress_points_preset.due_date, \
            'Preset timeline nodes should be ordered by their due date'
        assert nodes.get(preset=progress_points_preset) == nodes.last()

        assert nodes.get(entry=unlimited_entry).sort_due_date == unlimited_entry.creation_date, \
            'Unlimited entry nodes should be ordered by their respective entry creation date'

        assert nodes.get(entry=preset_entry).sort_due_date == preset_entry.node.preset.due_date, \
            'Preset deadline nodes (even filled in) should be ordered by their preset due date'
        assert nodes.get(entry=preset_entry) == nodes.first()

        progress_points_preset.delete()
        nodes = journal.get_sorted_nodes()
        preset_entry.node.preset = None
        preset_entry.node.save()
        assert nodes.get(entry=preset_entry).sort_due_date == preset_entry.creation_date, \
            'Deadline entries of which the preset is deleted should be sorted based on their creation date.'
        assert nodes.get(entry=unlimited_entry) == nodes.first(), \
            'After deletion of the related preset, unlimited_entry should be first. ' + \
            'The creation_date of preset_entry is AFTER the one from unlimited_entry'

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

    def test_validate_youtube_url_with_video_id(self):
        valid_youtube_video_urls = [
            'http://youtube.com/watch?v=iwGFalTRHDA',
            'http://www.youtube.com/watch?v=iwGFalTRHDA&feature=related',
            'https://youtube.com/iwGFalTRHDA',
            'http://youtu.be/n17B_uFF4cA',
            'youtube.com/iwGFalTRHDA',
            'youtube.com/n17B_uFF4cA',
            'http://www.youtube.com/watch?v=t-ZRX8984sc',
            'http://youtu.be/t-ZRX8984sc',
            'https://www.youtube.com/watch?v=DFYRQ_zQ-gk&feature=featured',
            'https://www.youtube.com/watch?v=DFYRQ_zQ-gk',
            'http://www.youtube.com/watch?v=DFYRQ_zQ-gk',
            'www.youtube.com/watch?v=DFYRQ_zQ-gk',
            'https://youtube.com/watch?v=DFYRQ_zQ-gk',
            'http://youtube.com/watch?v=DFYRQ_zQ-gk',
            'youtube.com/watch?v=DFYRQ_zQ-gk',
            'https://m.youtube.com/watch?v=DFYRQ_zQ-gk',
            'http://m.youtube.com/watch?v=DFYRQ_zQ-gk',
            'm.youtube.com/watch?v=DFYRQ_zQ-gk',
            'https://www.youtube.com/v/DFYRQ_zQ-gk?fs=1&hl=en_US',
            'http://www.youtube.com/v/DFYRQ_zQ-gk?fs=1&hl=en_US',
            'www.youtube.com/v/DFYRQ_zQ-gk?fs=1&hl=en_US',
            'youtube.com/v/DFYRQ_zQ-gk?fs=1&hl=en_US',
            'https://www.youtube.com/embed/DFYRQ_zQ-gk?autoplay=1',
            'https://www.youtube.com/embed/DFYRQ_zQ-gk',
            'http://www.youtube.com/embed/DFYRQ_zQ-gk',
            'www.youtube.com/embed/DFYRQ_zQ-gk',
            'https://youtube.com/embed/DFYRQ_zQ-gk',
            'http://youtube.com/embed/DFYRQ_zQ-gk',
            'youtube.com/embed/DFYRQ_zQ-gk',
            'https://youtu.be/DFYRQ_zQ-gk?t=120',
            'https://youtu.be/DFYRQ_zQ-gk',
            'http://youtu.be/DFYRQ_zQ-gk',
            'youtu.be/DFYRQ_zQ-gk',
            'https://www.youtube.com/HamdiKickProduction?v=DFYRQ_zQ-gk',
            '//www.youtube.com/watch?v=DFYRQ_zQ-gk',
            '//youtube.com/embed/DFYRQ_zQ-gk',
        ]

        invalid_youtube_video_urls = [
            'https://www.youtube.com/channel/UCDZkgJZDyUnqwB070OyP72g',
            'http://www.youtube.com/embed/watch?feature=player_embedded&v=r5nB9u4jjy4',  # Valid but not working atm
            'http://altotube.com/t-ZRX8984sc',
            'https://bootstrap-vue.org/',
            '',
            1,
            False,
            True,
        ]

        for valid_url in valid_youtube_video_urls:
            validate_youtube_url_with_video_id(valid_url)

        for invalid_url in invalid_youtube_video_urls:
            self.assertRaises(ValidationError, validate_youtube_url_with_video_id, invalid_url)
