import test.factory
from datetime import date

import factory

import VLE.models


class GradeFactory(factory.django.DjangoModelFactory):
    """
    Generates a grade instance for an entry.

    Default yields:
        - UnlimitedEntry
        - Author: Defaults to the assignment author.
    """
    class Meta:
        model = 'VLE.Grade'

    entry = factory.SubFactory('test.factory.entry.UnlimitedEntryFactory')
    grade = 1
    published = True
    creation_date = date(2019, 1, 1)

    @factory.post_generation
    def author(self, create, extracted, **kwargs):
        test.factory.rel_factory(
            self, create, extracted, 'author', VLE.models.User, default=self.entry.node.journal.assignment.author)

    @factory.post_generation
    def link_grade_to_entry(self, create, extracted, **kwargs):
        if not create:
            return

        self.entry.grade = self
        self.entry.save()
