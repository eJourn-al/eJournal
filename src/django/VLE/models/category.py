from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import CheckConstraint, Q

import VLE.utils.file_handling as file_handling

from .base import CreateUpdateModel
from .template import Template


class CategoryQuerySet(models.QuerySet):
    def create(self, templates=None, *args, **kwargs):
        """Creates a category, setting templates in the same transaction"""
        with transaction.atomic():
            category = super().create(*args, **kwargs)

            if templates is not None:
                category.templates.set(Template.objects.full_chain(templates))

            file_handling.establish_rich_text(author=category.author, rich_text=category.description, category=category)

            return category


class Category(CreateUpdateModel):
    """
    Grouping of multiple templates contributing to a specific category / skill
    """
    class Meta:
        ordering = ['name']
        constraints = [
            CheckConstraint(check=~Q(name=''), name='non_empty_name'),
            CheckConstraint(check=Q(color__regex=r'^#(?:[0-9a-fA-F]{1,2}){3}$'), name='non_valid_rgb_color_code'),
        ]
        unique_together = (
            ('name', 'assignment'),
        )

    objects = models.Manager.from_queryset(CategoryQuerySet)()

    name = models.TextField()
    description = models.TextField(
        blank=True,
    )
    color = models.CharField(
        max_length=9
    )
    author = models.ForeignKey(
        'User',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    assignment = models.ForeignKey(
        'assignment',
        related_name='categories',
        on_delete=models.CASCADE,
    )
    templates = models.ManyToManyField(
        'Template',
        related_name='categories',
        through='TemplateCategoryLink',
        through_fields=('category', 'template'),
    )

    @staticmethod
    def validate_category_data(name, assignment, category=None):
        equal_name = Category.objects.filter(name=name, assignment=assignment)

        if category:
            equal_name = equal_name.exclude(pk=category.pk)

        if name == '':
            raise ValidationError('Please provide a non empty name.')
        if equal_name.exists():
            raise ValidationError('Please provide a unqiue category name.')


class TemplateCategoryLink(CreateUpdateModel):
    """
    Explicit M2M table, linking Templates to Categories.
    """
    class Meta:
        unique_together = ('template', 'category')

    template = models.ForeignKey(
        'template',
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        'category',
        on_delete=models.CASCADE,
    )


class EntryCategoryLink(CreateUpdateModel):
    """Explicit M2M table, linking Entries to Categories."""
    class Meta:
        unique_together = ('entry', 'category')

    entry = models.ForeignKey(
        'entry',
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        'category',
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        'user',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
