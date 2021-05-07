from django.db import migrations, models
from django.db.models import Q


def add_hosts_to_field_options(apps, schema_editor):
    Field = apps.get_model('VLE', 'Field')

    Field.objects.filter(
        Q(options__isnull=True) | Q(options=''),
        type='v',
    ).update(options='y,k')


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0083_preferences_hide_past_deadlines_of_assignments'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='kaltura_url',
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(add_hosts_to_field_options, reverse_code=lambda apps, schema_editor: None),
    ]
