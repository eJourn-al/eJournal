import random
import factory

from VLE.models import Field


def _verbose_field_type(type):
    for short, verbose in Field.TYPES:
        if short == type:
            return verbose


def _select_location(g_field):
    fields = g_field.template.set.all()

    if not fields.exists():
        return 0

    return fields.order_by('-location')[0].location + 1


class FieldFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Field'

    template = factory.SubFactory('test.factory.template.TemplateFactory')

    type = factory.LazyAttribute(lambda o: random.choice([t for t, _ in Field.TYPES]))
    title = factory.LazyAttribute(lambda o: '%s field title' % (_verbose_field_type(o.type)))
    description = factory.LazyAttribute(lambda o: '%s field description' % (_verbose_field_type(o.type)))
    options = factory.LazyAttribute(lambda o: ['A', 'B', 'C'] if o.type == Field.SELECTION else None))
    location = factory.LazyAttribute(lambda o: _select_location(o))
    required = True


class TextFieldFactory(FieldFactory):
    type = Field.TEXT


class RichTextFieldFactory(FieldFactory):
    type = Field.RICH_TEXT


class FileFieldFactory(FieldFactory):
    type = Field.FILE
    # options = ['jpg', 'png']


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
    options = ['A', 'B', 'C']


class NoSubmissionFieldFactory(FieldFactory):
    type = Field.NO_SUBMISSION
