"""
timeline.py.

Useful timeline functions.
"""
from django.utils import timezone

from VLE.models import Node
from VLE.serializers import EntrySerializer, TemplateSerializer
from VLE.utils import generic_utils as utils


def get_nodes(journal, author=None):
    """Convert a journal to a list of node dictionaries.

    First sorts the nodes on date, then attempts to add an
    add-node if the user can add to the journal, the subsequent
    progress node is in the future and maximally one.
    """
    can_add = author and author not in journal.authors.all() and \
        author.has_permission('can_have_journal', journal.assignment) and not len(journal.needs_lti_link) > 0

    node_list = []
    for node in utils.get_sorted_nodes(journal):
        # If there is a progress node upcoming, and there are stackable entries before the deadline
        # add an ADDNODE
        if node.type == Node.PROGRESS:
            is_future = (node.preset.due_date - timezone.now()).total_seconds() > 0
            if can_add and is_future:
                add_node = get_add_node(journal)
                if add_node:
                    node_list.append(add_node)
                can_add = False

        if node.type == Node.ENTRY:
            node_list.append(get_entry_node(node, author))
        elif node.type == Node.ENTRYDEADLINE:
            node_list.append(get_deadline(node, author))
        elif node.type == Node.PROGRESS:
            node_list.append(get_progress(node))

    if can_add and not journal.assignment.is_locked():
        add_node = get_add_node(journal)
        if add_node:
            node_list.append(add_node)

    return node_list


# TODO: Make serializers for these functions as well (if possible)
def get_add_node(journal):
    """Convert a add_node to a dictionary."""
    if not journal or journal.assignment.format.template_set.filter(archived=False, preset_only=False).count() == 0:
        return None
    return {
        'type': Node.ADDNODE,
        'nID': -1,
        'templates': TemplateSerializer(
            journal.assignment.format.template_set.filter(archived=False, preset_only=False).order_by('name'),
            many=True).data
    }


def get_entry_node(node, user):
    return {
        'type': node.type,
        'nID': node.id,
        'jID': node.journal.id,
        'entry': EntrySerializer(node.entry, context={'user': user}).data if node.entry else None,
    } if node else None


def get_deadline(node, user):
    """Convert entrydeadline to a dictionary."""
    return {
        'description': node.preset.description,
        'type': node.type,
        'nID': node.id,
        'jID': node.journal.id,
        'unlock_date': node.preset.unlock_date,
        'due_date': node.preset.due_date,
        'lock_date': node.preset.lock_date,
        'template': TemplateSerializer(node.preset.forced_template).data,
        'entry': EntrySerializer(node.entry, context={'user': user}).data if node.entry else None,
    } if node else None


def get_progress(node):
    """Convert progress node to dictionary."""
    return {
        'description': node.preset.description,
        'type': node.type,
        'nID': node.id,
        'jID': node.journal.id,
        'due_date': node.preset.due_date,
        'target': node.preset.target,
    } if node else None
