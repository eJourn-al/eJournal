import json
import random
from test.factory.file_context import FileContentFileContextFactory, RichTextContentFileContextFactory

import factory

from VLE.models import Content, Field
from VLE.utils.error_handling import VLEProgrammingError


class ContentFactory(factory.django.DjangoModelFactory):
    '''
    Generates valid content for the selected (:model:`VLE.Field`): type

    Kwargs:
        data__n_files (int): The number of desired RichText images defaults to one.

    Does not support deep syntax for the generated FileContext models.
    '''
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
            if self.field.type == Field.TEXT:
                self.data = factory.Faker('text').generate()
            elif self.field.type == Field.RICH_TEXT:
                # NOTE: Params are not available in post generation
                # https://github.com/FactoryBoy/factory_boy/issues/544
                for _ in range(kwargs['n_files'] if 'n_files' in kwargs else 1):
                    # TODO deep syntax could be made available by using a dedicated class with its own related
                    # factory. Could be done via traits as well, could these be unlocked based on field type?
                    # Same for FileContentFileContextFactory
                    RichTextContentFileContextFactory(content=self, author=self.entry.author)
                # The factory appends the created download urls, so here we prepend so text
                self.data = factory.Faker('text').generate() + self.data if self.data else ''
            elif self.field.type == Field.FILE:
                # The factory sets the data to the fc id
                extention = random.choice(self.field.options.split(', ')) if self.field.options else None
                file_name = factory.Faker('file_name', extension=extention).generate()
                FileContentFileContextFactory(content=self, file__filename=file_name, author=self.entry.author)
            elif self.field.type == Field.VIDEO:
                # According to our current validators this can be any url
                self.data = 'https://www.youtube.com/watch?v=lJMNA7UcpxE'
            elif self.field.type == Field.URL:
                self.data = factory.Faker('url').generate()
            elif self.field.type == Field.DATE:
                self.data = factory.Faker('time', pattern=Field.ALLOWED_DATE_FORMAT).generate()
            elif self.field.type == Field.DATETIME:
                self.data = factory.Faker('time', pattern=Field.ALLOWED_DATETIME_FORMAT).generate()
            elif self.field.type == Field.SELECTION:
                self.data = random.choice(json.loads(self.field.options))
            elif self.field.type == Field.NO_SUBMISSION:
                raise VLEProgrammingError('Content should never be generated for a no submission field')

        self.save()
