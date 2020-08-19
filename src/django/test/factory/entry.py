import random
import test.factory

import factory
from django.core.exceptions import ValidationError
from django.utils import timezone

import VLE.models


def _set_template(self, create, extracted, **kwargs):
    '''
    Defaults to the first available template of the assignment, else generates a TextTemplate

    kwargs allow the format to be set to a different format than the assignment, as this is the case for imported
    entries.
    '''
    if not create:
        return

    if isinstance(extracted, VLE.models.Template):
        self.template = extracted
    elif kwargs:
        self.template = test.factory.TextTemplate(
            **{'format': self.node.journal.assignment.format, **kwargs})
    else:
        if self.node.journal.assignment.format.template_set.exists():
            self.template = random.choice(self.node.journal.assignment.format.template_set.all())
        else:
            self.template = test.factory.TextTemplate(format=self.node.journal.assignment.format)
    self.save()


class UnlimitedEntryFactory(factory.django.DjangoModelFactory):
    '''
    Creates an 'unlimited' template entry.

    Will generate content for all allowed fields of its template.

    Methods:
        author: Set author as given user or first author of the associated journal. Has to be an author of the journal.
        template: Set template as given template or random template of the associated assignment. If not found, creates
            a text template.
    '''
    class Meta:
        model = 'VLE.Entry'

    node = factory.RelatedFactory(
        'test.factory.node.NodeFactory', factory_related_name='entry', type=VLE.models.Node.ENTRY)
    last_edited = factory.LazyFunction(timezone.now)
    template = None

    @factory.post_generation
    def author(self, create, extracted, **kwargs):
        test.factory.rel_factory(self, create, extracted, 'author', VLE.models.User, factory=None,
                                 default=self.node.journal.authors.first().user)

    @factory.post_generation
    def template(self, create, extracted, **kwargs):
        _set_template(self, create, extracted, **kwargs)

    @factory.post_generation
    def grade(self, create, extracted, **kwargs):
        '''
        Defaults to no grade unless passed or mentioned via deep syntax,
        e.g. factory.UnlimitedEntry(grade__published=True)
        '''
        if not create:
            return

        if isinstance(extracted, VLE.models.Grade) or extracted is None and not kwargs:
            self.grade = extracted
        else:
            self.grade = test.factory.Grade(**{**kwargs, 'entry': self})

        self.save()

    @factory.post_generation
    def gen_content(self, create, extracted):
        if not create:
            return

        for field in self.template.field_set.all():
            if field.type == VLE.models.Field.NO_SUBMISSION:
                continue
            test.factory.Content(field=field, entry=self)

    @factory.post_generation
    def validate(self, create, extracted):
        if not create:
            return

        # TODO JIR: Move to model validators
        if not self.node:
            raise ValidationError('Entry created without node')
        if not self.node.journal.authors.filter(user=self.author).exists():
            if not VLE.models.Journal.all_objects.filter(pk=self.node.journal.pk, author=self.author).exists():
                # Most likely teacher, allow this for now
                # raise ValidationError('Entry created by user only found via all journal query.')
                pass
            else:
                raise ValidationError('Entry created by user not part of journal.')


class PresetEntryFactory(UnlimitedEntryFactory):
    @factory.post_generation
    def fix_node(self, create, extracted, **kwargs):
        if not create:
            return

        if self.node.preset:
            # We have an additional node which was added to the journal by the PresetNodeFactory
            correct_node = self.node.preset.node_set.filter(journal=self.node.journal).first()
            assert correct_node.pk != self.node
            related_factory_generated_node = self.node
            self.node = correct_node
            related_factory_generated_node.delete()

            # PresetNode template should match entry template, initialisation conflict, default to forced_template
            self.template = self.node.preset.forced_template
        else:
            # No DeadlinePreset has been created yet, so we iniate one
            # Because we already have a node link (used for deep syntax), we exclude the entries journal, otherwise
            # the PresetNode factory would create an additional node for this entry.
            self.node.preset = test.factory.DeadlinePresetNode(
                format=self.node.journal.assignment.format,
                forced_template=self.template,
                add_node_to_journals__exclude=[self.node.journal],
            )
            # All thats left now is to set the node to the correct type.
            self.node.type = VLE.models.Node.ENTRYDEADLINE

        self.node.save()

    @factory.post_generation
    def validate(self, create, extracted):
        if not create:
            return

        if self.node is None:
            raise ValidationError('Dangling preset entry (node = None)')
        if self.template.pk != self.node.preset.forced_template.pk:
            raise ValidationError('Deadline Entry template does not match its PresetNode\'s template')
