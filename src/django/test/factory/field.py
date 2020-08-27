import random

import factory
from VLE.models import Field, Template


def _verbose_field_type(type):
    for short, verbose in Field.TYPES:
        if short == type:
            return verbose


def _select_location(g_field):
    assert isinstance(g_field.template, Template)
    if not g_field.template.field_set.exists():
        return 0
    return g_field.template.field_set.all().order_by('-location')[0].location + 1


def _gen_options(g_field):
    if g_field.type == Field.SELECTION:
        return '["a", "b", "c"]'
    return None


class FieldFactory(factory.django.DjangoModelFactory):
    '''
    Generates a field for a given template. If no template is provided a template is also generated.
    The field type is randomly chosen unless specified.

    Default yields:
        - Field
        - Template, requires a format to be intialized in advance.
    '''
    class Meta:
        model = 'VLE.Field'

    template = factory.SubFactory('test.factory.template.TemplateFactory')

    type = factory.LazyAttribute(lambda o: random.choice([t for t, _ in Field.TYPES if t != Field.NO_SUBMISSION]))
    title = factory.LazyAttribute(lambda o: '%s field title' % (_verbose_field_type(o.type)))
    description = factory.LazyAttribute(lambda o: '%s field description' % (_verbose_field_type(o.type)))
    options = factory.LazyAttribute(_gen_options)
    location = factory.LazyAttribute(_select_location)
    required = True


class TextFieldFactory(FieldFactory):
    type = Field.TEXT


class RichTextFieldFactory(FieldFactory):
    type = Field.RICH_TEXT


class FileFieldFactory(FieldFactory):
    type = Field.FILE


class VideoFieldFactory(FieldFactory):
    type = Field.VIDEO


class UrlFieldFactory(FieldFactory):
    type = Field.URL


class DateFieldFactory(FieldFactory):
    type = Field.DATE


class DateTimeFieldFactory(FieldFactory):
    type = Field.DATETIME


class SelectionFieldFactory(FieldFactory):
    type = Field.SELECTION
    options = '["A", "B", "C"]'


class NoSubmissionFieldFactory(FieldFactory):
    type = Field.NO_SUBMISSION
    required = False
    description = '<p>This is a description only field</p><p>{}</p>'.format(factory.Faker('text').generate())
