# from VLE.models import FileContext
from test.factory.file_context import AttachedCommentFileContextFactory, RichTextCommentFileContextFactory

import factory


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Comment'

    entry = factory.SubFactory('test.factory.entry.UnlimitedEntryFactory')
    author = factory.SelfAttribute('entry.author')
    text = 'test-comment'

    @factory.post_generation
    def n_att_files(self, create, extracted):
        if not create:
            return

        if extracted and isinstance(extracted, int):
            for _ in range(extracted):
                AttachedCommentFileContextFactory(comment=self)

    @factory.post_generation
    def n_rt_files(self, create, extracted):
        if not create:
            return

        if extracted and isinstance(extracted, int):
            for _ in range(extracted):
                RichTextCommentFileContextFactory(comment=self)


class StudentCommentFactory(CommentFactory):
    published = True


class TeacherCommentFactory(CommentFactory):
    published = False
    author = factory.SelfAttribute('entry.node.journal.assignment.author')
