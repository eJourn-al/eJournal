import os
import test.factory

import factory
from django.core.exceptions import ValidationError

from VLE.models import Field, Journal, PresetNode


def _fc_to_rt_img_element(fc):
    return f'<img src="{fc.download_url(access_id=fc.access_id)}"/>'


def _none_to_str(el):
    return el if el else ''


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


class TempRichTextFileContextFactory(FileContextFactory):
    in_rich_text = True
    is_temp = True
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))


class TempFileContextFactory(FileContextFactory):
    is_temp = True


class RichTextFileContextFactory(FileContextFactory):
    in_rich_text = True
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))


class RichTextCommentFileContextFactory(RichTextFileContextFactory):
    """
    Generates a FC which is embedded in the rich text of a comment

    An embedded download image link of the generated file is appended to the comment's text

    Default Yields:
        - Comment: student comment
        - Author: equal to the author of the student comment itself
        - File: By default an image type file.
        - Journal: By default attached to the journal of the comment.
    """
    comment = factory.SubFactory('test.factory.comment.StudentCommentFactory')
    author = factory.SelfAttribute('comment.author')

    @factory.post_generation
    def journal(self, create, extracted):
        test.factory.rel_factory(self, create, extracted, 'journal', Journal, default=self.comment.entry.node.journal)

    @factory.post_generation
    def set_fc_text(self, create, extracted):
        if not create:
            return

        self.comment.text = _none_to_str(self.comment.text) + _fc_to_rt_img_element(self)
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


class RichTextContentFileContextFactory(RichTextFileContextFactory):
    """
    Generates a FC embedded to the content of rich text field.

    Will appended a html img tag containing the download link of the FC to the data of the attached content.

    Additional Default Yields:
        - Content: VLE.models.Content whose field is of type RICH_TEXT
        - File: Image category
    """
    content = factory.SubFactory('test.factory.content.ContentFactory', field__type=Field.RICH_TEXT)
    # Order is relevant, need content to be set first (since content is overwritten parent author would run first
    author = factory.SelfAttribute('content.entry.author')

    @factory.post_generation
    def update_content_data(self, create, extracted):
        if not create:
            return

        self.content.data = _none_to_str(self.content.data) + _fc_to_rt_img_element(self)
        self.content.save()


class JournalFileContextFactory(FileContextFactory):
    """
    Generates a FC attached to a journal (journal cover image).

    Additional Default yields:
        - Author: VLE.models.User who is the author of the FileContext, defautls to first journal author.
        - Journal: VLE.models.Journal.
    """
    journal = factory.SubFactory('test.factory.journal.GroupJournalFactory')
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))

    @factory.post_generation
    def update_journal_stored_image(self, create, extracted):
        if not create:
            return

        self.journal.stored_image = self.download_url(access_id=True)
        self.journal.save()

    @factory.post_generation
    def validate(self, create, extracted):
        if not create:
            return

        # Cover image not set by author of journal or supervisor of group assignment.
        if not self.journal.authors.filter(user=self.author).exists() \
                and not self.author.participation_set.filter(
                    course__in=self.journal.assignment.courses, can_manage_journals=True):
            raise ValidationError('Journal FileContext created by an author not part of its journal or supervisor.')


class ProfilePictureFileContextFactory(FileContextFactory):
    """
    Generates a profile picture for a user.

    Additional Default yields:
        - Author: VLE.models.User, user who the profile picture belong to.
    """
    file = factory.django.FileField(filename=factory.Faker('file_name', category='image'))

    @factory.post_generation
    def update_profile_picture_download_link(self, create, extracted):
        if not create:
            return

        self.author.profile_picture = self.download_url(access_id=True)
        self.author.save()


class RichTextAssignmentDescriptionFileContextFactory(RichTextFileContextFactory):
    """
    Generates a RT file embedded in the description of an assignment.

    Additional Default yields:
        - Author: VLE.models.User, user who created the FileContext, defaults to assignment author.
        - Assignment: VLE.models.Assignment, assignment where the FC is embedded in the RT.
    """
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    author = factory.SelfAttribute('assignment.author')

    @factory.post_generation
    def update_assignment_description(self, create, extracted):
        if not create:
            return

        self.assignment.description = _none_to_str(self.assignment.description) + _fc_to_rt_img_element(self)
        self.assignment.save()


class RichTextFieldDescriptionFileContextFactory(RichTextFileContextFactory):
    """
    Generates a RT file embedded in the description of an NO_SUBMISSION field.

    Additional Default yields:
        - Author: VLE.models.User, user who created the FileContext, defaults to assignment author.
        - Field: VLE.models.Field, NO_SUBMISSION type field and the upwards chain to an assignment.
    """
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    author = factory.SelfAttribute('assignment.author')

    @factory.post_generation
    def field(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, Field):
            extracted.description = _none_to_str(extracted.description) + _fc_to_rt_img_element(self)
            extracted.save()
        else:
            field = test.factory.Field(**{
                'template': self.assignment.format.template_set.first(),
                **kwargs,
                'type': Field.NO_SUBMISSION,
            })
            field.description = _none_to_str(field.description) + _fc_to_rt_img_element(self)
            field.save()


class RichTextPresetNodeDescriptionFileContextFactory(RichTextFileContextFactory):
    """
    Generates a RT file embedded in the description of a presetnode, defaults to PROGRESS.

    Additional Default yields:
        - Assignment: VLE.models.Assignment, assignment which the FC is linked to.
        - Author: VLE.models.User, user who created the FileContext, defaults to assignment author.
        - PresetNode: VLE.models.PresetNode, presetnode of which the RT description contains the FC.
    """
    assignment = factory.SubFactory('test.factory.assignment.AssignmentFactory')
    author = factory.SelfAttribute('assignment.author')

    @factory.post_generation
    def preset(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, PresetNode):
            if extracted.format.assignment != self.assignment:
                raise ValidationError('Provided presetnode is not part of the set assignment.')

            extracted.description = _none_to_str(extracted.description) + _fc_to_rt_img_element(self)
            extracted.save()
        else:
            preset = test.factory.ProgressPresetNode(**{
                'forced_template': self.assignment.format.template_set.first(),
                **kwargs,
                'format': self.assignment.format,
            })
            preset.description = _none_to_str(preset.description) + _fc_to_rt_img_element(self)
            preset.save()
