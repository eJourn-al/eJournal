import test.factory as factory
from test.utils import api
from test.utils.generic_utils import equal_models

from django.test import TestCase

import VLE.utils.import_utils as import_utils
from VLE.models import (Assignment, AssignmentParticipation, Comment, Content, Course, Entry, Field, FileContext,
                        Journal, JournalImportRequest, Node, PresetNode, Template)
from VLE.utils.error_handling import VLEProgrammingError


class ImportTest(TestCase):
    def test_comment_import(self):
        source_comment = factory.StudentComment(n_att_files=1)
        source_comment_pk = source_comment.pk

        count = Comment.objects.filter(entry=source_comment.entry).count()
        imported_comment = import_utils.import_comment(source_comment, source_comment.entry)
        source_comment = Comment.objects.get(pk=source_comment_pk)

        assert Comment.objects.filter(entry=source_comment.entry).count() == count + 1, \
            'One additional comment is created'
        assert source_comment.pk != imported_comment.pk, 'The imported comment instance differs from the original'
        assert equal_models(
            source_comment, imported_comment, ignore=['last_edited', 'creation_date', 'update_date', 'files', 'id']), \
            'The imported model is mostly equal to the source model'
        assert FileContext.objects.filter(comment=imported_comment).count() == 1, \
            'FCs are copied alongside the comment import.'
        assert imported_comment.files.count() == 1, 'One attached file context is created'

        source_comment = factory.StudentComment(n_rt_files=1)
        source_comment_pk = source_comment.pk
        imported_comment = import_utils.import_comment(source_comment, source_comment.entry)
        source_comment = Comment.objects.get(pk=source_comment_pk)

        imported_comment_rt_fc = FileContext.objects.filter(comment=imported_comment, in_rich_text=True)
        source_comment_rt_fc = FileContext.objects.filter(comment=source_comment, in_rich_text=True).first()
        assert imported_comment_rt_fc.count() == 1, 'One in richtext file context is created'
        imported_comment_rt_fc = imported_comment_rt_fc.first()
        assert source_comment.text != imported_comment.text, \
            'The text of the imported comment should be updated to contain the new access id'
        assert imported_comment_rt_fc.download_url(access_id=imported_comment_rt_fc.access_id) in imported_comment.text\
            and not source_comment_rt_fc.download_url(access_id=source_comment_rt_fc.access_id) \
            in imported_comment.text, 'The download url should be updated in the comment text'

        source_comment = factory.TeacherComment(published=False)
        self.assertRaises(VLEProgrammingError, import_utils.import_comment, source_comment, source_comment.entry)

    # TODO JIR
    # def test_content_import(self):
    #     journal = factory.PopulatedJournal()

    #     contents = Content.objects.filter(entry__node__journal=journal)
    #     entries = Entry.objects.filter(node__journal=journal)

    #     for entry in entries:
    #         print(entry.template.field_set.all())

    #     print(contents)
    #     print(journal)

    #     content = contents.first()

    #     import_utils.import_content(content, entries.first())

    #     print(Content.objects.filter(entry__node__journal=journal))

    #     assert False
