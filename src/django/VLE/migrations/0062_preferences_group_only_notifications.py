# Generated by Django 2.2.10 on 2020-09-14 22:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0061_compute_journal_groups_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='preferences',
            name='group_only_notifications',
            field=models.BooleanField(default=True),
        ),
    ]
