import random
import factory

from VLE.models import Field


def _verbose_field_type(type):
    for short, verbose in Field.TYPES:
        if short == type:
            return verbose


def _select_location(g_field):
    fields = g_field.template.field_set.all()

    if not fields.exists():
        return 0

    return fields.order_by('-location')[0].location + 1


def _gen_options(g_field):
    if g_field.type == Field.SELECTION:
        return '["a", "b", "c"]'
    # TODO JIR: Make content factory adaptive based on field..
    # if g_field.type == Field.FILE
    #     return 'bmp, gif, ico, cur, jpg, jpeg, jfif, pjpeg, pjp, png, svg'
    return None


class FieldFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Field'

    template = factory.SubFactory('test.factory.template.TemplateFactory')

    type = factory.LazyAttribute(lambda o: random.choice([t for t, _ in Field.TYPES if t != Field.NO_SUBMISSION]))
    title = factory.LazyAttribute(lambda o: '%s field title' % (_verbose_field_type(o.type)))
    description = factory.LazyAttribute(lambda o: '%s field description' % (_verbose_field_type(o.type)))
    options = factory.LazyAttribute(lambda o: _gen_options(o))
    location = factory.LazyAttribute(lambda o: _select_location(o))
    required = True


class TextFieldFactory(FieldFactory):
    type = Field.TEXT


class RichTextFieldFactory(FieldFactory):
    type = Field.RICH_TEXT


class FileFieldFactory(FieldFactory):
    type = Field.FILE
    # options = '["jpg", "png"]'


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
