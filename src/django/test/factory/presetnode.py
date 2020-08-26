import datetime

import factory
from django.utils import timezone

import VLE.models
from VLE.utils import generic_utils as utils


class PresetNodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    format = factory.SubFactory('test.factory.format.FormatFactory')

    @factory.post_generation
    def add_node_to_journals(self, create, extracted, **kwargs):
        if not create:
            return

        journals = VLE.models.Journal.all_objects.filter(assignment__format=self.format)
        if 'exclude' in kwargs:
            journals = journals.exclude(pk__in=[j.pk for j in kwargs['exclude']])

        for j in journals:
            if not j.node_set.filter(preset=self).exists():
                utils.update_journals([j], self)


class ProgressPresetNodeFactory(PresetNodeFactory):
    class Meta:
        model = 'VLE.PresetNode'

    type = VLE.models.Node.PROGRESS
    description = 'Progress node description'

    due_date = timezone.now() + datetime.timedelta(weeks=1)
    lock_date = timezone.now() + datetime.timedelta(weeks=2)

    target = 5


class DeadlinePresetNodeFactory(PresetNodeFactory):
    class Meta:
        model = 'VLE.PresetNode'

    type = VLE.models.Node.ENTRYDEADLINE
    description = 'Entrydeadline node description'

    due_date = timezone.now() + datetime.timedelta(days=3)
    lock_date = timezone.now() + datetime.timedelta(days=5)

    forced_template = factory.SubFactory('test.factory.template.TemplateFactory',
                                         format=factory.SelfAttribute('..format'))
