# Generated by Django 2.2.10 on 2020-08-06 11:49
from django.db import migrations


def set_entry_last_edited_by(apps, schema_editor):
    Entry = apps.get_model('VLE', 'Entry')
    for entry in Entry.objects.all():
        if entry.last_edited_by is None:
            entry.last_edited_by = entry.author
            entry.save()


def set_teacher_can_post_teacher_entries(apps, schema_editor):
    Role = apps.get_model('VLE', 'Role')
    Role.objects.filter(name='Teacher').update(can_post_teacher_entries=True)


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0056_teacher_entry'),
    ]

    operations = [
        migrations.RunPython(set_entry_last_edited_by, lambda apps, schema_editor: None),
        migrations.RunPython(set_teacher_can_post_teacher_entries, lambda apps, schema_editor: None),
    ]
