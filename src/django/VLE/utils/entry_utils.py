"""
Entry utilities.

A library with utilities related to entries.
"""
import VLE.timeline as timeline
import VLE.validators as validators
from VLE import factory
from VLE.models import Field, Node
from VLE.utils.error_handling import VLEBadRequest, VLEMissingRequiredField


def get_node_index(journal, node, user):
    for i, result_node in enumerate(timeline.get_nodes(journal, user)):
        if result_node['nID'] == node.id:
            return i


def check_fields(template, content_dict):
    """Check if the supplied content list is a valid for the given template"""
    received_ids = []

    # Check if all the content is valid
    for field_id, content in content_dict.items():
        if content is not None and content != '':
            # Content dict comes from JS object (which has only string accessors), but field IDs are ints.
            received_ids.append(int(field_id))
            try:
                field = Field.objects.get(pk=field_id, template=template)
            except Field.DoesNotExist:
                raise VLEBadRequest('Passed field is not from template.')
            validators.validate_entry_content(content, field)

    # Check for missing required fields
    required_fields = Field.objects.filter(template=template, required=True)
    for field in required_fields:
        if field.id not in received_ids:
            raise VLEMissingRequiredField(field)


def add_entry_to_node(node, template, author):
    if not (node.preset and node.preset.forced_template == template):
        raise VLEBadRequest('Invalid template for preset node.')

    if node.type != Node.ENTRYDEADLINE:
        raise VLEBadRequest('Passed node is not an EntryDeadline node.')

    if node.entry:
        raise VLEBadRequest('Passed node already contains an entry.')

    if node.preset.is_locked():
        raise VLEBadRequest('The lock date for this node has passed.')

    entry = factory.make_entry(template, author, node)
    node.entry = entry
    node.save()
    return entry
