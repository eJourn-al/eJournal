import re
import test.factory as factory
import test.utils.generic_utils as test_utils
from test.utils import api

from django.test import TestCase

from VLE.models import (Assignment, AssignmentParticipation, Comment, Content, Course, Entry, Field, Format, Journal,
                        JournalImportRequest, Node, PresetNode, Role, Template)


class JournalImportRequestTest(TestCase):
    def test_journal_import_request_factory(self):
        jir_c = JournalImportRequest.objects.count()
        jir = factory.JournalImportRequest(author=factory.Student())

        assert JournalImportRequest.objects.count() == jir_c + 1, 'A single journal import request is created'
        assert jir.target.pk != jir.source.pk, 'A unique journal is generated for both the source and target'

        # A jir generates only a single ap for both its source and target
        ap_source = AssignmentParticipation.objects.get(journal=jir.source)
        ap_target = AssignmentParticipation.objects.get(journal=jir.target)

        assert jir.author.pk is ap_source.user.pk and jir.author.pk is ap_target.user.pk, \
            'A generated journal import request shares its author among the source and target journals'

        student = factory.Student()
        factory.AssignmentParticipation(user=student, assignment=jir.target.assignment)
        jir = factory.JournalImportRequest(author=factory.Student(), source__ap__user=student, target__ap__user=student)
        assert jir.target.authors.get(user=student.pk), 'Deep syntax works for source/target logic'

        jir2 = factory.JournalImportRequest(target=jir.target)
        assert jir.target.pk == jir2.target.pk, 'Directly assigning journal works'

        course = factory.Course()
        jir = factory.JournalImportRequest(source__assignment__courses=[course])
        assert jir.source.assignment.courses.first().pk == course.pk

        # # TODO JIR: Triggers unique constraint of AP (assignment, user) but why..
        # factory.JournalImportRequest(target__assignment__courses=[course], source__assignment__courses=[course])
        # # Despite the following being possible
        # j1 = factory.Journal(assignment__courses=[course])
        # j2 = factory.Journal(assignment__courses=[course])
        # factory.JournalImportRequest(source=j1, target=j2)

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

        assert len(resp) == 2, 'All JIRs for the given target are serialized'
        assert resp[0]['id'] == jir.pk and resp[1]['id'] == jir2.pk, 'The correct JIRs are serialized'
        assert resp[0]['source']['journal']['id'] == jir.source.pk \
            and resp[0]['target']['journal']['id'] == jir.target.pk, \
            'The correct source and target journal are serialized'
        assert resp[0]['source']['journal']['import_requests'] == 0, \
            'JIR import_requests (count) are only serialized for the target journal'
        assert resp[0]['target']['journal']['import_requests'] == 2

    def test_create_jir(self):
        # TODO JIR, test group journals, can a member of target import? source? both required?
        # it only makes sense if a student creates an import request of which he/she is both member, which is tested
        source_journal = factory.Journal(entries__n=0)
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
        factory.UnlimitedEntry(node__journal=source_journal)

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
        # TODO JIR, test group journals, can a member of target import? source? both required?
        course = factory.Course()
        teacher = course.author
        # TODO JIR fix source init once possible
        source = factory.Journal(assignment__courses=[course])
        jir = factory.JournalImportRequest(source=source, target__assignment__courses=[course])
        # jir = factory.JournalImportRequest(source=source_journal, target=target_journal)
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
        # TODO JIR: Test jir_action variant impact on entry grade and vle coupling states
        course = factory.Course()
        source_journal = factory.Journal(assignment__courses=[course])
        target_journal = factory.Journal(assignment__courses=[course])
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)

        entry1 = factory.UnlimitedEntry(node__journal=source_journal)
        factory.StudentComment(entry=entry1, published=True)
        factory.TeacherComment(entry=entry1, published=False)
        factory.TeacherComment(entry=entry1, published=True)
        factory.PresetEntry(node__journal=source_journal)
        factory.ProgressPresetNode(format=source_journal.assignment.format)

        pre_import_entry_count = Entry.objects.filter(node__journal=jir.target).count()
        pre_import_journal_node_count = Node.objects.filter(journal=jir.target).count()
        pre_import_comment_count = Comment.objects.filter(entry__node__journal=jir.target).count()
        pre_import_preset_node_count = PresetNode.objects.filter(format=jir.target.assignment.format).count()
        pre_import_needs_marking = target_journal.needs_marking
        source_entry_count = Entry.objects.filter(node__journal=jir.source).count()
        source_journal_node_count = Node.objects.filter(journal=jir.source).count()
        source_published_comment_count = Comment.objects.filter(entry__node__journal=jir.source, published=True).count()
        source_journal_progress_nodes = source_journal.node_set.filter(preset__type=Node.PROGRESS).count()
        source_journal_deadline_nodes_without_entry = \
            source_journal.node_set.filter(preset__type=Node.ENTRYDEADLINE, entry=None).count()

        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_INC_GRADES}
        api.update(self, 'journal_import_request', params=data, user=course.author, status=200)
        target_journal.refresh_from_db()
        source_journal.refresh_from_db()

        for entry in Entry.objects.filter(node__journal=jir.target):
            entry.node in jir.target.node_set.all(), 'Created nodes correctly linked via node set'

        assert pre_import_entry_count + source_entry_count == Entry.objects.filter(node__journal=jir.target).count(), \
            'Post import entry count increased by the source journal entry count'
        assert pre_import_comment_count + source_published_comment_count \
            == Comment.objects.filter(entry__node__journal=jir.target).count(), \
            'Post import comment count increased by the PUBLISHED source comment count'
        assert (pre_import_journal_node_count + source_journal_node_count - source_journal_progress_nodes
                - source_journal_deadline_nodes_without_entry) == Node.objects.filter(journal=jir.target).count(), \
            'Post import node count increased by the source node count (wtihout progress and empty deadline nodes'
        assert pre_import_preset_node_count == PresetNode.objects.filter(format=jir.target.assignment.format).count(), \
            'Post import preset node count unaffected by the source preset node count'
        target_journal.needs_marking == pre_import_needs_marking, \
            'Approving including grades should not increase needs marking'

        jir = factory.JournalImportRequest(source=source_journal, target=factory.Journal(assignment__courses=[course]))
        pre_import_needs_marking = jir.target.needs_marking
        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_EXC_GRADES}
        api.update(self, 'journal_import_request', params=data, user=course.author, status=200)
        jir.target.refresh_from_db()

        jir.target.needs_marking == pre_import_needs_marking, \
            'Approving excluding grades should increase needs marking'

    # TODO JIR: Reenable once tests are fixed
    # def test_jir_import_result_via_serialization(self):
    #     course = factory.Course()
    #     source_journal = factory.Journal(assignment__courses=[course])
    #     jir = factory.JournalImportRequest(
    #         source=source_journal,
    #         target=factory.Journal(assignment__courses=[course], entries__n=0)
    #     )

    #     assert not jir.target.node_set.exists() and not jir.target.assignment.format.presetnode_set.exists(), \
    #         'Target journal is initialized empty'

    #     entry1 = factory.UnlimitedEntry(node__journal=source_journal)
    #     factory.StudentComment(entry=entry1, published=True)
    #     factory.TeacherComment(entry=entry1, published=True)
    #     factory.PresetEntry(node__journal=source_journal)
    #     factory.ProgressPresetNode(format=source_journal.assignment.format)

    #     pre_source_journal_resp = api.get(self, 'journals', params={'pk': jir.source.pk}, user=course.author)['journal']
    #     pre_source_node_resp = api.get(self, 'nodes', params={'journal_id': jir.source.pk}, user=course.author)['nodes']
    #     pre_target_journal_resp = api.get(self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']

    #     data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_INC_GRADES}
    #     api.update(self, 'journal_import_request', params=data, user=course.author, status=200)

    #     post_source_journal_resp = api.get(
    #         self, 'journals', params={'pk': jir.source.pk}, user=course.author)['journal']
    #     post_source_node_resp = api.get(
    #         self, 'nodes', params={'journal_id': jir.source.pk}, user=course.author)['nodes']

    #     post_target_journal_resp = api.get(
    #         self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']
    #     post_target_node_resp = api.get(
    #         self, 'nodes', params={'journal_id': jir.target.pk}, user=course.author)['nodes']

    #     assert pre_source_journal_resp == post_source_journal_resp, 'Soure journal is unchanged'
    #     assert pre_source_node_resp == post_source_node_resp, 'Source journal nodes are unchanged'

    #     for source_node, target_node in zip(pre_source_node_resp, post_target_node_resp):
    #         assert test_utils.equal_models(
    #             source_node, target_node,
    #             ignore_keys=['jID', 'nID', 'creation_date', 'last_edited', 'download_url'],
    #             exclude_regex_paths=[
    #                 # QUESTION: Below fixes flake8 warning for IDE, but not for pytest? Cleanest solution?
    #                 # noqa: W605
    #                 "^{}\d{}$".format(re.escape(r"root['entry']['content']["), re.escape(r"]['entry']")),
    #                 re.escape(r"root['entry']['id']"),
    #                 "^{}\d{}$".format(re.escape(r"root['entry']['content']["), re.escape(r"]['data']['id']"))
    #             ]
    #         ), '''Match node responses except ignore_keys and entry.content.<id>.entry, entry.id,
    #               entry.content.<id>.data.id'''

    #     assert test_utils.equal_models(pre_target_journal_resp, post_target_journal_resp), \
    #         'Target journal should have NO new entries to mark as the import action was approve including grades'
