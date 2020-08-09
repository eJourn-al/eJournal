import factory

from VLE.models import Field
from test.factory.field import FieldFactory


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Template'

    format = factory.SubFactory('test.factory.format.FormatFactory')
    name = 'Colloquium'

    field_set = factory.RelatedFactoryList(
        'test.factory.field.FieldFactory', factory_related_name='template', size=3, type=Field.TEXT)


class TemplateAllTypesFactory(TemplateFactory):
    name = 'all types'

    @factory.post_generation
    def field_set(self, create, extracted):
        if not create:
            return

        [FieldFactory(type=t, template=self, required=False) for t, _ in Field.TYPES]
        # Create a custom img field ontop
        FieldFactory(type=Field.FILE, template=self, required=False, options='png, jpg, svg')
