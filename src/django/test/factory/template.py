import test.factory

import factory

from VLE.models import Category, Field


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Template'

    name = factory.Sequence(lambda x: "Template {}".format(x))

    # Forces format specification
    format = None

    @factory.post_generation
    def add_fields(self, create, extracted):
        if not create:
            return

        if isinstance(extracted, list):
            for kwargs in extracted:
                test.factory.Field(**{**kwargs, 'template': self})

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, Category):
            self.categories.set([extracted])
        elif isinstance(extracted, list):
            self.categories.set(extracted)
        elif isinstance(extracted, int):
            for _ in range(extracted):
                test.factory.Category(assignment=self.format.assignment, templates=self)


class MentorgesprekTemplateFactory(TemplateFactory):
    name = 'Mentorgesprek'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        test.factory.Field(type=Field.RICH_TEXT, title='Title', template=self, required=True)


class TextTemplateFactory(TemplateFactory):
    name = 'Default Text'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        test.factory.Field(type=Field.TEXT, title='Title', template=self, required=True)
        test.factory.Field(type=Field.TEXT, title='Summary', template=self, required=True)
        test.factory.Field(type=Field.TEXT, title='Optional', template=self, required=False)


class FilesTemplateFactory(TemplateFactory):
    name = 'Files'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        test.factory.Field(type=Field.FILE, title='IMG', template=self,
                           options='bmp, gif, ico, cur, jpg, jpeg, jfif, pjpeg, pjp, png, svg', required=False)
        test.factory.Field(type=Field.FILE, title='FILE', template=self, required=False)
        test.factory.Field(type=Field.FILE, title='PDF', template=self, options='pdf', required=False)


class ColloquiumTemplateFactory(TemplateFactory):
    name = 'Colloquium'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        test.factory.Field(type=Field.TEXT, title='Title', template=self, required=True)
        test.factory.Field(type=Field.RICH_TEXT, title='Summary', template=self, required=True)
        test.factory.Field(type=Field.RICH_TEXT, title='Experience', template=self, required=True)
        test.factory.Field(type=Field.TEXT, title='Requested Points', template=self, required=True)
        test.factory.Field(type=Field.FILE, title='Proof', template=self, options='png, jpg, svg', required=False)


class TemplateAllTypesFactory(TemplateFactory):
    name = 'all types'

    @factory.post_generation
    def gen_fields(self, create, extracted):
        [test.factory.Field(type=t, template=self, required=False) for t, _ in Field.TYPES]
        # Create an additional file field which only allows images
        test.factory.Field(type=Field.FILE, template=self, required=False, options='png, jpg, svg')


class TemplateCreationParamsFactory(factory.Factory):
    class Meta:
        model = dict

    name = factory.Sequence(lambda x: f"Template {x + 1}".format(x))
    allow_custom_categories = False
    default_grade = None
    preset_only = True

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        assert kwargs['assignment_id'], 'assignment_id is a required parameter key for template creation'

        n_fields = kwargs.pop('n_fields', 1)
        n_fields_with_file_in_description = kwargs.pop('n_fields_with_file_in_description', 0)
        author = kwargs.pop('author', None)

        kwargs['field_set'] = []
        for i in range(n_fields):
            description = ''

            if i < n_fields_with_file_in_description:
                assert author, 'author is a required kwarg in order to generate temporary files.'

                fc = test.factory.TempFileContext(author=author)
                description = f'<img src="{fc.download_url(access_id=fc.access_id)}"/>'

            kwargs['field_set'].append({
                'type': Field.TEXT,
                'title': 'Title',
                'description': description,
                'options': '',
                'location': i,
                'required': True,
            })

        return kwargs
