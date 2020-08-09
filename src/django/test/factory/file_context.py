import os

import factory


class FileContextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.FileContext'

    file = factory.django.FileField()
    author = factory.SubFactory('test.factory.user.UserFactory')
    is_temp = False

    @factory.post_generation
    def file_name(self, create, extracted):
        if not create:
            return

        if not extracted:
            self.file_name = os.path.basename(self.file.name)
            self.save()


class RichTextCommentFileContextFactory(FileContextFactory):
    '''
    We enforce the save order for author on the FC model level, otherwise 'add_author' could be 'author' allowing
    author to be passed as the expected argument.
    '''
    comment = factory.SubFactory('test.factory.comment.StudentCommentFactory')
    in_rich_text = True

    @factory.post_generation
    def set_author(self, create, extracted):
        if not create:
            return

        if extracted:
            self.author = extracted
        else:
            self.author = self.comment.entry.node.journal.authors.first().user

        self.save()

    @factory.post_generation
    def journal(self, create, extracted):
        if not create:
            return

        if extracted:
            self.journal = extracted
        else:
            self.journal = self.comment.entry.node.journal

        self.save()

    @factory.post_generation
    def set_fc_text(self, create, extracted):
        if not create:
            return

        self.comment.text += '<img src="{}"/>'.format(self.download_url(access_id=self.access_id))
        self.comment.save()


class AttachedCommentFileContextFactory(RichTextCommentFileContextFactory):
    in_rich_text = False

    @factory.post_generation
    def set_fc_text(self, create, extracted):
        pass

    @factory.post_generation
    def attach_file_to_comment(self, create, extracted):
        if not create:
            return

        self.comment.files.add(self)
        self.comment.save()
