import io
import json
import os
import random
from test.factory.file_context import FileContentFileContextFactory, RichTextContentFileContextFactory

import factory
from django.core.exceptions import ValidationError

from VLE.models import Field
from VLE.utils.error_handling import VLEProgrammingError

IMG_FILE_PATH = '../vue/public/journal-view.png'
PDF_FILE_PATH = './VLE/management/commands/dummy.pdf'

if not (os.path.exists(IMG_FILE_PATH)):
    IMG_FILE_PATH = './src/vue/public/journal-view.png'
    PDF_FILE_PATH = './src/django/VLE/management/commands/dummy.pdf'


def _from_file_to_file(from_file):
    """
    factoryboy's FileField from_path default is ''
    """

    if isinstance(from_file, io.IOBase):
        return from_file
    if isinstance(from_file, str) and from_file != '':
        return open(from_file, 'rb')
    return ''


def gen_valid_non_file_data(field):
    if field.type not in Field.TYPES_WITHOUT_FILE_CONTEXT:
        raise VLEProgrammingError('Field type with possible FC association called')

    if field.type == Field.TEXT:
        return factory.Faker('text').generate()
    if field.type == Field.VIDEO:
        # According to our current validators this can be any url
        return 'https://www.youtube.com/watch?v=lJMNA7UcpxE'
    if field.type == Field.URL:
        return factory.Faker('url').generate()
    if field.type == Field.DATE:
        return factory.Faker('time', pattern=Field.ALLOWED_DATE_FORMAT).generate()
    if field.type == Field.DATETIME:
        return factory.Faker('time', pattern=Field.ALLOWED_DATETIME_FORMAT).generate()
    if field.type == Field.SELECTION:
        return random.choice(json.loads(field.options))
    if field.type == Field.NO_SUBMISSION:
        raise VLEProgrammingError('Content should never be generated for a no submission field')


class ContentFactory(factory.django.DjangoModelFactory):
    """
    Generates valid content for the selected (:model:`VLE.Field`): type

    Kwargs:
        data__n_files (int): The number of desired RichText images defaults to one.

    Does not support deep syntax for the generated FileContext models.

    ToDo:
        Make from_file passing argument checks clean
        Provide a way to provide more varied from file arguments
        Make from file argument compatible with field options
    """
    class Meta:
        model = 'VLE.Content'

    entry = factory.SubFactory('test.factory.entry.UnlimitedEntryFactory')
    field = factory.SubFactory('test.factory.field.FieldFactory', template=factory.SelfAttribute('..entry.template'))

    @factory.post_generation
    def data(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.data = extracted
        else:
            if self.field.type in Field.TYPES_WITHOUT_FILE_CONTEXT:
                self.data = gen_valid_non_file_data(self.field)
            elif self.field.type == Field.RICH_TEXT:
                from_file = ''
                filename = factory.Faker('file_name', category='image').generate()
                # Use a preexisintg file on os
                if 'from_file' in kwargs and not kwargs['from_file'] == '':
                    from_file = _from_file_to_file(IMG_FILE_PATH)
                    filename = factory.Faker('file_name', category='image', extension='png').generate()

                # NOTE: Params are not available in post generation
                # https://github.com/FactoryBoy/factory_boy/issues/544
                for _ in range(kwargs['n_files'] if 'n_files' in kwargs else 1):
                    RichTextContentFileContextFactory(
                        content=self,
                        author=self.entry.author,
                        file__from_file=from_file,
                        file__filename=filename,
                    )

                # The factory appends the created download urls, so here we prepend so text
                self.data = factory.Faker('text').generate() + self.data if self.data else ''
            elif self.field.type == Field.FILE:
                from_file = ''
                extention = random.choice(self.field.options.split(', ')) if self.field.options else None
                filename = factory.Faker('file_name', extension=extention).generate()
                # Use a preexisting file on os
                if 'from_file' in kwargs and not kwargs['from_file'] == '':
                    from_file = _from_file_to_file(PDF_FILE_PATH)
                    filename = factory.Faker('file_name', category='text', extension='pdf').generate()

                # The factory sets the data to the fc id
                FileContentFileContextFactory(
                    content=self,
                    file__filename=filename,
                    file__from_file=from_file,
                    author=self.entry.author
                )

    @factory.post_generation
    def validate(self, create, extracted, **kwargs):
        if not create:
            return

        if not self.entry.template.field_set.filter(pk=self.field.pk).exists():
            raise ValidationError('Content initiated for a field which is not part of its entries template.')
