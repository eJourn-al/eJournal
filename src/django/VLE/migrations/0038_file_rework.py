import base64
import logging
import re
import uuid
from mimetypes import guess_extension

import django.db.models.deletion
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import migrations, models
from django.utils import timezone

import VLE.utils.file_handling
from VLE.utils import file_handling

logger = logging.getLogger(__name__)
base64ImgEmbedded = re.compile(r'<img\s+src=\"(data:image\/[^;]+;base64[^\"]+)\"\s*/>')


class UserFile(models.Model):
    """UserFile.

    UserFile is a file uploaded by the user stored in MEDIA_ROOT/uID/aID/<file>
    - author: The user who uploaded the file.
    - file_name: The name of the file (no parts of the path to the file included).
    - creation_date: The time and date the file was uploaded.
    - content_type: The content type supplied by the user (unvalidated).
    - assignment: The assignment that the UserFile is linked to.
    - node: The node that the UserFile is linked to.
    - entry: The entry that the UserFile is linked to.
    - content: The content that UserFile is linked to.

    Note that deleting the assignment, node or content will also delete the UserFile.
    UserFiles uploaded initially have no node or content set, and are considered temporary until the journal post
    is made and the corresponding node and content are set.
    """
    file = models.FileField(
        null=False,
        upload_to=file_handling.get_path
    )
    file_name = models.TextField(
        null=False
    )
    author = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        null=False
    )
    content_type = models.TextField(
        null=False
    )
    assignment = models.ForeignKey(
        'Assignment',
        on_delete=models.CASCADE,
        null=False
    )
    node = models.ForeignKey(
        'Node',
        on_delete=models.CASCADE,
        null=True
    )
    entry = models.ForeignKey(
        'Entry',
        on_delete=models.CASCADE,
        null=True
    )
    content = models.ForeignKey(
        'Content',
        on_delete=models.CASCADE,
        null=True
    )
    creation_date = models.DateTimeField(editable=False)
    last_edited = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.creation_date = timezone.now()
        self.last_edited = timezone.now()

        return super(UserFile, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.file.delete()
        super(UserFile, self).delete(*args, **kwargs)

    def to_string(self, user=None):
        return "UserFile"


def decode_base64(data, altchars=b'+/'):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    data = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', data)  # normalize
    missing_padding = len(data) % 4
    if missing_padding:
        data += b'='* (4 - missing_padding)
    return base64.b64decode(data, altchars)


# Expects a string containing a single base64 file
def base64ToContentFile(string, filename):
    matches = re.findall(r'data:(.*);base64,(.*)', string)[0]
    mimetype = matches[0]
    extension = guess_extension(mimetype)
    return ContentFile(base64.b64decode(matches[1]), name='{}{}'.format(filename, extension))


def download_url(file, access_id=False):
    if access_id:
        return '{}/files/{}?access_id={}'.format(settings.API_URL, file.pk, file.access_id)
    return '/files/{}/'.format(file.pk)


def fileToEmbdeddedImageLink(file):
    return '<img src="{}"/>'.format(download_url(file, access_id=True))


def convertUserFiles(apps, schema_editor):
    FileContext = apps.get_model('VLE', 'FileContext')
    User = apps.get_model('VLE', 'User')
    Content = apps.get_model('VLE', 'Content')
    Assignment = apps.get_model('VLE', 'Assignment')
    Journal = apps.get_model('VLE', 'Journal')

    # Delete temp files
    UserFile.objects.filter(content=None).delete()

    for f in UserFile.objects.all():
        # Works once per file retrieval
        try:
            content = Content.objects.get(pk=f.content.pk)
            journal = Journal.all_objects.get(pk=content.entry.node.journal.pk)
            assignment = Assignment.objects.get(pk=journal.assignment.pk)
            FileContext.objects.create(
                file=ContentFile(f.file.file.read(), name=f.file_name),
                file_name=f.file_name,
                author=User.objects.get(pk=f.author.pk),
                journal=journal,
                assignment=assignment,
                is_temp=False,
                creation_date=f.creation_date,
                last_edited=f.last_edited,
                content=content,
            )
            f.delete()
        except OSError:
            logger.error('File {} was not found on the filesystem ({})'.format(f.file_name, f.content))
            f.delete()


    remaining_user_files = UserFile.objects.all()
    if remaining_user_files.exists():
        logger.error('UserFiles {} still exist.'.format([f.pk for f in remaining_user_files]))


def convertBase64CommentsToFiles(apps, schema_editor):
    Comment = apps.get_model('VLE', 'Comment')
    FileContext = apps.get_model('VLE', 'FileContext')

    for c in Comment.objects.all():
        if c.author is None and re.search(base64ImgEmbedded, c.text):
            logger.error('Comment {} contains base64 images without author'.format(c.id))
            continue

        def createEmbbededCommentFiles(str_match):
            file_name = 'comment-{}-from-base64-{}'.format(c.pk, uuid.uuid4().hex)
            f = FileContext.objects.create(
                file=base64ToContentFile(str_match.group(1), file_name),
                file_name=file_name,
                author=c.author,
                comment=c,
                journal=c.entry.node.journal,
                is_temp=False,
                in_rich_text=True,
                creation_date=c.creation_date,
                last_edited=c.last_edited,
            )

            return fileToEmbdeddedImageLink(f)

        c.text = re.sub(base64ImgEmbedded, createEmbbededCommentFiles, c.text)
        c.save()


def convertBase64ContentsToFiles(apps, schema_editor):
    Content = apps.get_model('VLE', 'Content')
    FileContext = apps.get_model('VLE', 'FileContext')
    Field = apps.get_model('VLE', 'Field')

    for c in Content.objects.filter(field__type='rt'):
        def createEmbbededContentFiles(str_match):
            file_name = 'content-{}-from-base64-{}'.format(c.pk, uuid.uuid4().hex)

            f = FileContext.objects.create(
                file=base64ToContentFile(str_match.group(1), file_name),
                file_name=file_name,
                author=c.entry.node.journal.user,
                content=c,
                journal=c.entry.node.journal,
                is_temp=False,
                in_rich_text=True,
                creation_date=c.entry.creation_date,
                last_edited=c.entry.last_edited,
            )

            return fileToEmbdeddedImageLink(f)

        if c.data:
            c.data = re.sub(base64ImgEmbedded, createEmbbededContentFiles, c.data)
            c.save()

    for c in Content.objects.filter(field__type__in=['p', 'f', 'i']):
        if c.data:
            try:
                c.data = str(FileContext.objects.get(content=c, file_name=c.data).pk)
                c.save()
            except:
                c.data = None
                c.save()


def convertBase64AssignmentDescriptionsToFiles(apps, schema_editor):
    Assignment = apps.get_model('VLE', 'Assignment')
    FileContext = apps.get_model('VLE', 'FileContext')

    for a in Assignment.objects.all():
        if a.author is None and re.search(base64ImgEmbedded, a.description):
            logger.error('Assignment {} description contains base64 images without author'.format(a.id))
            continue

        def createEmbbededAssignmentDescriptionFiles(str_match):
            file_name = 'assignment-description-{}-from-base64-{}'.format(a.pk, uuid.uuid4().hex)

            f = FileContext.objects.create(
                file=base64ToContentFile(str_match.group(1), file_name),
                file_name=file_name,
                author=a.author,
                assignment=a,
                is_temp=False,
                in_rich_text=True,
                creation_date=a.courses.first().startdate or timezone.now(),
                last_edited=a.courses.first().startdate or timezone.now(),
            )

            return fileToEmbdeddedImageLink(f)

        if a.description:
            a.description = re.sub(base64ImgEmbedded, createEmbbededAssignmentDescriptionFiles, a.description)
            a.save()


def convertBase64FieldDescriptionsToFiles(apps, schema_editor):
    Field = apps.get_model('VLE', 'Field')
    FileContext = apps.get_model('VLE', 'FileContext')
    Assignment = apps.get_model('VLE', 'Assignment')
    Node = apps.get_model('VLE', 'Node')

    for field in Field.objects.all():
        if not Node.objects.filter(preset__format=field.template.format).exists():
            continue
        assignment = field.template.format.assignment
        if not assignment:
            assignment = Node.objects.filter(preset__format=field.template.format).first().journal.assignment
        if assignment.author is None and re.search(base64ImgEmbedded, field.description):
            logger.error('Field {} description contains base64 images without author'.format(field.id))
            continue

        def createEmbbededFieldDescriptionFiles(str_match):
            file_name = 'field-description-{}-from-base64-{}'.format(field.pk, uuid.uuid4().hex)

            f = FileContext.objects.create(
                file=base64ToContentFile(str_match.group(1), file_name),
                file_name=file_name,
                author=assignment.author,
                assignment=assignment,
                in_rich_text=True,
                is_temp=False,
                # QUESTION: Should we add these dates to a template?
                creation_date=assignment.courses.first().startdate or timezone.now(),
                last_edited=assignment.courses.first().startdate or timezone.now(),
            )

            return fileToEmbdeddedImageLink(f)

        if field.description:
            field.description = re.sub(base64ImgEmbedded, createEmbbededFieldDescriptionFiles, field.description)
            field.save()


def convertBase64ProfilePicturesToFiles(apps, schema_editor):
    User = apps.get_model('VLE', 'User')
    FileContext = apps.get_model('VLE', 'FileContext')
    base64Img = re.compile(r'data:image\/[^;]+;base64[^\"]+')

    for u in User.objects.all():
        match = re.search(base64Img, u.profile_picture)
        if match:
            file_name = 'profile-picture-from-base64-{}'.format(uuid.uuid4().hex)

            f = FileContext.objects.create(
                file=base64ToContentFile(match.group(0), file_name),
                file_name=file_name,
                author=u,
                is_temp=False,
                creation_date=timezone.now(),
                last_edited=timezone.now(),
            )

            u.profile_picture = download_url(f, access_id=True)
            u.save()


class Migration(migrations.Migration):

    dependencies = [
        ('VLE', '0037_assignment_assigned_groups'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileContext',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=VLE.utils.file_handling.get_file_path)),
                ('file_name', models.TextField()),
                ('is_temp', models.BooleanField(default=True)),
                ('in_rich_text', models.BooleanField(default=False)),
                ('creation_date', models.DateTimeField(editable=False)),
                ('last_edited', models.DateTimeField()),
                ('assignment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.Assignment')),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('content', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.Content')),
                ('comment', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.Comment')),
                ('course', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.Course')),
                ('journal', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='VLE.Journal')),
                ('access_id', models.CharField(default=VLE.models.access_gen, max_length=128, unique=True)),
            ],
        ),
        migrations.RunPython(convertUserFiles),
        migrations.RunPython(convertBase64CommentsToFiles),
        migrations.RunPython(convertBase64ContentsToFiles),
        migrations.RunPython(convertBase64AssignmentDescriptionsToFiles),
        migrations.RunPython(convertBase64FieldDescriptionsToFiles),
        migrations.RunPython(convertBase64ProfilePicturesToFiles),
    ]
