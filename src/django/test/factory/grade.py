from datetime import date

import factory


class GradeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Grade'

    entry = factory.SubFactory('test.factory.entry.EntryFactory')
    grade = 1
    published = True
    creation_date = date(2019, 1, 1)
    author = factory.LazyAttribute(
        lambda self: self.entry.node.journal.assignment.courses.first().author
    )

    @factory.post_generation
    def add_author(self, create, extracted):
        if not create:
            return

        self.entry.grade = self
        self.entry.save()
