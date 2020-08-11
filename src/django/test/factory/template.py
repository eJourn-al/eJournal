from test.factory.field import FieldFactory

import factory

from VLE.models import Field


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Template'

    format = factory.SubFactory('test.factory.format.FormatFactory')
    name = 'Empty Template'

    @factory.post_generation
    def add_fields(self, create, extracted):
        if not create:
            return

        if extracted:
            for field in extracted:
                self.field_set.add(field)


class TextTemplateFactory(TemplateFactory):
    name = 'Default Text'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        FieldFactory(type=Field.TEXT, title='title', template=self, required=True)
        FieldFactory(type=Field.TEXT, title='summary', template=self, required=True)
        FieldFactory(type=Field.TEXT, title='optional', template=self, required=False)


class ColloquiumTemplateFactory(TemplateFactory):
    name = 'Colloquium'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        FieldFactory(type=Field.TEXT, title='Title', template=self, required=True)
        FieldFactory(type=Field.TEXT, title='Summary', template=self, required=True)
        FieldFactory(type=Field.FILE, title='Proof of presence', template=self, options='png, jpg, svg', required=False)


class TemplateAllTypesFactory(TemplateFactory):
    name = 'all types'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        [FieldFactory(type=t, template=self, required=False) for t, _ in Field.TYPES]
        # Create an additional file field which only allows images
        FieldFactory(type=Field.FILE, template=self, required=False, options='png, jpg, svg')
