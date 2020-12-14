from test.factory.file_context import RichTextCategoryDescriptionFileContextFactory

import factory

import VLE.models


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Category'

    name = factory.Sequence(lambda n: f"{factory.Faker('word').generate()} {n}")
    description = ''
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    author = factory.SelfAttribute('assignment.author')

    @factory.post_generation
    def templates(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        if isinstance(extracted, list):
            self.templates.set(extracted)
        else:
            template = VLE.models.Template.objects.filter(format__assignment=self.assignment).order_by('?').first()
            if template:
                self.templates.add(template)

    @factory.post_generation
    def n_rt_files(self, create, extracted):
        if not create:
            return

        if extracted and isinstance(extracted, int):
            for _ in range(extracted):
                RichTextCategoryDescriptionFileContextFactory(category=self)
