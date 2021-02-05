from VLE.models import PresetNode, Template, TemplateCategoryLink


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


def update_categories_of_template_chain(data, template):
    """
    Updates the categories of the full template chain to those provided in data

    Template can be archived or not, regardless whether the categories are updated. Simply always set the categories
    for the created/updated template.

    Since we sync all template categories across a chain, we can use any older template to evaluate the previous
    category state, and use that to more efficiently update the categories across the template chain.
    """
    category_ids = set([category['id'] for category in data['categories']])

    template.categories.set(category_ids)

    rest_of_template_chain = template.chain.template_set.exclude(pk=template.pk)
    older_template = rest_of_template_chain.first()

    if older_template:
        existing_category_ids = set(older_template.categories.values_list('pk', flat=True))

        ids_to_create = category_ids - existing_category_ids
        ids_to_delete = existing_category_ids - category_ids

        TemplateCategoryLink.objects.filter(template__in=rest_of_template_chain, category__in=ids_to_delete).delete()

        template_category_links = [
            TemplateCategoryLink(
                category_id=category_id,
                template=template,
            )
            for category_id in ids_to_create
            for template in rest_of_template_chain
        ]
        TemplateCategoryLink.objects.bulk_create(template_category_links)


def handle_template_update(data, current_template):
    updated_template = current_template

    if _should_be_archived(current_template, data):
        updated_template = Template.objects.create_template_and_fields_from_data(
            data=data,
            format=current_template.format,
            archived_template=current_template,
        )

        PresetNode.objects.filter(forced_template=current_template).update(forced_template=updated_template)

        if current_template.can_be_deleted():
            current_template.delete()
        else:
            current_template.archived = True
            current_template.save()

    update_categories_of_template_chain(data, updated_template)

    return updated_template
