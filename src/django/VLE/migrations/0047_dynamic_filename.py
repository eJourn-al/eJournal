from django.db import migrations, models


def convert_to_dynamic_file_types(apps, schema_editor):
    Field = apps.get_model('VLE', 'Field')
    Field.objects.filter(type='i').update(
        options='bmp, gif, ico, cur, jpg, jpeg, jfif, pjpeg, pjp, png, svg',
        type='f'
    )
    Field.objects.filter(type='p').update(
        options='pdf',
        type='f'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0046_compute_journal2'),
    ]

    operations = [
        migrations.RunPython(
            convert_to_dynamic_file_types, lambda apps, schema_editor: None
        ),
        migrations.AlterField(
            model_name='field',
            name='type',
            field=models.TextField(choices=[('t', 'text'), ('rt', 'rich text'), ('f', 'file'), ('v', 'vid'), ('u', 'url'), ('d', 'date'), ('dt', 'datetime'), ('s', 'selection')], default='t', max_length=4),
        ),
    ]
