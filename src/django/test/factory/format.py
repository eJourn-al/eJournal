
import test.factory

import factory

from VLE.utils.error_handling import VLEProgrammingError


class FormatFactory(factory.django.DjangoModelFactory):
    '''
    A format is only created by an Assignment. Do not initialise in isolation or via an upwards chain. E.g.
    format.Template without arguments.
    '''
    class Meta:
        model = 'VLE.Format'

    class Params:
        called_from_assignment = False

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        '''
        Blocks setting the assignment via the format.

        Because of the OneToOne relation between Assignment and Format, initialisation can become unclear:

        - factory.Format(): Should yield a format but also generate an assignment.
        - factory.Format(assignment=assignment): Should yield a format, but the assignment already has a format with
        possible instances attached to it.
        - It gets worse the further down the chain an initialisation is called. E.g. format.Content(), as this
        is linked to a format via, content.entry.node.journal.assignment.format and content.field.template.format.

        Simply only allowing an assignment to create a format removes this ambiguity.
        '''
        if not kwargs['called_from_assignment']:
            raise VLEProgrammingError('Invalid initialisation. Initialise the assignment first.')

        return kwargs

    @factory.post_generation
    def templates(self, create, extracted):
        '''
        Generates a TextTemplate and a Colloquium template by default
        '''
        if not create:
            return

        if extracted:
            for kwargs in extracted:
                template = test.factory.Template(format=self)
                test.factory.Field(**{**kwargs, 'template': template})
        elif extracted is None:
            test.factory.TextTemplate(format=self)
            test.factory.ColloquiumTemplate(format=self)
