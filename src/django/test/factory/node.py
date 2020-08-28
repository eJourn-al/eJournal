import factory


class NodeFactory(factory.django.DjangoModelFactory):
    """
    NodeFactory should never be directly initiated, only via Entry or PresetNode factories
    """
    class Meta:
        model = 'VLE.Node'

    journal = factory.SubFactory('test.factory.journal.JournalFactory')
