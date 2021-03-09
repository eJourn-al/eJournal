import VLE.utils.generic_utils as generic_utils
from VLE.models import Entry, EntryCategoryLink, PresetNode, Template, TemplateCategoryLink


def _template_concrete_fields_updated(template, data):
    check_fields = [
        'name',
        'preset_only',
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
    A template should also be archived when a change is made to its field, or any of its concrete fields change.

    To choice to archive on its concrete fields is done for consistency, e.g. when template name is updated it could
    no longer matched the entry created using an older version.
    """
    assert data['id'], 'Template can only be updated if it was already created'

    return (
        _template_concrete_fields_updated(template, data)
        or _field_set_updated(template, data)
    )


def update_template_categories_of_template_chain(template, category_ids, existing_category_ids):
    """
    Updates the categories of the full template chain to those provided in data

    Template can be archived or not, regardless whether the categories are updated. Simply always set the categories
    for the created/updated template.

    Since we sync all template categories across a chain, we can use any older template to evaluate the previous
    category state, and use that to more efficiently update the categories across the template chain.
    """
    template.categories.set(category_ids)

    rest_of_template_chain = template.chain.template_set.exclude(pk=template.pk)
    older_template = rest_of_template_chain.first()

    if older_template:
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


def update_entry_categories_using_templates_of_chain(template, new_ids, existing_ids, user):
    """
    Updates the categories of all entries which make use of a template part of the provided template's chain.

    The categories are updated according to the difference between the new and existing ids.

    NOTE: It is possible to override changes made to entry categories by students or staff via this path.
    E.g. by reintroducing a category to a template which a student or TA has removed from an entry in the meanwhile.
    This scenario is sufficiently rare to be considered acceptable.
    """
    entries = Entry.objects.filter(template__chain=template.chain).distinct()

    ids_to_create = new_ids - existing_ids
    ids_to_delete = existing_ids - new_ids

    EntryCategoryLink.objects.filter(entry__in=entries, category__in=ids_to_delete).delete()

    entry_category_links = [
        EntryCategoryLink(
            category_id=category_id,
            entry=entry,
            author=user,
        )
        for category_id in ids_to_create
        for entry in entries
    ]
    EntryCategoryLink.objects.bulk_create(entry_category_links)


def update_template_chain_based_settings(chain, data):
    """
    Updates template settings which hold for the entire template chain.

    Archiving a template part of the chain should have no impact on these settings.
    """
    chain_fields = [
        'allow_custom_categories',
        'default_grade',
    ]

    if any(getattr(chain, f) != data[f] for f in chain_fields):
        chain.allow_custom_categories, = generic_utils.required_typed_params(data, (bool, 'allow_custom_categories'))
        chain.default_grade, = generic_utils.optional_typed_params(data, (float, 'default_grade'))
        chain.save()


def handle_template_update(data, current_template, user):
    data_category_ids = set([category['id'] for category in data['categories']])
    existing_template_category_ids = set(current_template.categories.values_list('pk', flat=True))
    updated_template = current_template

    update_template_chain_based_settings(current_template.chain, data)

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

    if existing_template_category_ids != data_category_ids:
        update_entry_categories_using_templates_of_chain(
            updated_template,
            data_category_ids,
            existing_template_category_ids,
            user,
        )
        update_template_categories_of_template_chain(
            updated_template,
            data_category_ids,
            existing_template_category_ids,
        )

    return updated_template
