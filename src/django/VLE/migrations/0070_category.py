# Generated by Django 2.2.10 on 2020-12-15 17:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0069_remove_journal_computed_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('name', models.TextField()),
                ('description', models.TextField(null=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='VLE.Assignment')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='template',
            name='locked_categories',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='TemplateCategoryLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='VLE.Category')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='VLE.Template')),
            ],
            options={
                'unique_together': {('template', 'category')},
            },
        ),
        migrations.CreateModel(
            name='EntryCategoryLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='VLE.Category')),
                ('entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='VLE.Entry')),
            ],
            options={
                'unique_together': {('entry', 'category')},
            },
        ),
        migrations.AddField(
            model_name='category',
            name='templates',
            field=models.ManyToManyField(related_name='categories', through='VLE.TemplateCategoryLink', to='VLE.Template'),
        ),
        migrations.AddField(
            model_name='entry',
            name='categories',
            field=models.ManyToManyField(related_name='entries', through='VLE.EntryCategoryLink', to='VLE.Category'),
        ),
        migrations.AddField(
            model_name='filecontext',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.Category'),
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.CheckConstraint(check=models.Q(_negated=True, name=''), name='non_empty_name'),
        ),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('name', 'assignment')},
        ),
    ]
