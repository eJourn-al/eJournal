import datetime
import test.factory

import factory
from django.conf import settings

import VLE.models
from VLE.serializers import TemplateSerializer


class PresetNodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    format = factory.SubFactory('test.factory.format.FormatFactory')
    due_date = factory.SelfAttribute('format.assignment.due_date')

    @factory.post_generation
    def n_att_files(self, create, extracted):
        if not create:
            return

        if extracted and isinstance(extracted, int):
            for _ in range(extracted):
                test.factory.AttachedPresetNodeFileContext(assignment=self.format.assignment, preset=self)

    @factory.post_generation
    def n_rt_files(self, create, extracted):
        if not create:
            return

        if extracted and isinstance(extracted, int):
            for _ in range(extracted):
                test.factory.RichTextPresetNodeDescriptionFileContext(assignment=self.format.assignment, preset=self)


class ProgressPresetNodeFactory(PresetNodeFactory):
    class Meta:
        model = 'VLE.PresetNode'

    type = VLE.models.Node.PROGRESS
    display_name = 'Progress goal'
    description = 'Progress node description'

    target = 5


class DeadlinePresetNodeFactory(PresetNodeFactory):
    class Meta:
        model = 'VLE.PresetNode'

    type = VLE.models.Node.ENTRYDEADLINE
    description = 'Entrydeadline node description'

    unlock_date = factory.SelfAttribute('format.assignment.unlock_date')
    lock_date = factory.SelfAttribute('format.assignment.lock_date')

    forced_template = factory.SubFactory('test.factory.template.TemplateFactory',
                                         format=factory.SelfAttribute('..format'))
    display_name = factory.SelfAttribute('forced_template.name')


def _create_and_add_temp_files_to_description_params(kwargs, params, n_files_in_description):
    author = kwargs.pop('author', kwargs['format'].assignment.author)

    for _ in range(n_files_in_description):
        fc = test.factory.TempFileContext(author=author)
        params['description'] += f'<img src="{fc.download_url(access_id=fc.access_id)}"/>'


def _clean_params_and_convert_dates_to_str(params):
    params.pop('_state')

    for key, value in params.items():
        if isinstance(value, datetime.datetime):
            params[key] = value.strftime(settings.ALLOWED_DATETIME_FORMAT)


class ProgressPresetNodeCreationParamsFactory(factory.Factory):
    class Meta:
        model = dict

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        n_files_in_description = kwargs.pop('n_files_in_description', 0)

        params = ProgressPresetNodeFactory.build(**kwargs).__dict__
        params['assignment_id'] = kwargs['format'].assignment.pk
        params['attached_files'] = kwargs.pop('attached_files', [])

        _clean_params_and_convert_dates_to_str(params)
        _create_and_add_temp_files_to_description_params(kwargs, params, n_files_in_description)

        return params


class DeadlinePresetNodeCreationParamsFactory(factory.Factory):
    class Meta:
        model = dict

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        n_files_in_description = kwargs.pop('n_files_in_description', 0)

        params = DeadlinePresetNodeFactory.build(**kwargs).__dict__
        params['assignment_id'] = kwargs['format'].assignment.pk
        params['attached_files'] = kwargs.pop('attached_files', [])

        params['template'] = TemplateSerializer(
            TemplateSerializer.setup_eager_loading(
                VLE.models.Template.objects.filter(pk=kwargs['forced_template'].pk)
            ).get(),
        ).data

        _clean_params_and_convert_dates_to_str(params)
        _create_and_add_temp_files_to_description_params(kwargs, params, n_files_in_description)

        return params
