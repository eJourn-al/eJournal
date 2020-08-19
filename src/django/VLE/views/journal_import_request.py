from django.core.files.base import ContentFile
from rest_framework import viewsets

import VLE.utils.generic_utils as utils
import VLE.utils.import_utils as import_utils
import VLE.utils.responses as response
from VLE.models import (AssignmentParticipation, Comment, Content, Entry, FileContext, Grade, Journal,
                        JournalImportRequest, Node, PresetNode)
from VLE.serializers import JournalImportRequestSerializer
from VLE.utils import grading


class JournalImportRequestView(viewsets.ViewSet):
    def list(self, request):
        """
        Lists all journal import requests (JIR) for a given (import) target journal.

        JIRs are not (fully) serialized alongside their respective journals in order to speedup the
        assignment page, as JIRs occur infrequently.
        """
        journal_target_id, = utils.required_typed_params(request.query_params, (int, 'journal_target_id'))

        journal_target = Journal.objects.get(pk=journal_target_id)
        request.user.check_can_view(journal_target)

        serializer = JournalImportRequestSerializer(
            journal_target.import_request_target.filter(state=JournalImportRequest.PENDING),
            context={'user': request.user},
            many=True
        )

        return response.success({'journal_import_requests': serializer.data})

    def create(self, request):
        journal_source_id, journal_target_id = utils.required_typed_params(
            request.data, (int, 'journal_source_id'), (int, 'journal_target_id'))

        if journal_source_id is journal_target_id:
            return response.bad_request('You cannot import a journal into itself.')

        journal_source = Journal.objects.get(pk=journal_source_id)
        journal_target = Journal.objects.get(pk=journal_target_id)
        ap_source = AssignmentParticipation.objects.filter(user=request.user, journal=journal_source)
        ap_target = AssignmentParticipation.objects.filter(user=request.user, journal=journal_target)

        # TODO JIR: Block creation of JIR from source to target more than once once approved (with or without grade)
        # or Pending

        if not ap_source.exists() or not ap_target.exists():
            return response.forbidden('You can only import from or into your own journals.')
        # TODO JIR: Block on lock of target assignment

        if not Entry.objects.filter(node__journal=journal_source).exists():
            return response.bad_request('Please select a non empty journal.')

        jir = JournalImportRequest.objects.create(source=journal_source, target=journal_target, author=request.user)

        serializer = JournalImportRequestSerializer(jir, many=False, context={'user': request.user})
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

        if not request.user.has_permission('can_grade', jir.target.assignment):
            return response.forbidden('You require the ability to grade the journal in order to approve the import.')
        # TODO JIR: Make new permission for importing
        request.user.check_permission('can_edit_assignment', jir.target.assignment)

        jir.state = jir_action
        jir.processor = request.user

        source_entries = Entry.objects.none()
        if not jir_action == jir.DECLINED:
            source_entries = Entry.objects.filter(node__journal=jir.source)
            if not source_entries.exists():
                jir.state = jir.EMPTY_WHEN_PROCESSED

        # TODO JIR: Wrap in transaction.atomic block
        for source_entry in source_entries:
            import_utils.import_entry(source_entry, jir.target, copy_grade=jir_action == jir.APPROVED_INC_GRADES)

        # TODO JIR: Grading update requires some tests
        if jir_action == jir.APPROVED_INC_GRADES:
            grading.task_journal_status_to_LMS.delay(jir.target.pk)

        jir.save()

        return response.success(description=jir.get_update_response())
