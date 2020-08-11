import test.factory.participation

import factory

from VLE.models import AssignmentParticipation


class JournalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Journal'

    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')

    # TODO JIR: Why does the assignment not get set correctly?
    # ap = factory.RelatedFactory(
    #     'test.factory.participation.AssignmentParticipationFactory',
    #     factory_related_name='journal',
    #     assignment=assignment
    # )

    # node = factory.RelatedFactory(
    #     'test.factory.node.EntryNodeFactory',
    #     factory_related_name='journal',
    # )

    @factory.post_generation
    def add_user(self, create, extracted):
        if not create:
            return

        if not AssignmentParticipation.objects.filter(journal=self).exists():
            if extracted:
                ap = test.factory.participation.AssignmentParticipationFactory(
                    journal=self, assignment=self.assignment, user=extracted)
            else:
                ap = test.factory.participation.AssignmentParticipationFactory(
                    journal=self, assignment=self.assignment)
            self.add_author(ap)

        # TODO JIR: Remove above and use related factory
        # if extracted:
        #     if not AssignmentParticipation.objects.filter(journal=self, user=extracted).exists():
        #         test.factory.participation.AssignmentParticipationFactory(
        #             journal=self, assignment=self.assignment, user=extracted)

    # TODO JIR: Hopefully not required.
    # @factory.post_generation
    # def update_ap_assignment(self, create, extracted):
    #     AssignmentParticipation.objects.filter(journal=self, assignment=None).update(assignment=self.assignment)


class LtiJournalFactory(JournalFactory):
    assignment = factory.SubFactory('test.factory.assignment.LtiAssignmentFactory')

    @factory.post_generation
    def add_user(self, create, extracted):
        if not create:
            return

        if not AssignmentParticipation.objects.filter(journal=self).exists():
            if extracted:
                ap = test.factory.participation.LtiAssignmentParticipationFactory(
                    journal=self, assignment=self.assignment, user=extracted)
            else:
                ap = test.factory.participation.LtiAssignmentParticipationFactory(
                    journal=self, assignment=self.assignment)
            self.add_author(ap)


class GroupJournalFactory(JournalFactory):
    assignment = factory.SubFactory('test.factory.assignment.GroupAssignmentFactory')
    author_limit = 3


class PopulatedJournalFactory(JournalFactory):
    node = factory.RelatedFactory(
        'test.factory.node.EntryNodeFactory',
        factory_related_name='journal',
    )

    # unlimited_entry = factory.RelatedFactory(
    #     'test.factory.entry.EntryFactory',
    #     factory_related_name='node__journal',
    #     node__type=Node.ENTRY
    # )

    # preset_entry = factory.RelatedFactory(
    #     'test.factory.entry.EntryFactory',
    #     factory_related_name='node__journal',
    # )


class JournalImportRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.JournalImportRequest'

    author = factory.SubFactory('test.factory.user.UserFactory')
    source = factory.LazyAttribute(lambda self: PopulatedJournalFactory(add_user=self.author))
    target = factory.LazyAttribute(lambda self: JournalFactory(add_user=self.author))
