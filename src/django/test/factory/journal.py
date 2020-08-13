import factory

import test.factory
from django.core.exceptions import ValidationError


class BaseJournalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Journal'

    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')


class JournalFactory(BaseJournalFactory):
    ap = factory.RelatedFactory(
        'test.factory.participation.AssignmentParticipationFactory',
        factory_related_name='journal',
        assignment=factory.SelfAttribute('..assignment')
    )


class LtiJournalFactory(BaseJournalFactory):
    assignment = factory.SubFactory('test.factory.assignment.LtiAssignmentFactory')

    ap = factory.RelatedFactory(
        'test.factory.participation.LtiAssignmentParticipationFactory',
        factory_related_name='journal',
        assignment=factory.SelfAttribute('..assignment')
    )


class GroupJournalFactory(BaseJournalFactory):
    assignment = factory.SubFactory('test.factory.assignment.GroupAssignmentFactory')
    author_limit = 3

    @factory.post_generation
    def users(self, create, extracted):
        if not create:
            return

        if extracted:
            for user in extracted:
                # QUESTION: Something to move to an actual validator?
                if self.authors.count() >= self.author_limit:
                    raise ValidationError('Journal users exceed author limit.')
                test.factory.participation.AssignmentParticipationFactory(
                    journal=self, assignment=self.assignment, user=user)
        else:
            test.factory.participation.AssignmentParticipationFactory(journal=self, assignment=self.assignment)


class PopulatedJournalFactory(JournalFactory):
    pass


class JournalImportRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.JournalImportRequest'

    author = factory.SubFactory('test.factory.user.UserFactory')
    source = factory.LazyAttribute(lambda self: JournalFactory(ap__user=self.author))
    target = factory.LazyAttribute(lambda self: JournalFactory(ap__user=self.author))
