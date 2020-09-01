"""
node.py.

In this file are all the node api requests.
"""
import VLE.timeline as timeline
import VLE.utils.generic_utils as utils
import VLE.utils.responses as response
from rest_framework import viewsets
from VLE.models import Journal


class NodeView(viewsets.ModelViewSet):
    """Node view.

    This class creates the following api paths:
    GET /nodes/ -- gets all the nodes
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
        On success:
            success -- with the node data

        """
        journal_id, = utils.required_typed_params(request.query_params, (int, 'journal_id'))
        journal = Journal.objects.get(pk=journal_id)

        request.user.check_can_view(journal)

        return response.success({'nodes': timeline.get_nodes(journal, request.user)})
