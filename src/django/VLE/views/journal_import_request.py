from rest_framework import viewsets

import VLE.lti1p3 as lti
import VLE.utils.generic_utils as utils
import VLE.utils.import_utils as import_utils
import VLE.utils.responses as response
from VLE.models import Assignment, Entry, Journal, JournalImportRequest, Node
from VLE.serializers import JournalImportRequestSerializer


class JournalImportRequestView(viewsets.ViewSet):
    def list(self, request):
        """
        Lists all journal import requests (JIR) for a given (import) target journal.

        JIRs are not (fully) serialized alongside their respective journals in order to speedup the
        assignment page, as JIRs occur infrequently. Instead Entries serialize a trimmed version.
        """
        journal_target_id, = utils.required_typed_params(request.query_params, (int, 'journal_target_id'))

        journal_target = Journal.objects.get(pk=journal_target_id)
        request.user.check_permission('can_manage_journal_import_requests', journal_target.assignment)

        serializer = JournalImportRequestSerializer(
            JournalImportRequestSerializer.setup_eager_loading(
                journal_target.import_request_targets.filter(state=JournalImportRequest.PENDING)
            ),
            context={'user': request.user},
            many=True,
        )

        return response.success({'journal_import_requests': serializer.data})

    def create(self, request):
        assignment_source_id, assignment_target_id = utils.required_typed_params(
            request.data, (int, 'assignment_source_id'), (int, 'assignment_target_id'))

        assignment_target = Assignment.objects.get(pk=assignment_target_id)

        journal_source = Journal.objects.get(assignment=assignment_source_id, authors__user=request.user)
        journal_target = Journal.objects.get(assignment=assignment_target, authors__user=request.user)

        if JournalImportRequest.objects.filter(state=JournalImportRequest.PENDING, target=journal_target,
                                               source=journal_source).exists():
            return response.success(
                description='The journal import request is awaiting approval from your instructor.')

        jir = JournalImportRequest.objects.create(source=journal_source, target=journal_target, author=request.user)

        serializer = JournalImportRequestSerializer(
            JournalImportRequestSerializer.setup_eager_loading(JournalImportRequest.objects.filter(pk=jir.pk)).get(),
            context={'user': request.user},
        )
        return response.created({'journal_import_request': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """
        Handles the processing of a pending JIR. There are three possible outcomes:

        - Decline the request
        - Approve import including any previous grades
        - Approve import without any of the previous grades

        The processed JIR instance is stored as a history of import requests.
        """
        pk, = utils.required_typed_params(kwargs, (int, 'pk'))
        jir_action, = utils.required_typed_params(request.data, (str, 'jir_action'))

        jir = JournalImportRequest.objects.get(pk=pk, state=JournalImportRequest.PENDING)

        allowed_actions = [abbr for (abbr, _) in jir.STATES if (abbr not in [jir.PENDING, jir.EMPTY_WHEN_PROCESSED])]
        if jir_action not in allowed_actions:
            return response.bad_request('Invalid journal import request action.')

        request.user.check_permission('can_manage_journal_import_requests', jir.target.assignment)

        jir.state = jir_action
        jir.processor = request.user

        source_entries = Entry.objects.none()
        if not jir_action == jir.DECLINED:
            source_entries = Entry.objects.filter(node__journal=jir.source)
            if not source_entries.exists():
                jir.state = jir.EMPTY_WHEN_PROCESSED

        entries_before = list(Entry.objects.filter(node__journal=jir.target).values_list('pk', flat=True))
        nodes_before = list(Node.objects.filter(journal=jir.target).values_list('pk', flat=True))

        try:
            for source_entry in source_entries:
                import_utils.import_entry(source_entry, jir.target, jir=jir)
        except Exception as e:
            Entry.objects.filter(node__journal=jir.target).exclude(pk__in=entries_before).delete()
            Node.objects.filter(journal=jir.target).exclude(pk__in=nodes_before).delete()
            raise e

        if jir_action == jir.APPROVED_INC_GRADES:
            lti.grading.task_send_grade.delay(author_pks=jir.target.values_list('authors__pk', flat=True))

        jir.save()

        return response.success(description=jir.get_update_response())
