from test.factory.file_context import RichTextCategoryDescriptionFileContextFactory

import factory

import VLE.models


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Category'

    name = factory.Sequence(lambda n: f"{factory.Faker('word').generate().capitalize()} {n}")
    description = ''
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    author = factory.SelfAttribute('assignment.author')
    color = factory.Faker('color', luminosity='bright')

    @factory.post_generation
    def templates(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, VLE.models.Template):
            self.templates.set([extracted])
        elif isinstance(extracted, list):
            self.templates.set(extracted)

    @factory.post_generation
    def n_rt_files(self, create, extracted):
        if not create:
            return

        if extracted and isinstance(extracted, int):
            for _ in range(extracted):
                RichTextCategoryDescriptionFileContextFactory(category=self)
