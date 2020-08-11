import factory
import VLE.models


class NodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Node'

    journal = factory.SubFactory('test.factory.journal.JournalFactory')


# TODO JIR: Test node uses..
class EntryNodeFactory(NodeFactory):
    type = VLE.models.Node.ENTRY
    entry = factory.RelatedFactory(
        'test.factory.entry.EntryFactory',
        factory_related_name='node',
    )


# TODO JIR: What is the 'preset' relation from a Node?
class EntryDeadlineNodeFactory(EntryNodeFactory):
    type = VLE.models.Node.ENTRYDEADLINE
    # TODO JIR: confusing duplicate factory name
    preset = factory.SubFactory('test.factory.presetnode.EntrydeadlineNodeFactory')


class ProgressNodeFactory(NodeFactory):
    type = VLE.models.Node.PROGRESS
