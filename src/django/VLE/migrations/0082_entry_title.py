# Generated by Django 2.2.10 on 2021-02-23 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0081_allow_custom_entry_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='title',
            field=models.TextField(null=True, blank=True),
        ),
    ]
