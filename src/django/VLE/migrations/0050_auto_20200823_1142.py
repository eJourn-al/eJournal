# Generated by Django 2.2.10 on 2020-08-23 11:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0049_auto_20200822_2128'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='enddate',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='course',
            name='startdate',
            field=models.DateTimeField(null=True),
        ),
    ]
