"""
Entry utilities.

A library with utilities related to entries.
"""
import VLE.timeline as timeline
import VLE.utils.generic_utils as utils
import VLE.validators as validators
from VLE import factory
from VLE.models import Field, FileContext, Node
from VLE.utils import file_handling
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


def create_entry_content(content_dict, entry, user):
    try:
        files_to_establish = []
        for field_id, content in content_dict.items():
            field = Field.objects.get(pk=field_id)
            if content is not None and field.type == field.FILE:
                content, = utils.required_typed_params(content, (str, 'id'))

            created_content = factory.make_content(entry, content, field)

            if field.type == field.FILE:
                if field.required and not content:
                    raise FileContext.DoesNotExist
                if content:
                    files_to_establish.append(
                        (FileContext.objects.get(pk=int(content)), created_content))

            # Establish all files in the rich text editor
            if field.type == Field.RICH_TEXT:
                files_to_establish += [
                    (f, created_content) for f in file_handling.get_temp_files_from_rich_text(content)]

    # If anything fails during creation of the entry, delete the entry
    except Exception as e:
        entry.delete()

        # If it is a file issue, raise with propper response, else respond with the exception that was raised
        if type(e) == FileContext.DoesNotExist:
            raise VLEBadRequest('One of your files was not correctly uploaded, please try again.')
        else:
            raise e

    for (fc, created_content) in files_to_establish:
        if fc.is_temp:
            file_handling.establish_file(
                author=user,
                file_context=fc,
                content=created_content,
                in_rich_text=created_content.field.type == Field.RICH_TEXT
            )
