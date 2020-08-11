import json
import random
from test.factory.file_context import FileContentFileContextFactory, RichTextContentFileContextFactory

import factory

from VLE.models import Field
from VLE.utils.error_handling import VLEProgrammingError


class ContentFactory(factory.django.DjangoModelFactory):
    '''
    Generates valid content for the selected (:model:`VLE.Field`): type

    The number of desired RichText images can be specified as 'ContentFactory(data__n_files=Number)' defaults to one
    '''
    class Meta:
        model = 'VLE.Content'

    entry = factory.SubFactory('test.factory.entry.EntryFactory')
    field = factory.SubFactory('test.factory.field.FieldFactory')

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
                    RichTextContentFileContextFactory(content=self)
                # The factory appends the created download urls, so here we prepend so text
                self.data = factory.Faker('text').generate() + self.data if self.data else ''
            elif self.field.type == Field.FILE:
                # The factory sets the data to the fc id
                FileContentFileContextFactory(content=self)
            elif self.field.type == Field.VIDEO:
                # According to our current validators this can be any url
                self.data = 'https://www.youtube.com/watch?v=lJMNA7UcpxE'
            elif self.field.type == Field.URL:
                self.data = factory.Faker('url').generate()
            elif self.field.type == Field.DATE:
                self.data = factory.Faker('date').generate()
            elif self.field.type == Field.DATETIME:
                self.data = factory.Faker('date_time').generate().strftime('%Y-%m-%dT%H:%M:%S')
            elif self.field.type == Field.SELECTION:
                self.data = random.choice(json.loads(self.field.options))
            elif self.field.type == Field.NO_SUBMISSION:
                raise VLEProgrammingError('Content should never be generated for a no submission field')

        self.save()
