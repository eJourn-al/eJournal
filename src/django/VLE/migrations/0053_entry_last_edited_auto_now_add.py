from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0052_content_field_cascade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='last_edited',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
