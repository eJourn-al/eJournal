import os
import test.factory

import factory
from VLE.models import Field, Journal


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
    in_rich_text = True
    comment = factory.SubFactory('test.factory.comment.StudentCommentFactory')
    author = factory.SelfAttribute('comment.author')
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))

    @factory.post_generation
    def journal(self, create, extracted):
        test.factory.rel_factory(self, create, extracted, 'journal', Journal, default=self.comment.entry.node.journal)

    @factory.post_generation
    def set_fc_text(self, create, extracted):
        if not create:
            return

        self.comment.text += '<img src="{}"/>'.format(self.download_url(access_id=self.access_id))
        self.comment.save()


class AttachedCommentFileContextFactory(RichTextCommentFileContextFactory):
    in_rich_text = False
    # Order matters, cannot inherit the FileContextFactory file property, the author would be set after.
    file = factory.django.FileField()

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
    author = factory.SelfAttribute('content.entry.author')

    @factory.post_generation
    def journal(self, create, extracted):
        test.factory.rel_factory(self, create, extracted, 'journal', Journal, default=self.content.entry.node.journal)

    @factory.post_generation
    def update_content_data(self, create, extracted):
        if not create:
            return

        self.content.data = str(self.pk)
        self.content.save()


class RichTextContentFileContextFactory(FileContentFileContextFactory):
    in_rich_text = True
    content = factory.SubFactory('test.factory.content.ContentFactory', field__type=Field.RICH_TEXT)
    # Order is relevant, need content to be set first (since content is overwritten parent author would run first
    author = factory.SelfAttribute('content.entry.author')
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))

    @factory.post_generation
    def update_content_data(self, create, extracted):
        if not create:
            return

        img_link = '<img src="{}"/>'.format(self.download_url(access_id=self.access_id))
        self.content.data = self.content.data + img_link if self.content.data else img_link
        self.content.save()
