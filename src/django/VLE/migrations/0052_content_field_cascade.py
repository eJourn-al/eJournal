import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0051_journal_import_request'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='field',
            field=models.ForeignKey(default=-1, on_delete=django.db.models.deletion.CASCADE, to='VLE.Field'),
            preserve_default=False,
        ),
    ]
