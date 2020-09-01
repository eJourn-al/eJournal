from test.factory.field import FieldFactory

import factory
from VLE.models import Field


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Template'

    name = 'Empty Template'

    # Forces format specification
    format = None


class MentorgesprekTemplateFactory(TemplateFactory):
    name = 'Mentorgesprek'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        FieldFactory(type=Field.RICH_TEXT, title='Title', template=self, required=True)


class TextTemplateFactory(TemplateFactory):
    name = 'Default Text'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        FieldFactory(type=Field.TEXT, title='Title', template=self, required=True)
        FieldFactory(type=Field.TEXT, title='Summary', template=self, required=True)
        FieldFactory(type=Field.TEXT, title='Optional', template=self, required=False)


class FilesTemplateFactory(TemplateFactory):
    name = 'Files'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        FieldFactory(type=Field.FILE, title='IMG', template=self,
                     options='bmp, gif, ico, cur, jpg, jpeg, jfif, pjpeg, pjp, png, svg', required=False)
        FieldFactory(type=Field.FILE, title='FILE', template=self, required=False)
        FieldFactory(type=Field.FILE, title='PDF', template=self, options='pdf', required=False)


class ColloquiumTemplateFactory(TemplateFactory):
    name = 'Colloquium'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        FieldFactory(type=Field.TEXT, title='Title', template=self, required=True)
        FieldFactory(type=Field.RICH_TEXT, title='Summary', template=self, required=True)
        FieldFactory(type=Field.RICH_TEXT, title='Experience', template=self, required=True)
        FieldFactory(type=Field.TEXT, title='Requested Points', template=self, required=True)
        FieldFactory(type=Field.FILE, title='Proof', template=self, options='png, jpg, svg', required=False)


class TemplateAllTypesFactory(TemplateFactory):
    name = 'all types'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        [FieldFactory(type=t, template=self, required=False) for t, _ in Field.TYPES]
        # Create an additional file field which only allows images
        FieldFactory(type=Field.FILE, template=self, required=False, options='png, jpg, svg')
