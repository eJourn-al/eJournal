import factory


class NodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Node'

    journal = factory.SubFactory('test.factory.journal.JournalFactory')
    preset = factory.SubFactory(
        'test.factory.presetnode.ProgressNodeFactory',
        format=factory.SelfAttribute('..journal.assignment.format'))

    @factory.post_generation
    def add_to_node_set(self, create, extracted):
        if not create:
            return
        self.journal.node_set.add(self)
        self.journal.save()
