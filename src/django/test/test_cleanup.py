import test.factory as factory

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

import VLE.tasks.beats.cleanup as cleanup
from VLE.models import Field, FileContext, PresetNode


class CleanupTest(TestCase):
    def test_remove_temp_files(self, cleanup_function=cleanup.remove_temp_files):
        def update_fc_creation_date(fc, date):
            """Auto_now_add ignores passed values on creation.."""
            fc.creation_date = date
            fc.save()

        non_temp_fc = factory.FileContext(is_temp=False)
        temp_fc_new = factory.FileContext(is_temp=True)
        temp_fc_6_hours = factory.FileContext(is_temp=True)
        update_fc_creation_date(temp_fc_6_hours, timezone.now() - relativedelta(hours=6))
        temp_fc_1_day = factory.FileContext(is_temp=True)
        update_fc_creation_date(temp_fc_1_day, timezone.now() - settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'])

        cleanup_function()

        assert FileContext.objects.filter(pk__in=[non_temp_fc.pk, temp_fc_new.pk, temp_fc_6_hours.pk]).count() == 3, \
            'Only temp files older than a day are deleted'
        assert not FileContext.objects.filter(pk=temp_fc_1_day.pk).exists(), 'Temp files older than a day are deleted'

    def test_remove_unused_content_files(self, cleanup_function=cleanup.remove_unused_content_files):
        rt_content = factory.Content(field__type=Field.RICH_TEXT)
        rt_fc = FileContext.objects.get(content=rt_content)
        file_content = factory.Content(field__type=Field.FILE)
        file_fc = FileContext.objects.get(content=file_content)
        cleanup_function()
        assert FileContext.objects.filter(pk__in=[rt_fc.pk, file_fc.pk]).count() == 2, 'Used fcs are not removed'

        factory.FileContentFileContext(journal=rt_content.entry.node.journal, content=rt_content)
        # RichTextContentFileContext will append to the existing content so first clear the content data
        file_content.data = ''
        file_content.save()
        factory.RichTextContentFileContext(journal=rt_content.entry.node.journal, content=rt_content)
        cleanup_function()
        assert not FileContext.objects.filter(pk__in=[rt_fc.pk, file_fc.pk]).exists(), \
            'Overwritten RT and FILE content file contexts are cleaned'

    def test_remove_unused_comment_files(self, cleanup_function=cleanup.remove_unused_comment_files):
        comment = factory.StudentComment(n_rt_files=1, n_att_files=1)
        entry = comment.entry
        att_fc = comment.files.first()
        rt_fc = FileContext.objects.get(comment=comment, comment_files__isnull=True)
        cleanup_function()
        assert FileContext.objects.filter(pk__in=[att_fc.pk, rt_fc.pk]).count() == 2, \
            'Correct comment FCs are not removed'

        comment.text = ''
        comment.save()
        cleanup_function()
        assert FileContext.objects.filter(pk=att_fc.pk).exists(), 'Attached comment FC should be unaffected'
        assert not FileContext.objects.filter(pk=rt_fc.pk).exists(), 'No longer referenced RT FC should be removed'

        comment = factory.StudentComment(n_rt_files=1, n_att_files=1, entry=entry)
        att_fc = comment.files.first()
        rt_fc = FileContext.objects.get(comment=comment, comment_files__isnull=True)
        comment.files.set(FileContext.objects.none())
        cleanup_function()
        assert not FileContext.objects.filter(pk=att_fc.pk).exists(), 'Attached comment FC should be removed'
        assert FileContext.objects.filter(pk=rt_fc.pk).exists(), 'Still referenced RT FC should not be removed'

        comment = factory.StudentComment(n_rt_files=1, n_att_files=1, entry=entry)
        att_fc = comment.files.first()
        rt_fc = FileContext.objects.get(comment=comment, comment_files__isnull=True)
        comment.text = ''
        comment.files.set(FileContext.objects.none())
        comment.save()
        cleanup_function()
        assert not FileContext.objects.filter(pk__in=[att_fc.pk, rt_fc.pk]).exists(), \
            'No longer referenced comment FCs are removed'

    def test_remove_unused_journal_files(self, cleanup_function=cleanup.remove_unused_journal_files):
        journal = factory.Journal()
        g_journal_cover_image = factory.JournalFileContext(journal=journal, author=journal.authors.first().user)
        cleanup_function()
        assert FileContext.objects.filter(pk=g_journal_cover_image.pk).exists(), 'Correct journal files should remain.'

        new_g_journal_cover_image = factory.JournalFileContext(journal=journal, author=journal.authors.first().user)
        cleanup_function()
        assert not FileContext.objects.filter(pk=g_journal_cover_image.pk).exists(), \
            'Replaced journal files should be cleaned'
        assert FileContext.objects.filter(pk=new_g_journal_cover_image.pk).exists(), \
            'The replacing journal file should remain'

    def test_remove_unused_profile_pictures(self, cleanup_function=cleanup.remove_unused_profile_pictures):
        fc = factory.ProfilePictureFileContext()
        cleanup_function()
        assert FileContext.objects.filter(pk=fc.pk).exists(), 'Correct profile pictures should remain'

        new_fc = factory.ProfilePictureFileContext(author=fc.author)
        cleanup_function()
        assert FileContext.objects.filter(pk=new_fc.pk).exists(), 'Correct profile pictures should remain'
        assert not FileContext.objects.filter(pk=fc.pk).exists(), 'Replaced profile picture should be cleaned'

    def test_remove_unused_assignment_files(self, cleanup_function=cleanup.remove_unused_assignment_files):
        a_description_fc = factory.RichTextAssignmentDescriptionFileContext()
        assignment = a_description_fc.assignment
        f_description_fc = factory.RichTextFieldDescriptionFileContext(assignment=assignment)
        progress_description_fc = factory.RichTextPresetNodeDescriptionFileContext(assignment=assignment)
        cleanup_function()
        assert FileContext.objects.filter(
            pk__in=[a_description_fc.pk, f_description_fc.pk, progress_description_fc.pk]).count() == 3, \
            'All correct assignment specific FCs should remain'

        assignment.description = ''
        assignment.save()
        Field.objects.filter(
            type=Field.NO_SUBMISSION, description__contains=f_description_fc.access_id).update(description='')
        PresetNode.objects.filter(
            format=assignment.format, description__contains=progress_description_fc.access_id).update(description='')
        cleanup_function()
        assert not FileContext.objects.filter(
            pk__in=[a_description_fc.pk, f_description_fc.pk, progress_description_fc.pk]).exists(), \
            'Once the respective descriptions no longer refer to the FCs, they should be cleaned'

    def test_remove_unused_files(self):
        self.test_remove_unused_content_files(cleanup_function=cleanup.remove_unused_files)
        self.test_remove_unused_comment_files(cleanup_function=cleanup.remove_unused_files)
        self.test_remove_unused_journal_files(cleanup_function=cleanup.remove_unused_files)
        self.test_remove_unused_profile_pictures(cleanup_function=cleanup.remove_unused_files)
        self.test_remove_unused_assignment_files(cleanup_function=cleanup.remove_unused_files)
