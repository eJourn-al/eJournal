# Generated by Django 2.2.10 on 2020-12-18 11:29

import django.db.models.deletion
from django.db import migrations, models


def createTemplateChainsForNonArchivedTemplates(apps, schema_editor):
    Template = apps.get_model('VLE', 'Template')
    TemplateChain = apps.get_model('VLE', 'TemplateChain')

    for template in Template.objects.filter(archived=False).select_related('format'):
        chain = TemplateChain.objects.create(format=template.format)
        template.chain = chain
        template.save()


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0070_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemplateChain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('format', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='VLE.Format')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='template',
            name='chain',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.TemplateChain'),
        ),
        migrations.RunPython(createTemplateChainsForNonArchivedTemplates, reverse_code=lambda apps, schema_editor: None),
    ]
