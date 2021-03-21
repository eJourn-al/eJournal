import random
import test.factory

import factory
from django.core.exceptions import ValidationError
from django.utils import timezone

import VLE.models
from VLE.utils.error_handling import VLEProgrammingError


def _set_template(self, create, extracted, **kwargs):
    """
    Defaults to the first available template of the assignment, else generates a TextTemplate

    If the template is already determined, e.g. by the preset node of a DeadlineEntry, use that template.

    kwargs allow the format to be set to a different format than the assignment, as this is the case for imported
    entries.
    """
    if not create:
        return

    if self.node.preset:
        self.template = self.node.preset.forced_template
    elif isinstance(extracted, VLE.models.Template):
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


def _author(self, create, extracted, **kwargs):
    default = self.node.journal.authors.first().user
    if self.node.journal.assignment.is_group_assignment:
        default = random.choice(self.node.journal.authors.all()).user
    test.factory.rel_factory(self, create, extracted, 'author', VLE.models.User, factory=None,
                             default=default)


def _grade(self, create, extracted, **kwargs):
    """
    Defaults to no grade unless passed or mentioned via deep syntax,
    e.g. factory.UnlimitedEntry(grade__published=True)
    """
    if not create:
        return

    if isinstance(extracted, VLE.models.Grade):
        if extracted.entry != self:
            raise ValidationError('Grade assigned to entry is already linked to a different entry.')
        self.grade = extracted
    elif kwargs:
        self.grade = test.factory.Grade(**{**kwargs, 'entry': self})
    else:
        self.grade = None


def _gen_content(self, create, extracted, **kwargs):
    if not create or extracted is False:
        return

    for field in self.template.field_set.all():
        if field.type == VLE.models.Field.NO_SUBMISSION:
            continue

        test.factory.Content(field=field, entry=self, data__from_file=kwargs.get('from_file', ''))


class BaseEntryFactory(factory.django.DjangoModelFactory):
    """
    Do not initialize on its own.
    """
    class Meta:
        model = 'VLE.Entry'

    last_edited = factory.LazyFunction(timezone.now)
    title = None
    template = None

    @factory.post_generation
    def categories(self, create, extracted):
        if not create:
            return

        if isinstance(extracted, int):
            categories = [test.factory.Category(assignment=self.node.journal.assignment) for _ in range(extracted)]
            self.categories.set(categories)

        elif extracted and isinstance(extracted, list) and isinstance(extracted[0], VLE.models.Category):
            self.categories.set(extracted)


class UnlimitedEntryFactory(BaseEntryFactory):
    """
    Creates an 'unlimited' template entry.

    Default Yields:
        - Entry: An Entry attached to a Node.
        - Author: If no author is provided it will select the first author of the journal the entry is attached to.
        - Template: If no template is provided it will randomly select an available tempalte from the assignment's
        format. If the format holds no template a TextTemplate is generated.
        - Grade: Ungraded by default.
        - Content: Will generate content for all allowed fields of its template.
        - Node: A node attached to a journal of type Entry, chains via journal to an assignment and a course.
    """
    node = factory.SubFactory(
        'test.factory.node.NodeFactory',
        type=VLE.models.Node.ENTRY,
        journal__entries__n=0,
        entry=None,
    )

    @factory.post_generation
    def fix_node(self, create, extracted, **kwargs):
        if not create:
            return

        self.node.entry = self
        self.node.save()

    @factory.post_generation
    def author(self, create, extracted, **kwargs):
        _author(self, create, extracted, **kwargs)

    @factory.post_generation
    def template(self, create, extracted, **kwargs):
        _set_template(self, create, extracted, **kwargs)

    @factory.post_generation
    def grade(self, create, extracted, **kwargs):
        _grade(self, create, extracted, **kwargs)

    @factory.post_generation
    def gen_content(self, create, extracted, **kwargs):
        _gen_content(self, create, extracted, **kwargs)


class PresetEntryFactory(UnlimitedEntryFactory):
    """
    Creates a Deadline entry for a ENTRYDEADLINE preset node.

    Yields:
        - Equal fields as an UnlimitedEntry
    """
    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'node' not in kwargs and not isinstance(kwargs['node'], VLE.models.Node):
            raise VLEProgrammingError('Preset entry requires a node during initialization')

        node = kwargs['node']

        if node.type != VLE.models.Node.ENTRYDEADLINE:
            raise VLEProgrammingError('Preset entry requires a node of type entry deadline during initialization')

        if not node.preset.forced_template:
            raise VLEProgrammingError('Preset entry node\'s preset is not linked to a forced template')

        return kwargs

    @factory.post_generation
    def save_and_validate(self, create, extracted):
        if self.node is None:
            raise ValidationError('Dangling preset entry (node = None).')
        if self.template.pk != self.node.preset.forced_template.pk:
            raise ValidationError('Deadline Entry template does not match its PresetNode\'s template.')
