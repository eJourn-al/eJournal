# Generated by Django 2.2.10 on 2020-10-11 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0064_use_ejournal_default_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='presetnode',
            name='files',
            field=models.ManyToManyField(related_name='preset_node_files', to='VLE.FileContext'),
        ),
    ]
