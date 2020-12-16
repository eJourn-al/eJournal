import colorsys
import random
from test.factory.file_context import RichTextCategoryDescriptionFileContextFactory

import factory

import VLE.models


def random_bright_RGB_color_code():
    """Yields random bright color: https://stackoverflow.com/a/43437435"""
    h, s, l = random.random(), 0.5 + random.random() / 2.0, 0.4 + random.random() / 5.0 # noqa E741
    r, g, b = [int(256 * i) for i in colorsys.hls_to_rgb(h, l, s)]
    return '#%x%x%x' % (r, g, b)


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Category'

    name = factory.Sequence(lambda n: f"{factory.Faker('word').generate()} {n}")
    description = ''
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    author = factory.SelfAttribute('assignment.author')
    color = factory.LazyFunction(random_bright_RGB_color_code)

    @factory.post_generation
    def templates(self, create, extracted, **kwargs):
        if not create or extracted is False:
            return

        if isinstance(extracted, VLE.models.Template):
            self.templates.set([extracted])
        elif isinstance(extracted, list):
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
