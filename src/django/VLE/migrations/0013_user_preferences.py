# Generated by Django 2.1.2 on 2019-01-26 16:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_user_preferences(apps, schema_editor):
    User = apps.get_model('VLE', 'User')
    Preferences = apps.get_model('VLE', 'Preferences')
    for user in User.objects.all():
        Preferences.objects.create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0012_user_full_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='comment_notifications',
        ),
        migrations.RemoveField(
            model_name='user',
            name='grade_notifications',
        ),
        migrations.CreateModel(
            name='Preferences',
            fields=[
                ('show_format_tutorial', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, serialize=False, primary_key=True)),
                ('comment_notifications', models.BooleanField(default=True)),
                ('grade_notifications', models.BooleanField(default=True)),
            ],
        ),
        migrations.RunPython(
            populate_user_preferences,
        ),
    ]
