import factory


class StudentCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Comment'

    entry = factory.SubFactory('test.factory.entry.EntryFactory')
    text = 'test-comment'
    published = True
    author = factory.LazyAttribute(
        lambda self: self.entry.node.journal.authors.first().user
    )


class TeacherCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Comment'

    entry = factory.SubFactory('test.factory.entry.EntryFactory')
    text = 'test-comment'
    published = False
    author = factory.LazyAttribute(
        lambda self: self.entry.node.journal.assignment.courses.first().author
    )
