"""
node.py.

In this file are all the node api requests.
"""
from datetime import datetime

from rest_framework import viewsets

import VLE.timeline as timeline
import VLE.utils.generic_utils as utils
import VLE.views.responses as response
from VLE.models import Journal


class NodeView(viewsets.ModelViewSet):
    """Node view.

    This class creates the following api paths:
    GET /nodes/ -- gets all the nodes

    TODO:
    POST /nodes/ -- create a new node
    GET /nodes/<pk> -- gets a specific node
    PATCH /nodes/<pk> -- partially update a node
    DEL /nodes/<pk> -- delete a node
    """

    def list(self, request):
        """Get all nodes contained within a journal.

        Arguments:
        request -- request data
            journal_id -- journal ID

        Returns:
        On failure:
            unauthorized -- when the user is not logged in
            not found -- when the course does not exist
            forbidden -- when the user is not part of the course
        On succes:
            success -- with the node data

        """
        if not request.user.is_authenticated:
            return response.unauthorized()

        journal_id, = utils.required_typed_params(request.query_params, (int, 'journal_id'))

        journal = Journal.objects.get(pk=journal_id)

        if request.user != journal.user:
            request.user.check_permission('can_view_assignment_journals', journal.assignment)

        if ((journal.assignment.unlock_date and journal.assignment.unlock_date > datetime.now()) or
            (journal.assignment.lock_date and journal.assignment.lock_date < datetime.now())) and \
           not request.user.has_permission('can_view_assignment_journals', journal.assignment):
            return response.forbidden('The assignment is locked and unavailable for students.')

        return response.success({'nodes': timeline.get_nodes(journal, request.user)})
