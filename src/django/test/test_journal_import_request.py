import re
import test.factory as factory
import test.utils.generic_utils as test_utils
from test.utils import api

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone

import VLE.utils.generic_utils as utils
from VLE.models import (AssignmentParticipation, Comment, Content, Entry, Field, FileContext, JournalImportRequest,
                        Node, PresetNode)


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

    def test_unpublish_assignment_with_outstanding_jirs(self):
        source_ass = factory.Assignment()
        target_ass = factory.Assignment()

        # It should be no problem to change the published state of a fresh assignment
        assert target_ass.can_unpublish(), 'Without entries or JIRs it should be possible to unpublish the assignment'
        api.update(self, 'assignments', params={'pk': target_ass.pk, 'is_published': False}, user=target_ass.author)
        api.update(self, 'assignments', params={'pk': target_ass.pk, 'is_published': True}, user=target_ass.author)

        # Create an outstanding JIR for the target assignment
        jir = factory.JournalImportRequest(source__assignment=source_ass, state=JournalImportRequest.PENDING,
                                           target__assignment=target_ass, target__entries__n=0)

        # It should no longer be possible to unpublish
        assert target_ass.has_outstanding_jirs(), 'Target assignment should now register outstanding JIRs'
        assert not target_ass.can_unpublish(), 'With outstanding JIRs it should not be possible to unpublish'
        jir.state = JournalImportRequest.DECLINED
        jir.save()
        assert not target_ass.has_outstanding_jirs(), 'Target assignment should no longer register outstanding JIRs'
        assert target_ass.can_unpublish(), 'Without outstanding JIRs it should again be possible to unpublish'
        jir.state = JournalImportRequest.PENDING
        jir.save()
        api.update(self, 'assignments', params={'pk': target_ass.pk, 'is_published': False},
                   user=target_ass.author, status=400)

        jir.state = JournalImportRequest.DECLINED
        jir.save()
        api.update(self, 'assignments', params={'pk': target_ass.pk, 'is_published': False}, user=target_ass.author)

    def test_pending_jir_delete_on_leave_group_journal(self):
        student = factory.Student()
        student2 = factory.Student()
        student3 = factory.Student()

        g_journal = factory.GroupJournal(ap__user=student, add_users=[student2, student3])

        factory.JournalImportRequest(target=g_journal, author=student2, state=JournalImportRequest.PENDING)
        approved_jir = factory.JournalImportRequest(
            target=g_journal, author=student2, state=JournalImportRequest.APPROVED_EXC_GRADES)

        api.update(self, 'journals/leave', params={'pk': g_journal.pk}, user=student)
        assert g_journal.import_request_targets.count() == 2, \
            'Kicking a group journal student who did not author a PENDING JIR, should not affect the JIR'

        api.update(self, 'journals/leave', params={'pk': g_journal.pk}, user=student2)
        remaining_jir = JournalImportRequest.objects.get(pk__in=g_journal.import_request_targets.all().values('pk'))
        assert remaining_jir == approved_jir, 'The pending JIR is removed, and the approved JIR is unaffected'

        factory.JournalImportRequest(author=student, source=g_journal, state=JournalImportRequest.PENDING)
        source_approved_jir = factory.JournalImportRequest(
            author=student, source=g_journal, state=JournalImportRequest.APPROVED_EXC_GRADES)

        api.update(self, 'journals/leave', params={'pk': g_journal.pk}, user=student3)
        remaining_jir_ids = g_journal.import_request_targets.all().values('pk') \
            | g_journal.import_request_sources.all().values('pk')
        remaining_jir = JournalImportRequest.objects.get(pk__in=remaining_jir_ids)
        assert remaining_jir == source_approved_jir, \
            '''When the final group member is removed, the journal reset is triggered. This should remove all
            jirs apart from those approved with the journal as source. These imported entries should remain flagged
            as imported.'''

    def test_pending_jir_delete_on_kick_group_journal(self):
        student = factory.Student()
        student2 = factory.Student()
        student3 = factory.Student()

        g_journal = factory.GroupJournal(ap__user=student, add_users=[student2, student3])

        factory.JournalImportRequest(target=g_journal, author=student2, state=JournalImportRequest.PENDING)
        approved_jir = factory.JournalImportRequest(
            target=g_journal, author=student2, state=JournalImportRequest.APPROVED_EXC_GRADES)

        api.update(self, 'journals/kick',
                   params={'pk': g_journal.pk, 'user_id': student.pk}, user=g_journal.assignment.author)
        assert g_journal.import_request_targets.count() == 2, \
            'Kicking a group journal student who did not author a PENDING JIR, should not affect the JIR'

        api.update(self, 'journals/kick',
                   params={'pk': g_journal.pk, 'user_id': student2.pk}, user=g_journal.assignment.author)
        remaining_jir = JournalImportRequest.objects.get(pk__in=g_journal.import_request_targets.all().values('pk'))
        assert remaining_jir == approved_jir, 'The pending JIR is removed, and the approved JIR is unaffected'

        factory.JournalImportRequest(author=student, source=g_journal, state=JournalImportRequest.PENDING)
        source_approved_jir = factory.JournalImportRequest(
            author=student, source=g_journal, state=JournalImportRequest.APPROVED_EXC_GRADES)

        api.update(self, 'journals/kick',
                   params={'pk': g_journal.pk, 'user_id': student3.pk}, user=g_journal.assignment.author)
        remaining_jir_ids = g_journal.import_request_targets.all().values('pk') \
            | g_journal.import_request_sources.all().values('pk')
        remaining_jir = JournalImportRequest.objects.get(pk__in=remaining_jir_ids)
        assert remaining_jir == source_approved_jir, \
            '''When the final group member is removed, the journal reset is triggered. This should remove all
            jirs apart from those approved with the journal as source. These imported entries should remain flagged
            as imported.'''

    def test_remove_jirs_on_user_remove_from_jounal(self):
        student = factory.Student()
        student2 = factory.Student()

        team_a_assign_a = factory.GroupJournal(ap__user=student, add_users=[student2])
        team_a_assign_b = factory.GroupJournal(ap__user=student, add_users=[student2])

        shared_pending_jir = factory.JournalImportRequest(
            author=student, source=team_a_assign_a, target=team_a_assign_b, state=JournalImportRequest.PENDING)
        shared_approved_jir = factory.JournalImportRequest(
            author=student,
            source=team_a_assign_a,
            target=team_a_assign_b,
            state=JournalImportRequest.APPROVED_INC_GRADES
        )
        unshared_source_pending_jir = factory.JournalImportRequest(
            author=student, target=team_a_assign_b, state=JournalImportRequest.PENDING)
        unshared_source_approved_jir = factory.JournalImportRequest(
            author=student, target=team_a_assign_b, state=JournalImportRequest.APPROVED_INC_GRADES)
        unrelated_pending_jir = factory.JournalImportRequest(
            author=student, state=JournalImportRequest.PENDING)
        unrelated_approved_jir = factory.JournalImportRequest(
            author=student, state=JournalImportRequest.APPROVED_INC_GRADES)

        utils.remove_jirs_on_user_remove_from_jounal(student, team_a_assign_b)

        assert JournalImportRequest.objects.filter(pk=shared_pending_jir.pk).exists(), \
            'If a group member leaves and made an import requests from a shared assignment, the JIR should persist'
        assert JournalImportRequest.objects.filter(pk=shared_approved_jir.pk).exists(), \
            'Approved JIR should be unafeccted'
        assert not JournalImportRequest.objects.filter(pk=unshared_source_pending_jir.pk).exists(), \
            'If a group member leaves and made an import request from an unshared assignment, the JIR should be removed'
        assert JournalImportRequest.objects.filter(pk=unshared_source_approved_jir.pk).exists(), \
            'Approved JIR should be unafeccted'
        assert JournalImportRequest.objects.filter(pk=unrelated_pending_jir.pk).exists(), \
            'Pending unrelated JIRs should be unaffected'
        assert JournalImportRequest.objects.filter(pk=unrelated_approved_jir.pk).exists(), \
            'Approved unrelated JIRs should be unaffected'

    def test_delete_pending_jir_on_source_deletion(self):
        j = factory.Journal()
        jir = factory.JournalImportRequest(source=j, state=JournalImportRequest.PENDING)
        j.delete()
        assert not JournalImportRequest.objects.filter(pk=jir.pk).exists()

        j = factory.Journal()
        jir = factory.JournalImportRequest(source=j, state=JournalImportRequest.DECLINED)
        j.delete()
        assert JournalImportRequest.objects.filter(pk=jir.pk).exists()

    def test_list_jir(self):
        jir = factory.JournalImportRequest()
        supervisor = jir.target.assignment.author
        unrelated_teacher = factory.Teacher()
        data = {'journal_target_id': jir.target.pk}

        # Only relevant users can access JIRs
        api.get(self, 'journal_import_request', params=data, user=jir.author, status=403)
        api.get(self, 'journal_import_request', params=data, user=unrelated_teacher, status=403)
        api.get(self, 'journal_import_request', params=data, user=supervisor)

        # Supervisor can only access JIRs with can_manage_journal_import_requests permission
        supervisor_role = supervisor.participation_set.get(course=jir.target.assignment.courses.first()).role
        supervisor_role.can_manage_journal_import_requests = False
        supervisor_role.save()
        api.get(self, 'journal_import_request', params=data, user=supervisor, status=403)
        supervisor_role.can_manage_journal_import_requests = True
        supervisor_role.save()

        jir2 = factory.JournalImportRequest(author=jir.author, target=jir.target)
        # Also generate an unrelated JIR
        factory.JournalImportRequest()

        resp = api.get(self, 'journal_import_request', params=data, user=supervisor)['journal_import_requests']

        assert len(resp) == 2, 'All JIRs for the given target are serialized'
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
        different_assignment = factory.Assignment()

        ap = factory.AssignmentParticipation(assignment=target_assignment, user=student)
        target_journal = ap.journal

        # You cannot import a journal into itself
        data = {'assignment_source_id': source_journal.assignment.pk,
                'assignment_target_id': source_journal.assignment.pk}
        api.create(self, 'journal_import_request', params=data, user=student, status=400)

        # You can only import from and to ones own journal
        data = {'assignment_source_id': source_journal.assignment.pk, 'assignment_target_id': different_assignment.pk}
        api.create(self, 'journal_import_request', params=data, user=student, status=404)

        # Valid creation data
        data = {'assignment_source_id': source_journal.assignment.pk,
                'assignment_target_id': target_journal.assignment.pk}

        # You cannot create a JIR for a locked assignment
        target_assignment.lock_date = timezone.now() - relativedelta(seconds=1)
        target_assignment.save()
        api.create(self, 'journal_import_request', params=data, user=student, status=400)
        target_assignment.lock_date = timezone.now() + relativedelta(days=1)
        target_assignment.save()

        # If a pending JIR exists for the same target and source, respond with success
        pending_jir = factory.JournalImportRequest(
            state=JournalImportRequest.PENDING, source=source_journal, target=target_journal)
        api.create(self, 'journal_import_request', params=data, user=student, status=200)
        pending_jir.delete()

        approved_jir = factory.JournalImportRequest(
            state=JournalImportRequest.APPROVED_INC_GRADES, source=source_journal, target=target_journal)
        api.create(self, 'journal_import_request', params=data, user=student, status=400)
        approved_jir.delete()

        Entry.objects.filter(node__journal=source_journal).first().delete()
        # You cannot request to import an empty journal
        api.create(self, 'journal_import_request', params=data, user=student, status=400)

        # So we create an entry in source_journal
        factory.UnlimitedEntry(node__journal=source_journal)

        # successfully create a JournalImportRequest
        resp = api.create(
            self, 'journal_import_request', params=data, user=student, status=201)['journal_import_request']

        jir = JournalImportRequest.objects.get(pk=resp['id'])
        assert jir.author.pk == student.pk, 'Author is correctly set'
        assert jir.source.pk == source_journal.pk, 'Source is correctly set'
        assert jir.target.pk == target_journal.pk, 'Target is correctly set'
        assert jir.processor is None, 'Processor is empty on JIR initialization'
        assert jir.state == JournalImportRequest.PENDING, 'JIR is awaiting processing'

    def test_create_jir_for_group_journal(self):
        student2 = factory.Student()
        source_journal = factory.GroupJournal(add_users=[student2])
        target_journal = factory.GroupJournal(add_users=[student2])

        data = {'assignment_source_id': source_journal.assignment.pk,
                'assignment_target_id': target_journal.assignment.pk}
        api.create(self, 'journal_import_request', params=data, user=student2, status=201)

    def test_patch_jir_permissions_and_actions(self):
        course = factory.Course()
        teacher = course.author
        source = factory.Journal(assignment__courses=[course])
        jir = factory.JournalImportRequest(source=source, target__assignment__courses=[course])
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

    def test_jir_import_standalone(self):
        course = factory.Course()
        source_assignment = factory.Assignment(format__templates=False, courses=[course])
        factory.TemplateAllTypes(format=source_assignment.format)
        source_journal = factory.Journal(assignment=source_assignment)
        student = source_journal.authors.first().user
        assignment2 = factory.Assignment(courses=[course])
        target_journal = factory.Journal(assignment=assignment2, ap__user=student)
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

    def test_jir_import_result_via_serialization(self):
        course = factory.Course()
        source_assignment = factory.Assignment(format__templates=False, courses=[course])
        factory.TemplateAllTypes(format=source_assignment.format)
        source_journal = factory.Journal(assignment=source_assignment, entries__n=1)
        jir = factory.JournalImportRequest(
            source=source_journal,
            target=factory.Journal(
                assignment__courses=[course], entries__n=0, ap__user=source_journal.authors.first().user)
        )

        assert not jir.target.node_set.exists() and not jir.target.assignment.format.presetnode_set.exists(), \
            'Target journal is initialized empty'

        entry = Entry.objects.get(node__journal=source_journal)
        factory.StudentComment(entry=entry, published=True)
        factory.TeacherComment(entry=entry, published=True)
        factory.PresetEntry(node__journal=source_journal)
        factory.ProgressPresetNode(format=source_journal.assignment.format)

        pre_source_journal_resp = api.get(self, 'journals', params={'pk': jir.source.pk}, user=course.author)['journal']
        pre_source_node_resp = api.get(self, 'nodes', params={'journal_id': jir.source.pk}, user=course.author)['nodes']

        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_INC_GRADES}
        api.update(self, 'journal_import_request', params=data, user=course.author, status=200)

        post_source_journal_resp = api.get(
            self, 'journals', params={'pk': jir.source.pk}, user=course.author)['journal']
        post_source_node_resp = api.get(
            self, 'nodes', params={'journal_id': jir.source.pk}, user=course.author)['nodes']

        post_target_node_resp = api.get(
            self, 'nodes', params={'journal_id': jir.target.pk}, user=course.author)['nodes']

        assert pre_source_journal_resp == post_source_journal_resp, 'Soure journal is unchanged'
        assert pre_source_node_resp == post_source_node_resp, 'Source journal nodes are unchanged'

        for source_node, target_node in zip(pre_source_node_resp, post_target_node_resp):
            diff = test_utils.equal_models(
                source_node, target_node,
                return_diff=True,
                ignore_keys=['jID', 'nID', 'creation_date', 'last_edited', 'download_url', 'jir'],
                exclude_regex_paths=[
                    # Match exactly root['entry']['content']['<index>']['id']
                    r"^{}\d+{}$".format(re.escape(r"root['entry']['content']['"), re.escape(r"']['id']")),
                    # Match exactly root['entry']['id']
                    r"^{}$".format(re.escape(r"root['entry']['id']")),
                ]
            )
            assert target_node['entry']['jir']['source']['assignment']['name'] == source_assignment.name

            # The only remaining allowed difference would be RichText content of which the download url should
            # be updated to match the new (copied) file context, or content for a FILE field of which the data
            # updated to match the new pk.
            if diff:
                values_changed = diff.pop('values_changed', None)
                assert not diff and values_changed, \
                    'Node diff consists of something else than just changed values, e.g. added or removed keys'

                # Check if the difference is indeed the path of content data (entry.content.id)
                r = r"^{}\d+{}$".format(re.escape(r"root['entry']['content']['"), re.escape(r"']"))
                is_content_data = re.compile(r)

                for path, change in values_changed.items():
                    assert is_content_data.match(path) is not None, \
                        'A node value other than the content data is different'

                    # Assume working with a Field.FILE
                    if change['new_value'].isdigit():
                        source_fc = FileContext.objects.get(pk=int(change['old_value']))
                        imported_fc = FileContext.objects.get(pk=int(change['new_value']))

                        test_utils.check_equality_of_imported_file_context(source_fc, imported_fc)
                        test_utils.check_equality_of_imported_file_context(
                            source_fc, imported_fc,
                            ignore_keys=['last_edited', 'creation_date', 'update_date', 'id', 'access_id', 'content',
                                         'journal']
                        )
                        assert imported_fc.journal.pk == jir.target.pk, 'FC is linked to the target journal'
                    # Assume working with Field.RICH_TEXT
                    else:
                        test_utils.check_equality_of_imported_rich_text(
                            change['old_value'], change['new_value'], Content)

    def test_jir_import_action_approve_including_grade(self):
        course = factory.Course()
        source_assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}], courses=[course])
        source_journal = factory.Journal(assignment=source_assignment, entries__n=0)
        target_journal = factory.Journal(
            assignment__courses=[course], entries__n=0, ap__user=source_journal.authors.first().user)
        source_grade = 2
        target_grade = 1
        source_entry = factory.UnlimitedEntry(
            node__journal=source_journal, grade__published=True, grade__grade=source_grade)
        target_entry = factory.UnlimitedEntry(
            node__journal=target_journal, grade__published=True, grade__grade=target_grade)
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)

        # Fetch journal stats via API before the import approval
        pre_source_journal_resp = api.get(self, 'journals', params={'pk': jir.source.pk}, user=course.author)['journal']
        pre_target_journal_resp = api.get(self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']
        assert pre_source_journal_resp['grade'] == source_grade
        assert pre_target_journal_resp['grade'] == target_grade

        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_INC_GRADES}
        api.update(self, 'journal_import_request', params=data, user=course.author, status=200)

        # Fetch journal stats via API after the import approval
        post_target_journal_resp = api.get(
            self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']

        assert pre_source_journal_resp['grade'] + pre_target_journal_resp['grade'] == post_target_journal_resp['grade']

        created_entry = Entry.objects.filter(node__journal=jir.target).exclude(pk=target_entry.pk).first()
        assert created_entry.grade.pk != source_entry.grade.pk, \
            'A new grade object is created as start of a new grade history'

    def test_jir_import_action_approve_excluding_grade(self):
        course = factory.Course()
        source_assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}], courses=[course])
        source_journal = factory.Journal(assignment=source_assignment, entries__n=0)
        target_journal = factory.Journal(
            assignment__courses=[course], entries__n=0, ap__user=source_journal.authors.first().user)
        source_grade = 2
        target_grade = 1
        factory.UnlimitedEntry(node__journal=source_journal, grade__published=True, grade__grade=source_grade)
        target_entry = factory.UnlimitedEntry(
            node__journal=target_journal, grade__published=True, grade__grade=target_grade)
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)

        # Fetch journal stats via API before the import approval
        pre_target_journal_resp = api.get(self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']
        assert pre_target_journal_resp['grade'] == target_grade

        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_EXC_GRADES}
        api.update(self, 'journal_import_request', params=data, user=course.author, status=200)

        # Fetch journal stats via API after the import approval
        post_target_journal_resp = api.get(
            self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']

        assert pre_target_journal_resp['grade'] == post_target_journal_resp['grade'] == target_grade
        created_entry = Entry.objects.filter(node__journal=jir.target).exclude(pk=target_entry.pk).first()
        assert created_entry.grade is None, 'No grade should be set for the created entry when approving without grades'

    def test_jir_import_action_approve_with_grades_zeroed(self):
        course = factory.Course()
        source_assignment = factory.Assignment(format__templates=[{'type': Field.TEXT}], courses=[course])
        source_journal = factory.Journal(assignment=source_assignment, entries__n=0)
        target_journal = factory.Journal(
            assignment__courses=[course], entries__n=0, ap__user=source_journal.authors.first().user)
        source_grade = 2
        target_grade = 1
        factory.UnlimitedEntry(node__journal=source_journal, grade__published=True, grade__grade=source_grade)
        target_entry = factory.UnlimitedEntry(
            node__journal=target_journal, grade__published=True, grade__grade=target_grade)
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)

        # Fetch journal stats via API before the import approval
        pre_target_journal_resp = api.get(self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']
        assert pre_target_journal_resp['grade'] == target_grade

        data = {'pk': jir.pk, 'jir_action': JournalImportRequest.APPROVED_WITH_GRADES_ZEROED}
        api.update(self, 'journal_import_request', params=data, user=course.author, status=200)

        # Fetch journal stats via API after the import approval
        post_target_journal_resp = api.get(
            self, 'journals', params={'pk': jir.target.pk}, user=course.author)['journal']

        assert pre_target_journal_resp['grade'] == post_target_journal_resp['grade'] == target_grade, \
            'Total grade should not be increased as all new grades should be set to zero'
        created_entry = Entry.objects.filter(node__journal=jir.target).exclude(pk=target_entry.pk).first()
        assert created_entry.grade.grade == 0, 'Created grades should be set to zero'
