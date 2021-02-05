"""
timeline.py.

Useful timeline functions.
"""
from django.utils import timezone

from VLE.models import Entry, Node, Template
from VLE.serializers import EntrySerializer, FileSerializer, TemplateSerializer


def get_nodes(journal, author=None):
    """Convert a journal to a list of node dictionaries.

    First sorts the nodes on date, then attempts to add an
    add-node if the user can add to the journal, the subsequent
    progress node is in the future and maximally one.
    """
    can_add = journal.can_add(author)

    node_qry = journal.get_sorted_nodes().select_related(
        'preset__forced_template',
    ).prefetch_related(
        'preset__attached_files',
    )

    node_list = []
    for node in node_qry:
        # Add an add node to the timeline before the first progress goal with a deadline in the future.
        # NOTE: Order is relevant
        if node.is_progress:
            is_future = (node.preset.due_date - timezone.now()).total_seconds() > 0
            if can_add and is_future:
                add_node = get_add_node(journal)
                if add_node:
                    node_list.append(add_node)
                can_add = False

            node_list.append(get_progress(journal, node))
        elif node.is_entry:
            node_list.append(get_entry_node(journal, node, author))
        elif node.is_deadline:
            node_list.append(get_deadline(journal, node, author))

    if can_add and not journal.assignment.is_locked():
        add_node = get_add_node(journal)
        if add_node:
            node_list.append(add_node)

    return node_list


# TODO: Make serializers for these functions as well (if possible)
def get_add_node(journal):
    """
    Creates a dictionary representing an 'add node' for the respective journal
    """
    return {
        'type': Node.ADDNODE,
        'nID': -1,
        'templates': TemplateSerializer(
            TemplateSerializer.setup_eager_loading(
                journal.assignment.format.template_set.filter(
                    archived=False,
                    preset_only=False
                ).order_by(
                    'name'
                )
            ),
            many=True
        ).data
    }


def get_entry_node(journal, node, user):
    entry_data = EntrySerializer(
        EntrySerializer.setup_eager_loading(Entry.objects.filter(node=node))[0],
        context={'user': user}
    ).data if node.entry else None

    return {
        'type': node.type,
        'nID': node.id,
        'jID': journal.pk,
        'entry': entry_data,
    } if node else None


def get_deadline(journal, node, user):
    """Convert entrydeadline to a dictionary."""
    if not node:
        return None

    entry_data = EntrySerializer(
        EntrySerializer.setup_eager_loading(Entry.objects.filter(node=node)).first(),
        context={'user': user}
    ).data if node.entry else None

    node_data = {
        'type': node.type,
        'nID': node.id,
        'jID': journal.pk,
        'entry': entry_data,
        'deleted_preset': node.preset is None
    }

    if not node.preset:
        return node_data

    node_data.update({
        'display_name': node.preset.display_name,
        # NOTE: 'template' duplicate serialization, Entry also serializes its template.
        # Is it needed to serialize the template, if an Entry is present?
        'template': TemplateSerializer(
            TemplateSerializer.setup_eager_loading(Template.objects.filter(pk=node.preset.forced_template_id)).get(),
            context={'user': user},
        ).data,
        'attached_files': FileSerializer(node.preset.attached_files, many=True).data,
        'description': node.preset.description,
        'unlock_date': node.preset.unlock_date,
        'due_date': node.preset.due_date,
        'lock_date': node.preset.lock_date,
    })

    return node_data


def get_progress(journal, node):
    """Convert progress node to dictionary."""
    return {
        'display_name': node.preset.display_name,
        'description': node.preset.description,
        'type': node.type,
        'nID': node.id,
        'jID': journal.pk,
        'due_date': node.preset.due_date,
        'target': node.preset.target,
        'attached_files': FileSerializer(node.preset.attached_files, many=True).data
    } if node else None
