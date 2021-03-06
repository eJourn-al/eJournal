# Generated by Django 2.2.8 on 2020-04-12 13:43

from django.conf import settings
from django.db import migrations, models


def remove_canvas_default_image(apps, schema_editor):
    User = apps.get_model('VLE', 'User')
    Instance = apps.get_model('VLE', 'Instance')
    User.objects.filter(profile_picture__icontains='images/messages/avatar-50.png').update(
        profile_picture=settings.DEFAULT_PROFILE_PICTURE
    )


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0063_notification_jir'),
    ]

    operations = [
        migrations.RunPython(remove_canvas_default_image, lambda apps, schema_editor: None),
    ]
