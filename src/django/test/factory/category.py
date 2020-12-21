import colorsys
import random
from test.factory.file_context import RichTextCategoryDescriptionFileContextFactory

import factory

import VLE.models


def random_bright_HSL_color():
    """
    Hue: [0, 1] (In JS this is commonly mapped to [0, 360])
    Saturation: [0, 1]
    Lightness: [0, 1]
    """
    hue = random.random()

    saturation_floor = 0.5
    saturation = random.random() * (1 - saturation_floor) + saturation_floor

    lightness_floor = 0.4
    lightness = random.random() * (1 - lightness_floor) + lightness_floor

    return (hue, saturation, lightness)


def random_bright_RGB_color_code():
    h, s, l = random_bright_HSL_color() # noqa E741
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
