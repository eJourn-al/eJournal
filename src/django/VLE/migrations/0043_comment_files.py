# Generated by Django 2.2.10 on 2020-05-23 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0042_add_create_and_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='files',
            field=models.ManyToManyField(related_name='comment_files', to='VLE.FileContext'),
        ),
    ]
