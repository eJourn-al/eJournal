import test.factory as factory
from test.utils import api

from django.test import TestCase

from VLE.models import (Assignment, AssignmentParticipation, Content, Course, Entry, Field, Format, Journal,
                        JournalImportRequest, Node, PresetNode, Role, Template, Comment)


class JournalImportRequestTest(TestCase):
    def test_journal_import_request_factory(self):
        jir = factory.JournalImportRequest(author=factory.Student())

        assert JournalImportRequest.objects.count() == 1, 'A single journal import request is created'
        assert jir.target.pk != jir.source.pk, 'A unique journal is generated for both the source and target'

        # A jir generates only a single ap for both its source and target
        ap_source = AssignmentParticipation.objects.get(journal=jir.source)
        ap_target = AssignmentParticipation.objects.get(journal=jir.target)

        assert jir.author.pk is ap_source.user.pk and jir.author.pk is ap_target.user.pk, \
            'A generated journal import request shares its author among the source and target journals'

    def test_list_jir(self):
        jir = factory.JournalImportRequest()
        supervisor = jir.target.assignment.author
        unrelated_teacher = factory.Teacher()
        data = {'journal_target_id': jir.target.pk}

        # Only relevant users can access JIRs
        api.get(self, 'journal_import_request', params=data, user=jir.author)
        api.get(self, 'journal_import_request', params=data, user=supervisor)
        api.get(self, 'journal_import_request', params=data, user=unrelated_teacher, status=403)

        jir2 = factory.JournalImportRequest(author=jir.author, target=jir.target)
        # Also generate an unrelated JIR
        factory.JournalImportRequest()

        resp = api.get(self, 'journal_import_request', params=data, user=jir.author)['journal_import_requests']

        assert len(resp) == 2, 'Both JIRs are serialized'
        assert resp[0]['id'] == jir.pk and resp[1]['id'] == jir2.pk, 'The correct JIRs are serialized'
        assert resp[0]['source']['journal']['id'] == jir.source.pk \
            and resp[0]['target']['journal']['id'] == jir.target.pk, \
            'The correct source and target journal are serialized'
        assert resp[0]['source']['journal']['import_requests'] == 0, \
            'JIR import_requests (count) are only serialized for the target journal'
        assert resp[0]['target']['journal']['import_requests'] == 2

    def test_create_jir(self):
        source_journal = factory.Journal()
        student = source_journal.authors.first().user

        target_assignment = factory.Assignment()
        different_student_journal = factory.Journal(assignment=target_assignment)

        ap = factory.AssignmentParticipation(assignment=target_assignment, user=student)
        target_journal = ap.journal

        # You cannot import a journal into itself
        data = {'journal_source_id': source_journal.pk, 'journal_target_id': source_journal.pk}
        api.create(self, 'journal_import_request', params=data, user=student, status=400)

        # You can only import from and to ones own journal
        data = {'journal_source_id': source_journal.pk, 'journal_target_id': different_student_journal.pk}
        api.create(self, 'journal_import_request', params=data, user=student, status=403)

        # You cannot request to import an empty journal
        data = {'journal_source_id': source_journal.pk, 'journal_target_id': target_journal.pk}
        api.create(self, 'journal_import_request', params=data, user=student, status=400)

        # So we create an entry in source_journal
        factory.Entry(node__journal=source_journal)

        # Succesfully create a JournalImportRequest
        data = {'journal_source_id': source_journal.pk, 'journal_target_id': target_journal.pk}
        resp = api.create(
            self, 'journal_import_request', params=data, user=student, status=201)['journal_import_request']

        jir = JournalImportRequest.objects.get(pk=resp['id'])
        assert jir.author.pk == student.pk, 'Author is correctly set'
        assert jir.source.pk == source_journal.pk, 'Source is correctly set'
        assert jir.target.pk == target_journal.pk, 'Target is correctly set'
        assert jir.processor is None, 'Processor is empty on JIR initialization'
        assert jir.state == JournalImportRequest.PENDING, 'JIR is awaiting processing'

    def test_patch_jir_permissions_and_actions(self):
        # TODO JIR: Fix 5 line instantation...
        course = factory.Course()
        teacher = course.author
        source_journal = factory.Journal(assignment__author=teacher, assignment__courses=[course])
        target_journal = factory.Journal(assignment__author=teacher, assignment__courses=[course])
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)
        unrelated_teacher = factory.Teacher()

        # Only valid actions are processed
        data = {'pk': jir.pk, 'jir_action': 'BLA'}
        api.update(self, 'journal_import_request', params=data, user=jir.target.assignment.author, status=400)
        # One cannot an update a JIR to pending, only pending JIRs are processed
        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.PENDING}
        api.update(self, 'journal_import_request', params=data, user=jir.target.assignment.author, status=400)
        # One cannot update a jir to indicate it was empty when processed, this is determined during processing itself.
        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.EMPTY_WHEN_PROCESSED}
        api.update(self, 'journal_import_request', params=data, user=jir.target.assignment.author, status=400)

        # A JIR can only be updated by a supervisor
        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.DECLINED}
        api.update(self, 'journal_import_request', params=data, user=jir.author, status=403)
        api.update(self, 'journal_import_request', params=data, user=unrelated_teacher, status=403)
        api.update(self, 'journal_import_request', params=data, user=teacher, status=200)

        jir = JournalImportRequest.objects.get(pk=jir.pk)
        assert jir.state == JournalImportRequest.DECLINED, 'The jir action is updated'
        assert jir.processor.pk == teacher.pk, 'The jir processor is updated'

    def test_jir_import(self):
        # TODO JIR: Fix 5 line instantation...
        # TODO JIR: Test jir_action variant impact on entry grade and vle coupling states
        course = factory.Course()
        teacher = course.author
        source_journal = factory.Journal(assignment__author=teacher, assignment__courses=[course])
        target_journal = factory.Journal(assignment__author=teacher, assignment__courses=[course])
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)

        entry1 = factory.Entry(node__journal=source_journal)
        factory.StudentComment(entry=entry1, published=True)
        factory.TeacherComment(entry=entry1, published=False)
        factory.TeacherComment(entry=entry1, published=True)
        factory.PresetEntry(node__journal=source_journal)

        assert PresetNode.objects.filter(type=Node.ENTRYDEADLINE, node__journal=source_journal).exists(), \
            'We are testing with preset nodes'

        pre_import_entry_count = Entry.objects.filter(node__journal=jir.target).count()
        source_entry_count = Entry.objects.filter(node__journal=jir.source).count()
        pre_import_comment_count = Comment.objects.filter(entry__node__journal=jir.target).count()
        source_published_comment_count = Comment.objects.filter(entry__node__journal=jir.source, published=True).count()

        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_INC_GRADES}
        api.update(self, 'journal_import_request', params=data, user=teacher, status=200)

        # TODO JIR: Doesnt this test always evaluate to True due to the node__journal query?
        for entry in Entry.objects.filter(node__journal=jir.target):
            entry.node in target_journal.node_set.all(), 'Node set correctly updated'

        assert pre_import_entry_count + source_entry_count == Entry.objects.filter(node__journal=jir.target).count(), \
            'Post import entry count increased by the source journal entry count'
        assert pre_import_comment_count + source_published_comment_count \
            == Comment.objects.filter(entry__node__journal=jir.target).count(), \
            'Post import comment count increased by the PUBLISHED source comment count'
