# Generated by Django 2.2.10 on 2021-02-08 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0077_move_description_text_fields_to_blank_over_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignment',
            name='points_possible',
            field=models.FloatField(default=10, verbose_name='points_possible'),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.CheckConstraint(check=models.Q(points_possible__gte=0.0), name='points_possible_gte_0'),
        ),
    ]