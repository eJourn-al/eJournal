# Generated by Django 2.2.10 on 2020-07-10 19:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0048_notifications'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preferences',
            name='upcoming_deadline_notifications',
        ),
    ]
