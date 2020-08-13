import os
import random

import factory

from VLE.models import Field


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
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))
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


class FileContentFileContextFactory(FileContextFactory):
    in_rich_text = False
    content = factory.SubFactory('test.factory.content.ContentFactory', field__type=Field.FILE)

    @factory.post_generation
    def set_author(self, create, extracted):
        if not create:
            return

        if extracted:
            self.author = extracted
        else:
            self.author = self.content.entry.node.journal.authors.first().user

        self.save()

    @factory.post_generation
    def journal(self, create, extracted):
        if not create:
            return

        if extracted:
            self.journal = extracted
        else:
            self.journal = self.content.entry.node.journal

        self.save()

    @factory.post_generation
    def update_content_data(self, create, extracted):
        if not create:
            return

        if extracted:
            self.content.data = extracted
        else:
            self.content.data = str(self.pk)

        self.content.save()


class RichTextContentFileContextFactory(FileContentFileContextFactory):
    in_rich_text = True
    content = factory.SubFactory('test.factory.content.ContentFactory', field__type=Field.RICH_TEXT)
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))

    @factory.post_generation
    def update_content_data(self, create, extracted):
        if not create:
            return

        if extracted:
            self.content.data = extracted
        else:
            img_link = '<img src="{}"/>'.format(self.download_url(access_id=self.access_id))
            self.content.data = self.content.data + img_link if self.content.data else img_link

        self.content.save()
