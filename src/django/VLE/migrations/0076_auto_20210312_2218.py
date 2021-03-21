# Generated by Django 2.2.19 on 2021-03-12 22:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0075_auto_20210312_2154'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='lti_id',
            new_name='lms_id',
        ),
        migrations.AlterUniqueTogether(
            name='group',
            unique_together={('lms_id', 'course')},
        ),
    ]
