import os
import test.factory

import factory
from django.core.exceptions import ValidationError

from VLE.models import Field, Journal


class FileContextFactory(factory.django.DjangoModelFactory):
    """
    An instance of a VLE.models.FileContext.

    The file_name attribute will default to the fc.file.file basename.

    Default yields:
        - File: A file with a random name (not just in memory but also on disk)
        - Author: a student user
    """
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

    @factory.post_generation
    def validate(self, create, extracted):
        if not create:
            return

        if not self.file or not os.path.exists(self.file.path):
            raise ValidationError('FC created without underlying file.')


class RichTextCommentFileContextFactory(FileContextFactory):
    """
    Generates a FC which is embedded in the rich text of a comment

    An embedded download image link of the generated file is appended to the comment's text

    Default Yields:
        - Comment: student comment
        - Author: equal to the author of the student comment itself
        - File: By default an image type file.
        - Journal: By default attached to the journal of the comment.
    """
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
    """
    Yields a FC which is attached to a student comment by default.

    Equal yields to RichText comment. However, the file can be of any type.
    """
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
    """
    Generates a FC attached to the content of a FILE field.

    Will set the data of the content its attached to to its own pk.

    Additional Default yields:
        - Content: VLE.models.Content whose field of is type FILE
        - Author: VLE.models.User who is equal to the author of content's entry by default.
        - Journal: VLE.models.Journal, equal by default of the content's entry's journal.
    """
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
    """
    Generates a FC embedded to the content of rich text field.

    Will appended a html img tag containing the download link of the FC to the data of the attached content.

    Additional Default Yields:
        - Content: VLE.models.Content whose field is of type RICH_TEXT
        - File: Image category
    """
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
