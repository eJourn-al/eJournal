# Generated by Django 2.1 on 2018-09-29 16:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0002_auto_20180927_1056'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='role',
            name='can_add_course',
        ),
    ]