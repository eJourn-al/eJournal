import test.factory as factory
from test.utils import api

from django.test import TestCase

from VLE.models import (Assignment, AssignmentParticipation, Content, Course, Entry, Field, Format, Journal,
                        JournalImportRequest, Node, PresetNode, Role, Template)


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
        journal1_student1 = factory.Journal()
        student1 = journal1_student1.authors.first().user
        assignment = journal1_student1.assignment

        assignment2 = factory.Assignment()
        journal1_student2 = factory.Journal(assignment=assignment2)

        ap = factory.AssignmentParticipation(assignment=assignment2, user=student1)
        journal2_student1 = ap.journal

        # You cannot import a journal into itself
        data = {'journal_source_id': journal1_student1.pk, 'journal_target_id': journal1_student1.pk}
        api.create(self, 'journal_import_request', params=data, user=student1, status=400)

        # You can only import from and to ones own journal
        data = {'journal_source_id': journal1_student1.pk, 'journal_target_id': journal1_student2.pk}
        api.create(self, 'journal_import_request', params=data, user=student1, status=403)

        # You cannot request to import an empty journal
        data = {'journal_source_id': journal1_student1.pk, 'journal_target_id': journal2_student1.pk}
        api.create(self, 'journal_import_request', params=data, user=student1, status=400)

        # So we create an entry in journal1_student1
        format = assignment.format
        template = factory.Template(format=format)
        valid_create_params = {
            'journal_id': journal1_student1.pk,
            'template_id': template.pk,
            'content': []
        }
        fields = Field.objects.filter(template=template)
        valid_create_params['content'] = [{'data': 'test data', 'id': field.id} for field in fields]
        api.create(self, 'entries', params=valid_create_params, user=student1)

        # Succesfully create a JournalImportRequest
        data = {'journal_source_id': journal1_student1.pk, 'journal_target_id': journal2_student1.pk}
        api.create(self, 'journal_import_request', params=data, user=student1, status=201)

    def test_patch_jir(self):
        # TODO JIR: Fix 5 line instantation...
        course = factory.Course()
        teacher = course.author
        source_journal = factory.Journal(assignment__author=teacher, assignment__courses=[course])
        target_journal = factory.Journal(assignment__author=teacher, assignment__courses=[course])
        jir = factory.JournalImportRequest(source=source_journal, target=target_journal)

        supervisor = jir.target.assignment.author
        assert supervisor.pk == teacher.pk
        unrelated_teacher = factory.Teacher()

        valid_action = JournalImportRequest.DECLINED
        invalid_action = 'BLA'

        # Only valid actions are processed
        data = {'pk': jir.pk, 'jir_action': invalid_action}
        api.update(self, 'journal_import_request', params=data, user=jir.target.assignment.author, status=400)

        # A JIR can only be updated by a supervisor
        data = {'pk': jir.pk, 'jir_action': valid_action}
        api.update(self, 'journal_import_request', params=data, user=jir.author, status=403)
        api.update(self, 'journal_import_request', params=data, user=unrelated_teacher, status=403)
        api.update(self, 'journal_import_request', params=data, user=supervisor, status=200)

    # def test_jir_copy(self):
    #     # TODO JIR: TODO
    #     assert False
