# Generated by Django 2.2.8 on 2020-04-19 12:38

import django.contrib.postgres.fields
from django.conf import settings
from django.db import migrations, models
from django.db.models import Sum


def update_journal_with_computed_vars(apps, schema_editor):
    Journal = apps.get_model('VLE', 'Journal')
    Group = apps.get_model('VLE', 'Group')

    for j in Journal.all_objects.all():
        j.groups = list(Group.objects.filter(participation__user__in=j.authors.values('user'))
                        .values_list('pk', flat=True).distinct())
        j.save()


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0060_compute_journal_groups'),
        ('computedfields', '0002_contributingmodelsmodel'),
    ]

    operations = [
        migrations.RunPython(update_journal_with_computed_vars, lambda apps, schema_editor: None),
    ]
