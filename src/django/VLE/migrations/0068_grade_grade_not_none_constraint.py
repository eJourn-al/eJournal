# Generated by Django 2.2.10 on 2020-11-20 08:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0067_user_manager_field_ordering'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grade',
            name='grade',
            field=models.FloatField(editable=False),
        ),
    ]
