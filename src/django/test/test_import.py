import test.factory as factory
import test.utils.generic_utils as test_utils
from test.utils.generic_utils import equal_models

from django.test import TestCase

import VLE.utils.import_utils as import_utils
from VLE.models import Comment, FileContext
from VLE.utils.error_handling import VLEProgrammingError


class ImportTest(TestCase):
    def test_generic_test_utils(self):
        a = {'a': {'b': 1}}
        b = {'a': {'b': 2}}

        assert not test_utils.equal_models(a, b)
        b['a']['b'] = 1
        assert test_utils.equal_models(a, b)

        c1 = factory.Course()
        c2 = factory.Course(author=c1.author, startdate=c1.startdate, enddate=c1.enddate)

        assert test_utils.equal_models(c1, c2, ignore_keys=['id', 'creation_date', 'update_date'])

    def test_comment_import(self):
        source_comment = factory.StudentComment(n_att_files=1)
        source_comment_pk = source_comment.pk

        count = Comment.objects.filter(entry=source_comment.entry).count()
        imported_comment = import_utils.import_comment(source_comment, source_comment.entry)
        source_comment = Comment.objects.get(pk=source_comment_pk)
        source_fc = source_comment.files.first()
        import_fc = imported_comment.files.first()

        assert source_comment.files.count() == 1, 'M2M files of the source comment is of correct length'
        assert FileContext.objects.filter(comment=source_comment, in_rich_text=False).count() == 1, \
            'No additional files are associated with the source comment'
        assert source_comment.files.filter(pk=source_fc.pk).exists(), \
            'Source comment M2M files still contains the correct fc'

        assert source_comment.pk != imported_comment.pk, 'The imported comment instance differs from the original'
        assert Comment.objects.filter(entry=source_comment.entry).count() == count + 1, \
            'One additional comment is created'
        assert equal_models(
            source_comment, imported_comment,
            ignore_keys=['last_edited', 'creation_date', 'update_date', 'files', 'id']), \
            'The imported model is mostly equal to the source model'

        assert FileContext.objects.filter(comment=imported_comment).count() == 1, \
            'FCs are copied alongside the comment import.'
        assert imported_comment.files.count() == 1, 'Comment M2M files is updated'
        assert imported_comment.files.filter(pk=import_fc.pk).exists(), \
            'imported comment M2M files contains the correct FC'

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
    def test_content_import(self):
        pass
