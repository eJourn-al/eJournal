# from VLE.models import FileContext
from test.factory.file_context import AttachedCommentFileContextFactory, RichTextCommentFileContextFactory

import factory


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.Comment'

    class Params:
        n_files = 1

    entry = factory.SubFactory('test.factory.entry.EntryFactory')
    text = 'test-comment'

    # NOTE: Await this issue to resolve dynamic size problems: https://github.com/FactoryBoy/factory_boy/issues/767
    files = factory.Maybe(
        'gen_att_files',
        yes_declaration=factory.RelatedFactoryList(
            'test.factory.file_context.AttachedCommentFileContextFactory',
            factory_related_name='comment',
            size=factory.SelfAttribute('n_files')
        ),
        no_declaration=None,
    )

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

    @factory.post_generation
    def author(self, create, extracted):
        if not create:
            return

        if extracted:
            self.author = extracted
        else:
            if self.entry.author:
                self.author = self.entry.author
            else:
                self.author = self.entry.node.journal.authors.first().user

        self.save()


class TeacherCommentFactory(CommentFactory):
    published = False

    @factory.post_generation
    def author(self, create, extracted):
        if not create:
            return

        if extracted:
            self.author = extracted
        else:
            self.author = self.entry.node.journal.assignment.courses.first().author

        self.save()
