# Generated by Django 2.2.10 on 2020-08-27 09:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0054_one_node_per_preset_and_journal'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='content',
            unique_together={('entry', 'field')},
        ),
    ]
