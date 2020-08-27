import test.factory

import factory
import VLE.models


def _ap(self, create, extracted, lti=False, **kwargs):
    if not create or extracted is False:
        return

    if isinstance(extracted, VLE.models.AssignmentParticipation):
        extracted.journal = self
        extracted.save()
    # An assignment will create an AP for all of its courses users so we need to filter if one already exists.
    elif 'user' in kwargs and VLE.models.AssignmentParticipation.objects.filter(
            user=kwargs['user'], assignment=self.assignment).exists():
        ap = VLE.models.AssignmentParticipation.objects.get(user=kwargs['user'], assignment=self.assignment)
        ap.journal = self
        ap.save()
    else:
        test.factory.AssignmentParticipation(**{**kwargs, 'journal': self, 'assignment': self.assignment, 'lti': lti})


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

    @factory.post_generation
    def ap(self, create, extracted, **kwargs):
        _ap(self, create, extracted, lti=False, **kwargs)

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

    @factory.post_generation
    def ap(self, create, extracted, **kwargs):
        _ap(self, create, extracted, lti=True, **kwargs)

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
    not been overwritten. This was a convenience trade off, as factory.GroupJournal(add_users=[user1, users2], ap=False)
    would no longer generate an assignment.
    '''
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory', group_assignment=True)
    author_limit = 3

    @factory.post_generation
    def ap(self, create, extracted, **kwargs):
        _ap(self, create, extracted, lti=False, **kwargs)

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
                ap = VLE.models.AssignmentParticipation.objects.filter(assignment=self.assignment, user=user)
                if ap.exists():
                    ap = ap.first()
                    ap.journal = self
                    ap.save()
                else:
                    test.factory.AssignmentParticipation(journal=self, assignment=self.assignment, user=user)


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
