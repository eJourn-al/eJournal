# Generated by Django 2.2.10 on 2020-08-06 11:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0055_one_content_per_field_and_entry'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeacherEntry',
            fields=[
                ('entry_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='VLE.Entry')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='VLE.Assignment')),
            ],
            options={
                'abstract': False,
            },
            bases=('VLE.entry',),
        ),
        migrations.AddField(
            model_name='teacherentry',
            name='title',
            field=models.TextField(default='BESTONE'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='teacherentry',
            name='show_title_in_timeline',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='entry',
            name='teacher_entry',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.TeacherEntry'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='vle_coupling',
            field=models.TextField(choices=[('Submission needs to be sent to VLE', 'entry_submission'), ('Submission is successfully received by VLE', 'entry_submitted'), ('Grade needs to be sent to VLE', 'grade_submission'), ('Everything is sent to VLE', 'done'), ('Ignore VLE coupling (e.g. for teacher entries)', 'no_link')], default='Submission needs to be sent to VLE'),
        ),
        migrations.AddField(
            model_name='role',
            name='can_post_teacher_entries',
            field=models.BooleanField(default=False),
        ),
    ]