import test.factory as factory
import test.utils.generic_utils as test_utils
from test.utils.generic_utils import (check_equality_of_imported_file_context, check_equality_of_imported_rich_text,
                                      equal_models, zip_equal)

from django.test import TestCase

import VLE.utils.import_utils as import_utils
from VLE.models import Comment, Content, Entry, Field, FileContext, JournalImportRequest
from VLE.utils.error_handling import VLEProgrammingError


class ImportTest(TestCase):
    def test_generic_test_utils_equal_models(self):
        a = {'a': {'b': 1}}
        b = {'a': {'b': 2}}

        assert not test_utils.equal_models(a, b)
        b['a']['b'] = 1
        assert test_utils.equal_models(a, b)

        c1 = factory.Course()
        c2 = factory.Course(author=c1.author, startdate=c1.startdate, enddate=c1.enddate, name=c1.name,
                            abbreviation=c1.abbreviation)

        assert test_utils.equal_models(c1, c2, ignore_keys=['id', 'creation_date', 'update_date'])

    def test_generic_test_utils_zip_equal(self):
        a = [1, 2]
        b = [1, 2, 3]

        with self.assertRaises(ValueError):
            for a, b in zip_equal(a, b):
                assert a == b

        with self.assertRaises(ValueError):
            for b, a in zip_equal(b, a):
                assert a == b

        a = [1, 2, 3]
        for a, b in zip_equal(a, b):
            assert a == b

    def test_comment_import_with_attached_files(self):
        source_comment = factory.StudentComment(n_att_files=1)
        source_comment_pk = source_comment.pk
        target_entry = factory.UnlimitedEntry()

        count = Comment.objects.filter(entry=target_entry).count()
        imported_comment = import_utils.import_comment(source_comment, target_entry)
        source_comment = Comment.objects.get(pk=source_comment_pk)
        source_fc = source_comment.attached_files.first()
        import_fc = imported_comment.attached_files.first()

        assert source_comment.attached_files.count() == 1, 'M2M files of the source comment is of correct length'
        assert FileContext.objects.filter(comment=source_comment, in_rich_text=False).count() == 1, \
            'No additional files are associated with the source comment'
        assert source_comment.attached_files.filter(pk=source_fc.pk).exists(), \
            'Source comment M2M files still contains the correct fc'

        assert source_comment.pk != imported_comment.pk, 'The imported comment instance differs from the original'
        assert Comment.objects.filter(entry=target_entry).count() == count + 1, \
            'One additional comment is created'
        assert equal_models(
            source_comment, imported_comment,
            ignore_keys=['creation_date', 'update_date', 'attached_files', 'id', 'entry']), \
            'The imported model is mostly equal to the source model'

        assert FileContext.objects.filter(comment=imported_comment).count() == 1, \
            'FCs are copied alongside the comment import.'
        assert imported_comment.attached_files.count() == 1, 'Comment M2M files is updated'
        assert imported_comment.attached_files.filter(pk=import_fc.pk).exists(), \
            'imported comment M2M files contains the correct FC'

        assert equal_models(
            source_fc, import_fc,
            ignore_keys=['last_edited', 'creation_date', 'update_date', 'id', 'comment', 'journal', 'access_id']
        )
        assert import_fc.journal.pk == target_entry.node.journal.pk, 'Created fc is linked to the target journal'
        assert import_fc.comment.id == imported_comment.pk, 'Created fc is linked to the created comment'
        assert import_fc.file.path != source_fc.file.path, 'New file on disk'
        assert import_fc.access_id != source_fc.access_id, 'New access id'

    def test_comment_import_with_rich_text_files(self):
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

        check_equality_of_imported_rich_text(source_comment.text, imported_comment.text, Comment)

    def test_cannot_import_unpublished_comments(self):
        source_comment = factory.TeacherComment(published=False)
        self.assertRaises(VLEProgrammingError, import_utils.import_comment, source_comment, source_comment.entry)
        source_comment = factory.StudentComment(published=False)
        self.assertRaises(VLEProgrammingError, import_utils.import_comment, source_comment, source_comment.entry)

    def test_copy_entry_and_node(self):
        source_entry = factory.UnlimitedEntry()
        target_journal = factory.Journal(entries__n=0, ap__user=source_entry.node.journal.authors.first().user)

        copied_node_instance = import_utils.copy_node(source_entry.node, target_journal)
        assert copied_node_instance.pk != source_entry.node.pk
        assert equal_models(
            source_entry.node,
            copied_node_instance,
            ignore_keys=['update_date', 'id', 'creation_date', 'journal', 'entry']
        ), 'Copied node is equal to the source node apart from the journal and entry'
        assert copied_node_instance.journal.pk == target_journal.pk, \
            'Node should be linked to the provided target journal'

        copied_entry_instance = import_utils.copy_entry(source_entry, node=copied_node_instance)
        assert copied_entry_instance.pk != source_entry
        assert equal_models(
            source_entry, copied_entry_instance, ignore_keys=['update_date', 'id', 'creation_date'])
        assert copied_entry_instance.node.entry.pk == copied_entry_instance.pk, \
            'Copied node is linked to the provided entry'
        assert copied_entry_instance.node.journal == target_journal, 'Entry is linked to the target journal'

    def test_content_import(self):
        assignment = factory.Assignment(format__templates=[])
        factory.TemplateAllTypes(format=assignment.format)
        source_entry = factory.UnlimitedEntry(node__journal__assignment=assignment)
        target_journal = factory.Journal(assignment=assignment, entries__n=0, ap__user=source_entry.author)

        copied_node = import_utils.copy_node(source_entry.node, target_journal)
        copied_entry = import_utils.copy_entry(source_entry, node=copied_node)
        ignore_keys = ['id', 'entry', 'update_date', 'creation_date']

        for source_content in source_entry.content_set.all():
            source_content_pk = source_content.pk
            # NOTE: This action modifies the reference of source content into imported content
            imported_content = import_utils.import_content(source_content, copied_entry)
            source_content = Content.objects.get(pk=source_content_pk)

            assert imported_content.pk != source_content.pk, 'The imported content is a different row'
            assert imported_content.entry.pk == copied_entry.pk, 'The imported content is linked to the copied entry'

            if source_content.field.type == Field.RICH_TEXT:
                assert FileContext.objects.filter(content=source_content, is_temp=False, in_rich_text=True).exists()
                assert equal_models(source_content, imported_content, ignore_keys=ignore_keys + ['data'])
                check_equality_of_imported_rich_text(source_content.data, imported_content.data, Content)
            elif source_content.field.type == Field.FILE:
                assert FileContext.objects.filter(content=source_content, is_temp=False, in_rich_text=False).exists()
                # There should only be one fc per content of type FILE
                source_fc = FileContext.objects.get(pk__in=source_content.filecontext_set.all().values('pk'))
                imported_fc = FileContext.objects.get(pk__in=imported_content.filecontext_set.all().values('pk'))
                assert source_fc.pk != imported_fc.pk
                assert imported_fc.pk == int(imported_content.data), \
                    'Data is correctly set to the pk of corresponding file context'

                assert equal_models(source_content, imported_content, ignore_keys=ignore_keys + ['data'])
                check_equality_of_imported_file_context(
                    source_fc,
                    imported_fc,
                    ignore_keys=['last_edited', 'creation_date', 'update_date', 'id', 'access_id', 'content', 'journal']
                )

                assert imported_fc.journal.pk == target_journal.pk, 'FC is linked to the target journal'
            else:
                assert equal_models(source_content, imported_content, ignore_keys=ignore_keys)

            assert imported_content.field.template.pk == source_content.field.template.pk, \
                'The template of the original content is used for the imported content'

    def test__copy_grade_based_on_jir_action(self):
        journal = factory.Journal()
        journal2 = factory.Journal(ap__user=journal.authors.first().user)
        teacher2 = factory.Teacher()

        entry = factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=True)
        new_entry = factory.UnlimitedEntry(node__journal=journal2, grade=None)
        grade = import_utils._copy_grade_based_on_jir_action(
            new_entry, entry.grade, teacher2, JournalImportRequest.APPROVED_INC_GRADES)

        # Only approved JIR states allow for grade copy
        self.assertRaises(
            VLEProgrammingError,
            import_utils._copy_grade_based_on_jir_action,
            entry, entry.grade, teacher2, JournalImportRequest.PENDING
        )
        assert grade.pk != entry.grade.pk, 'A new grade object is created'
        assert grade.grade == entry.grade.grade, \
            'When approving including grades, the entry\'s grade\'s points is copied'
        assert grade.author.pk == teacher2.pk, 'The passed author is set as author of the grade'
        assert grade.published, 'The grade is always published'
        assert grade.entry.pk == new_entry.pk, 'The copied grade is linked to the passed entry'

        entry = factory.UnlimitedEntry(node__journal=journal, grade=None)
        grade = import_utils._copy_grade_based_on_jir_action(
                entry, entry.grade, teacher2, JournalImportRequest.APPROVED_INC_GRADES)
        assert grade is None, 'Approved including grades with a previous grade of None creates no new grade object'

        entry = factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)
        grade = import_utils._copy_grade_based_on_jir_action(
                entry, entry.grade, teacher2, JournalImportRequest.APPROVED_INC_GRADES)
        assert grade is None, 'Copying an unpublished grade should yield no new grade'

        grade = import_utils._copy_grade_based_on_jir_action(
                entry, entry.grade, teacher2, JournalImportRequest.APPROVED_EXC_GRADES)
        assert grade is None, 'Approved excluding grades creates no new grade object'

        grade = import_utils._copy_grade_based_on_jir_action(
            entry, entry.grade, teacher2, JournalImportRequest.APPROVED_WITH_GRADES_ZEROED)
        assert grade.grade == 0, 'Approved with grades zeroed creates a new grade object set to zero.'

    def test__select_vle_coupling_based_on_jir_action(self):
        f = import_utils._select_vle_coupling_based_on_jir_action
        journal = factory.Journal()
        entry = factory.UnlimitedEntry(node__journal=journal, grade__grade=1, grade__published=False)

        self.assertRaises(VLEProgrammingError, f, JournalImportRequest.DECLINED, entry)

        vle_coupling = f(JournalImportRequest.APPROVED_INC_GRADES, entry)
        assert vle_coupling == Entry.NEEDS_GRADE_PASSBACK, 'When grades are approved they need to be sent to the VLE'

        entry = factory.UnlimitedEntry(node__journal=journal, grade=None)
        vle_coupling = f(JournalImportRequest.APPROVED_INC_GRADES, entry)
        assert vle_coupling == Entry.NEEDS_SUBMISSION, \
            'When grades are approved but the entry has no grade, the entry requires a new grade'

        vle_coupling = f(JournalImportRequest.APPROVED_EXC_GRADES, entry)
        assert vle_coupling == Entry.NEEDS_SUBMISSION, 'WHen grades are excluded, the entries need a new grade'

        vle_coupling = f(JournalImportRequest.APPROVED_WITH_GRADES_ZEROED, entry)
        assert vle_coupling == Entry.NEEDS_GRADE_PASSBACK, \
            'When grades are zeroed, those grade need to be sent to the VLE'
