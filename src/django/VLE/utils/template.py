from VLE.models import PresetNode, Template


def _template_concrete_fields_updated(template, data):
    check_fields = [
        'name',
        'preset_only',
        'fixed_categories',
    ]

    return any(getattr(template, f) != data[f] for f in check_fields)


def _field_concrete_fields_updated(field, data):
    check_fields = [
        'type',
        'title',
        'location',
        'required',
        'description',
        'options',
    ]

    return any(getattr(field, f) != data[f] for f in check_fields)


def _field_set_updated(template, data):
    data['field_set'].sort(key=lambda f: f['location'])
    field_set = template.field_set.order_by('location')

    return (
        len(field_set) != len(data['field_set'])
        or any(_field_concrete_fields_updated(field, data) for field, data in zip(field_set, data['field_set']))
    )


def _should_be_archived(template, data):
    """
    A template should also be archived when any of its concrete fields change.

    This is done for consistency, e.g. when template name is updated it could
    no longer matched the entry created using an older version.
    """
    assert data['id'], 'Template can only be updated if it was already created'

    return (
        _template_concrete_fields_updated(template, data)
        or _field_set_updated(template, data)
    )


def handle_template_update(data, format, new_ids):
    current_template = Template.objects.get(pk=data['id'])

    if _should_be_archived(current_template, data):
        current_template.archived = True
        current_template.save()

        new_template = Template.objects.create_template_and_fields_from_data(data, format, current_template)
        new_ids[data['id']] = new_template.pk

        PresetNode.objects.filter(forced_template=current_template).update(forced_template=new_template)

        if current_template.can_be_deleted():
            current_template.delete()


def update_templates(format, templates_data):
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

    for data in templates_data:
        if data['id'] >= 0:
            handle_template_update(data, format, new_ids)
        else:  # Unknown (newly created) template.
            new_template = Template.objects.create_template_and_fields_from_data(data, format)
            new_ids[data['id']] = new_template.pk

    return new_ids


def delete_or_archive_templates(templates_data):
    template_ids = [template['id'] for template in templates_data]

    Template.objects.unused().filter(pk__in=template_ids).delete()
    Template.objects.filter(pk__in=template_ids).update(archived=True)
