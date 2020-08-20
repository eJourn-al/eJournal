import test.factory

import factory

import VLE.models


class BaseJournalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Journal'

    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')


class JournalFactory(BaseJournalFactory):
    '''
    Generates a Journal

    Default yields:
        - AssignmentParticipation: AP for the attached assignment, will generate a user unless specified as
        factory.Journal(ap__user=user).
        - Assignment: generates a new one unless set.
        - Entry: will generate one unlimited entry by default, can be changed via entries__n=int
    '''
    ap = factory.RelatedFactory(
        'test.factory.participation.AssignmentParticipationFactory',
        factory_related_name='journal',
        assignment=factory.SelfAttribute('..assignment')
    )

    # NOTE: Can become be a RelatedFactoryList once size is passable as an initialisation arg
    # entries = factory.RelatedFactoryList(
    #     'test.factory.entry.UnlimitedEntryFactory',
    #     factory_related_name='node__journal',
    #     node__journal=factory.SelfAttribute('..'),
    #     size=1
    # )

    @factory.post_generation
    def entries(self, create, extracted, **kwargs):
        if not create:
            return

        for _ in range(kwargs['n'] if 'n' in kwargs else 1):
            test.factory.UnlimitedEntry(node__journal=self)


class LtiJournalFactory(BaseJournalFactory):
    '''
    Equal to a JournalFactory but generates an Lti assignment and AP.
    '''
    assignment = factory.SubFactory('test.factory.assignment.LtiAssignmentFactory')

    ap = factory.RelatedFactory(
        'test.factory.participation.AssignmentParticipationFactory',
        factory_related_name='journal',
        assignment=factory.SelfAttribute('..assignment'),
        lti=True
    )

    @factory.post_generation
    def entries(self, create, extracted, **kwargs):
        if not create:
            return

        for _ in range(kwargs['n'] if 'n' in kwargs else 1):
            test.factory.UnlimitedEntry(node__journal=self)


class GroupJournalFactory(BaseJournalFactory):
    '''
    Generates a group assignment, still defaults to a single user. Any additional users can be set via add_users.
    Note that factory.GroupJournal(add_users=[user1, users2]) will generate three users as the default AP has
    not been overwritten. This was a convenience trade off, as factory.GroupJournal(add_users=[user1, users2], ap=None)
    would no longer generate an assignment.
    '''
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory', group_assignment=True)
    author_limit = 3

    ap = factory.RelatedFactory(
        'test.factory.participation.AssignmentParticipationFactory',
        factory_related_name='journal',
        assignment=factory.SelfAttribute('..assignment')
    )

    @factory.post_generation
    def entries(self, create, extracted, **kwargs):
        if not create:
            return

        for _ in range(kwargs['n'] if 'n' in kwargs else 1):
            test.factory.UnlimitedEntry(node__journal=self)

    @factory.post_generation
    def add_users(self, create, extracted):
        if not create:
            return

        if extracted:
            for user in extracted:
                test.factory.AssignmentParticipation(
                    journal=self, assignment=self.assignment, user=user)


class JournalImportRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.JournalImportRequest'

    author = factory.SubFactory('test.factory.user.UserFactory')

    @factory.post_generation
    def source(self, create, extracted, **kwargs):
        test.factory.rel_factory(self, create, extracted, 'source', VLE.models.Journal, JournalFactory,
                                 cond_kwargs={'ap__user': self.author}, **kwargs)

    @factory.post_generation
    def target(self, create, extracted, **kwargs):
        test.factory.rel_factory(self, create, extracted, 'target', VLE.models.Journal, JournalFactory,
                                 cond_kwargs={'ap__user': self.author}, **kwargs)
