from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0053_entry_last_edited_auto_now_add'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='node',
            unique_together={('preset', 'journal')},
        ),
    ]
