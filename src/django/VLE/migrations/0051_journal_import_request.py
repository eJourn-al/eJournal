import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0050_no_submission_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='JournalImportRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('state', models.CharField(choices=[('PEN', 'Pending'), ('DEC', 'Declined'), ('AIG', 'Approved including grades'), ('AEG', 'Approved excluding grades'), ('AWGZ', 'Approved with all grades set to zero'), ('EWP', 'Empty when processed')], default='PEN', max_length=4)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='jir_author', to=settings.AUTH_USER_MODEL)),
                ('processor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='jir_processor', to=settings.AUTH_USER_MODEL)),
                ('source', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='import_request_sources', to='VLE.Journal')),
                ('target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='import_request_targets', to='VLE.Journal')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='entry',
            name='jir',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to='VLE.JournalImportRequest'),
        ),
        migrations.AddField(
            model_name='role',
            name='can_manage_journal_import_requests',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='journal',
            name='import_requests',
            field=models.IntegerField(editable=False, null=True),
        ),
    ]
