from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import CheckConstraint, Q, QuerySet
from django.dispatch import receiver

import VLE.utils.file_handling as file_handling
import VLE.utils.generic_utils as generic_utils
from VLE.utils.error_handling import VLEProgrammingError

from .base import CreateUpdateModel
from .content import Content
from .field import Field


class TemplateChain(CreateUpdateModel):
    """
    Identifies multiple templates which were updated as belonging to the same template

    Any fields hold for the entire template chain
    """
    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(default_grade__gte=0) | Q(default_grade__isnull=True),
                name='default_grade_gte_0',
            ),
        ]

    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )

    allow_custom_categories = models.BooleanField(
        default=False,
    )

    allow_custom_title = models.BooleanField(
        default=True,
    )

    title_description = models.TextField(
        blank=True,
        null=True,
    )

    default_grade = models.FloatField(
        blank=True,
        null=True,
    )


class TemplateQuerySet(models.QuerySet):
    def create(self, format, *args, **kwargs):
        """Creates a template and starts a new chain if not provided in the same transaction."""
        with transaction.atomic():
            allow_custom_categories = kwargs.pop('allow_custom_categories', False)
            allow_custom_title = kwargs.pop('allow_custom_title', True)
            title_description = kwargs.pop('title_description', None)
            default_grade = kwargs.pop('default_grade', None)
            if default_grade == '':
                default_grade = None

            if not kwargs.get('chain', False):
                kwargs['chain'] = TemplateChain.objects.create(
                    format=format,
                    allow_custom_categories=allow_custom_categories,
                    allow_custom_title=allow_custom_title,
                    title_description=title_description,
                    default_grade=default_grade,
                )

            return super().create(*args, **kwargs, format=format)

    def create_template_and_fields_from_data(
        self,
        data,
        format,
        archived_template=None,
        template_import=False,
        author=None,
    ):
        category_ids = [category['id'] for category in data['categories']]

        with transaction.atomic():
            template = Template.objects.create(
                name=data['name'],
                format=format,
                preset_only=data['preset_only'],
                allow_custom_categories=data['allow_custom_categories'],
                allow_custom_title=data['allow_custom_title'],
                title_description=data['title_description'],
                default_grade=data['default_grade'],
                chain=archived_template.chain if archived_template else False,
            )

            if not template_import:
                template.categories.set(category_ids)

            fields = [
                Field(
                    template=template,
                    type=field['type'],
                    title=field['title'],
                    location=field['location'],
                    required=field['required'],
                    description=field['description'],
                    options=field['options'],
                )
                for field in data['field_set']
            ]

            if template_import:
                if not author:
                    raise VLEProgrammingError('Author is required when importing a template')

                template.chain.title_description = file_handling.copy_assignment_related_rt_files(
                    template.chain.title_description,
                    author,
                    assignment=format.assignment,
                )
                template.chain.save()

                fields_with_copied_rt_description_files = []
                for field in fields:
                    field.description = file_handling.copy_assignment_related_rt_files(
                        field.description,
                        author,
                        assignment=format.assignment,
                    )
                    fields_with_copied_rt_description_files.append(field)
                fields = fields_with_copied_rt_description_files

            fields = Field.objects.bulk_create(fields)

        return template

    def unused(self):
        return self.filter(
            presetnode__isnull=True,
            entry__isnull=True,
        ).distinct()

    def full_chain(self, templates):
        if isinstance(templates, list) or isinstance(templates, QuerySet) or isinstance(templates, set):
            return self.filter(chain__template__in=templates).distinct()
        return self.filter(chain__template=templates).distinct()


class Template(CreateUpdateModel):
    """Template.

    A template for an Entry.
    """
    class Meta:
        constraints = [
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
        ]
        ordering = [
            'name',
        ]

    objects = models.Manager.from_queryset(TemplateQuerySet)()

    name = models.TextField()

    format = models.ForeignKey(
        'Format',
        on_delete=models.CASCADE
    )

    preset_only = models.BooleanField(
        default=False
    )

    archived = models.BooleanField(
        default=False
    )

    chain = models.ForeignKey(
        'TemplateChain',
        on_delete=models.CASCADE,
    )

    @staticmethod
    def validate(data, assignment, old=None):
        def validate_concrete_fields():
            name, = generic_utils.required_typed_params(data, (str, 'name'))
            data['name'] = name.strip()

            if old:
                assert old.format.assignment == assignment

            if (
                not old and assignment.format.template_set.filter(archived=False, name=name).exists()
                or old and assignment.format.template_set.filter(archived=False, name=name).exclude(pk=old.pk).exists()
            ):
                raise ValidationError('Please provide a unique template name.')

            if name == '':
                raise ValidationError('Template name cannot be empty.')

        def validate_chain_fields():
            default_grade, = generic_utils.optional_typed_params(data, (float, 'default_grade'))

            if default_grade is not None:
                if default_grade < 0:
                    raise ValidationError('Default grade should be positive.')

        def validate_categories():
            category_data, = generic_utils.required_params(data, 'categories')
            category_ids = set([category['id'] for category in category_data])

            if not category_ids:
                return

            if len(category_ids) != len(category_data):
                raise ValidationError('Duplicate categories provided.')
            if assignment.categories.filter(pk__in=category_ids).count() != len(category_ids):
                raise ValidationError('One or more categories are not part of the assignment.')

        def validate_field_set():
            field_set_data, = generic_utils.required_params(data, 'field_set')
            locations = set()

            for field_data in field_set_data:
                location, = generic_utils.required_typed_params(field_data, (int, 'location'))

                if location in locations:
                    raise ValidationError('Duplicate template field location provided.')
                if location < 0 or location >= len(field_set_data):
                    raise ValidationError('Template field location is out of bounds.')

                locations.add(location)

            if len(locations) == 0:
                raise ValidationError('A template should include one or more fields.')

        validate_concrete_fields()
        validate_chain_fields()
        validate_categories()
        validate_field_set()

    def can_be_deleted(self):
        return not (
            self.presetnode_set.exists()
            or self.entry_set.exists()
        )

    def to_string(self, user=None):
        return "Template"


@receiver(models.signals.pre_delete, sender=Template)
def delete_pending_jirs_on_source_deletion(sender, instance, **kwargs):
    if Content.objects.filter(field__template=instance).exists():
        raise VLEProgrammingError('Content still exists which depends on a template being deleted.')


@receiver(models.signals.post_delete, sender=Template)
def delete_floating_empty_template_chain(sender, instance, **kwargs):
    """Deletes the template's chain if no templates are left."""
    if not instance.chain.template_set.exists():
        instance.chain.delete()
