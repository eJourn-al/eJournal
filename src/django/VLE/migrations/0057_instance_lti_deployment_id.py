# Generated by Django 2.2.10 on 2020-09-03 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0056_auto_20200903_1607'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='lti_deployment_id',
            field=models.TextField(blank=True, null=True, unique=True),
        ),
    ]
