# Generated by Django 2.2.10 on 2021-02-01 18:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0074_order_template_by_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='presetnode',
            name='forced_template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='VLE.Template'),
        ),
    ]