"""
Utilities.

A library with useful functions.
"""
import base64
import re
from mimetypes import guess_extension

from django.core.files.base import ContentFile
from django.db.models import Case, When

import VLE.factory as factory
from VLE.models import Entry, Journal, Node, Notification, PresetNode, Template
from VLE.utils.error_handling import VLEBadRequest, VLEMissingRequiredKey, VLEParamWrongType


# START: API-POST functions
def required_params(post, *keys):
    """Get required post parameters, throwing KeyError if not present."""
    if keys and not post:
        raise VLEMissingRequiredKey(keys)

    result = []
    for key in keys:
        try:
            if post[key] == '':
                VLEMissingRequiredKey(key)
            result.append(post[key])
        except KeyError:
            raise VLEMissingRequiredKey(key)

    return result


def optional_params(post, *keys):
    """Get optional post parameters, filling them as None if not present."""
    if keys and not post:
        return [None] * len(keys)

    result = []
    for key in keys:
        if key in post and post[key] != '':
            result.append(post[key])
        else:
            result.append(None)
    return result


def required_typed_params(post, *keys):
    if keys and not post:
        raise VLEMissingRequiredKey([key[1] for key in keys])

    result = []
    for func, key in keys:
        try:
            if post[key] == '':
                VLEMissingRequiredKey(key)
            if isinstance(post[key], list):
                result.append([func(elem) for elem in post[key]])
            elif post[key] is not None:
                result.append(func(post[key]))
            else:
                result.append(None)
        except ValueError as err:
            raise VLEParamWrongType(err)
        except KeyError:
            raise VLEMissingRequiredKey(key)

    return result


def optional_typed_params(post, *keys):
    if keys and not post:
        return [None] * len(keys)

    result = []
    for func, key in keys:
        if key and key in post and post[key] != '':
            try:
                if post[key] is not None:
                    result.append(func(post[key]))
                else:
                    result.append(None)
            except ValueError as err:
                raise VLEParamWrongType(err)
        else:
            result.append(None)

    return result
# END: API-POST functions


def get_sorted_nodes(journal):
    """Get sorted nodes.

    Get all the nodes of a journal in sorted order.
    Order is default by due_date.
    """
    return journal.node_set.annotate(
        sort_due_date=Case(
            When(type=Node.ENTRY, then='entry__creation_date'),
            default='preset__due_date')
    ).order_by('sort_due_date')


def update_templates(format, templates):
    """Update or create templates for a format.

    - format: the format that is being edited
    - templates: the list of temlates that should be updated or created

    Since existing entries that use a template should remain untouched a copy
    of the current template is saved in an archived state before processing any
    changes. The distinction between existing and new templates occurs based on
    the id: newly created templates are assigned a negative id in the format
    editor.
    """
    new_ids = {}
    for template in templates:
        if template['id'] > 0:  # Template already exists.
            old_template = Template.objects.get(pk=template['id'])

            # Archive the previous version of the template if changes were made.
            if (old_template.name != template['name'] or old_template.field_set.count() !=
                    len(template['field_set']) or old_template.preset_only != template['preset_only']):
                old_template.archived = True
            else:
                for old_field, new_field in zip(sorted(old_template.field_set.all(), key=lambda f: f.location),
                                                sorted(template['field_set'], key=lambda f: f['location'])):
                    if (old_field.type != new_field['type'] or old_field.title != new_field['title'] or
                            old_field.location != new_field['location'] or old_field.required !=
                            new_field['required'] or old_field.description != new_field['description'] or
                            old_field.options != new_field['options']):
                        old_template.archived = True
                        break

            if old_template.archived:
                old_template.save()
                new_template = parse_template(template, format)
                new_ids[template['id']] = new_template.pk

                # Update preset nodes to use the new template.
                presets = PresetNode.objects.filter(forced_template=old_template).all()
                for preset in presets:
                    preset.forced_template = new_template
                    preset.save()

                if len(presets) == 0 and not Entry.objects.filter(template=old_template).exists():
                    old_template.delete()

        else:  # Unknown (newly created) template.
            new_template = parse_template(template, format)
            new_ids[template['id']] = new_template.pk

    return new_ids


def parse_template(template_dict, format):
    """Parse a new template according to the passed JSON-serialized template."""
    name = template_dict['name']
    preset_only = template_dict['preset_only']
    fields = template_dict['field_set']

    template = factory.make_entry_template(name, format, preset_only)

    for field in fields:
        type = field['type']
        title = field['title']
        location = field['location']
        required = field['required']
        description = field['description']
        options = field['options']

        factory.make_field(template, title, location, type, required, description, options)

    template.save()
    return template


def update_journals(journals, preset):
    """Create the preset node in all relevant journals.

    Arguments:
    journals -- the journals to update.
    preset -- the preset node to add to the journals.
    """
    for journal in journals:
        node = factory.make_node(journal, None, preset.type, preset)
        for author in journal.authors.all():
            if author.user.can_view(journal):
                Notification.objects.create(
                    type=Notification.NEW_NODE,
                    user=author.user,
                    node=node,
                )


def update_presets(assignment, presets, new_ids):
    """Update preset nodes in the assignment according to the passed list.

    Arguments:
    assignment -- the assignment to update the presets in.
    presets -- a list of JSON-serialized presets.
    """
    format = assignment.format
    for preset in presets:
        id, template = required_typed_params(preset, (int, 'id'), (dict, 'template'))
        target, unlock_date, lock_date = optional_typed_params(
            preset, (float, 'target'), (str, 'unlock_date'), (str, 'lock_date'))
        type, description, due_date = required_params(
            preset, 'type', 'description', 'due_date')

        if id > 0:
            preset_node = PresetNode.objects.get(pk=id)
        else:
            preset_node = PresetNode(format=format)
            preset_node.type = type

        preset_node.description = description
        preset_node.unlock_date = unlock_date if unlock_date else None
        preset_node.due_date = due_date
        preset_node.lock_date = lock_date if lock_date else None

        if preset_node.type == Node.PROGRESS:
            if target > 0 and target <= assignment.points_possible:
                preset_node.target = target
            else:
                raise VLEBadRequest(
                    'Progress goal needs to be between 0 and the maximum amount for the assignment: {}'
                    .format(assignment.points_possible))
        elif preset_node.type == Node.ENTRYDEADLINE:
            if template['id'] in new_ids:
                preset_node.forced_template = Template.objects.get(pk=new_ids[template['id']])
            else:
                preset_node.forced_template = Template.objects.get(pk=template['id'])
        preset_node.save()
        if id < 0:
            update_journals(Journal.all_objects.filter(assignment=assignment), preset_node)


def delete_presets(presets):
    """Deletes all presets in remove_presets from presets. """
    ids = []
    for preset in presets:
        ids.append(preset['id'])

    for id in ids:
        Node.objects.filter(preset=id, entry__isnull=True).delete()
    PresetNode.objects.filter(pk__in=ids).delete()


def archive_templates(templates):
    """Puts all templates in an archived stated. This means that they cannot be
    used for new entries anymore."""
    ids = []
    for template in templates:
        ids.append(template['id'])

    Template.objects.filter(pk__in=ids).update(archived=True)


def base64ToContentFile(string, filename):
    matches = re.findall(r'data:(.*);base64,(.*)', string)[0]
    mimetype = matches[0]
    extension = guess_extension(mimetype)
    return ContentFile(base64.b64decode(matches[1]), name='{}{}'.format(filename, extension))
