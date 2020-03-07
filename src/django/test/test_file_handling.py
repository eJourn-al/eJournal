import os
import test.factory as factory
from pathlib import Path
from test.utils import api

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from VLE.models import Field, FileContext
from VLE.utils import file_handling
from VLE.utils.error_handling import VLEBadRequest, VLEPermissionError

BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY


class FileHandlingTest(TestCase):
    def setUp(self):
        self.student = factory.Student()
        self.journal = factory.Journal(user=self.student)
        self.assignment = self.journal.assignment
        self.format = self.journal.assignment.format
        self.teacher = self.journal.assignment.courses.first().author
        self.unrelated_assignment = factory.Assignment()
        self.video = SimpleUploadedFile('file.mp4', b'file_content', content_type='video/mp4')
        self.image = SimpleUploadedFile('file.png', b'image_content', content_type='image/png')
        self.template = factory.TemplateAllTypes(format=self.format)
        self.img_field = Field.objects.get(type=Field.IMG)
        self.rt_field = Field.objects.get(type=Field.RICH_TEXT)
        self.file_field = Field.objects.get(type=Field.FILE)

        self.create_params = {
            'journal_id': self.journal.pk,
            'template_id': self.template.pk,
            'content': []
        }

    def tearDown(self):
        """Cleans any remaining user_files on the file system (remnants from failed tests) assumes user_file instance
        infact deletes corresponding files"""
        FileContext.objects.all().delete()

    def test_file_retrieve(self):
        file = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)

        # Test get unestablished files
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=200)
        api.get(self, 'files', params={'pk': file.pk}, user=self.teacher, status=403)
        api.get(self, 'files', params={'pk': file.pk}, user=factory.Teacher(), status=403)

        # Test teacher can see after establishing in journal
        file_handling.establish_file(self.student, file.pk, journal=self.journal)
        api.get(self, 'files', params={'pk': file.pk}, user=self.teacher, status=200)

        # Test only teacher can see own unpublished comment
        file = FileContext.objects.create(file=self.video, author=self.teacher, file_name=self.video.name)
        hidden_comment = factory.TeacherComment(
            author=self.teacher, entry=factory.Entry(node__journal=self.journal), published=False)
        file_handling.establish_file(self.teacher, file.pk, comment=hidden_comment)
        api.get(self, 'files', params={'pk': file.pk}, user=factory.Teacher(), status=403)
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=403)
        api.get(self, 'files', params={'pk': file.pk}, user=self.teacher, status=200)

        # Test student can see after comment publish
        hidden_comment.published = True
        hidden_comment.save()
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=200)

        file = FileContext.objects.create(file=self.video, author=self.teacher, file_name=self.video.name)
        file_handling.establish_file(self.teacher, file.pk, assignment=self.assignment)
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=200)
        api.get(self, 'files', params={'pk': file.pk}, user=factory.Teacher(), status=403)

    def test_file_context_model(self):
        file = FileContext.objects.filter(author=self.student.pk, file_name=self.video.name)
        assert not file.exists(), "Assumes the student has no apriori user files."

        file = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)

        file_get = FileContext.objects.filter(author=self.student.pk, file_name=self.video.name).first()
        assert file, "The student should have succesfully created a temp user file."
        assert file == file_get, "The created user file should be equal to the gotten user file from db."
        path = file.file.path
        actual_file_name = Path(path).name

        assert os.path.exists(path) and os.path.isfile(path), \
            "The file should be created on file styem as an actual file."

        assert actual_file_name == file.file_name, "The user file name field should match the actual file name."

        assert file_handling.get_file_path(file, file.file_name) in file.file.path, \
            "The user file's file path should follow the get_path logic"

        file.delete()
        assert not FileContext.objects.filter(author=self.student.pk, file_name=self.video.name).exists(), \
            "User file should be deleted from DB."
        assert not os.path.exists(path), \
            "Deleting a user file instance should delete the corresponding file as well."

        # Check if path moves after establishing
        file = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)
        file_handling.establish_file(self.student, file.pk, assignment=self.assignment)
        file = FileContext.objects.get(author=self.student, file_name=self.video.name)

        assert file_handling.get_file_path(file, file.file_name) in file.file.path, \
            "The user file's file path should follow the get_path logic once made a permanent file"

        # Two files with the same name should be able to be established to the same folder
        file1 = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)
        file2 = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)
        file_handling.establish_file(self.student, file1.pk, assignment=self.assignment)
        file_handling.establish_file(self.student, file2.pk, assignment=self.assignment)
        # After established files, another file with same name should be able to be established
        file3 = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)
        file_handling.establish_file(self.student, file3.pk, assignment=self.assignment)

        # Files should be on their own
        assert FileContext.objects.get(pk=file1.pk).file.path != FileContext.objects.get(pk=file2.pk).file.path
        assert FileContext.objects.get(pk=file2.pk).file.path != FileContext.objects.get(pk=file3.pk).file.path

    def test_remove_unused_files(self):
        # Test uploading two files, then post entry, 1 gets removed
        content_fake = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201)
        content_real = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201)
        post = self.create_params
        post['content'] = [{'data': content_real, 'id': self.img_field.pk}]
        api.post(self, 'entries', params=post, user=self.student, status=201)
        assert self.student.filecontext_set.filter(pk=content_real['id']).exists(), 'real file should stay'
        assert not self.student.filecontext_set.filter(pk=content_fake['id']).exists(), 'fake file should be removed'

        # Rich text fields also need to be checked to not be deleted
        content_fake = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)
        content_real = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)
        content_rt = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)
        post = self.create_params
        post['content'] = [
            {'data': content_real, 'id': self.img_field.pk},
            {'data': "<p>hello!<img src='{}' /></p>".format(content_rt['download_url']), 'id': self.rt_field.pk}
        ]
        entry_with_rt = api.post(self, 'entries', params=post, user=self.student, status=201)['entry']
        assert self.student.filecontext_set.filter(pk=content_real['id']).exists(), 'real file should stay'
        assert self.student.filecontext_set.filter(pk=content_rt['id']).exists(), 'rich text shoud stay'
        assert not self.student.filecontext_set.filter(pk=content_fake['id']).exists(), 'fake file should be removed'

        # When file in entry updates, old file needs to be removed
        content_old = content_real
        content_new = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201)
        patch = {
            'pk': entry_with_rt['id'],
            'content': post['content']
        }
        patch['content'][0]['data'] = content_new
        api.update(self, 'entries', params=patch, user=self.student)
        assert self.student.filecontext_set.filter(pk=content_new['id']).exists(), 'new file should exist'
        assert not self.student.filecontext_set.filter(pk=content_old['id']).exists(), 'old file should be removed'

        # When file in rich text updates, old file needs to be removed
        content_old_rt = content_rt
        content_new_rt = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)
        content_new_rt2 = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)
        patch['content'][1]['data'] = "<p>hello!<img src='{}' /><img src='{}' /></p>".format(
            content_new_rt['download_url'], content_new_rt2['download_url'])
        api.update(self, 'entries', params=patch, user=self.student)
        assert self.student.filecontext_set.filter(pk=content_new_rt['id']).exists(), 'new file should exist'
        assert self.student.filecontext_set.filter(pk=content_new_rt2['id']).exists(), 'new file should exist'
        assert not self.student.filecontext_set.filter(pk=content_old_rt['id']).exists(), 'old file should be removed'

    def test_remove_unused_files_assignment(self):
        # Remove old images in rich text of assignment description / template fields
        needs_removal = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        field_description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        self.assignment.description = '<p> <img src="{}" /> </p>'.format(description['download_url'])
        self.assignment.save()
        update_params = {
            'pk': self.assignment.pk,
            'assignment_details': {},
            'templates': [{
                'field_set': [{
                    'type': 't',
                    'title': '',
                    'description': '<p><img src="{}" /></p>'.format(field_description['download_url']),
                    'options': None,
                    'location': 0,
                    'required': True
                }],
                'name': 'Entry',
                'id': -1,
                'preset_only': False
            }],
            'presets': [], 'removed_presets': [], 'removed_templates': []
        }
        api.update(self, 'formats', params=update_params, user=self.teacher)
        assert self.teacher.filecontext_set.filter(pk=description['id']).exists(), 'new file should exist'
        assert self.teacher.filecontext_set.filter(pk=field_description['id']).exists(), 'new file should exist'
        assert not self.teacher.filecontext_set.filter(pk=needs_removal['id']).exists(), 'old file should be removed'

    def test_file_upload(self):
        api.post(
            self, 'files', params={'file': self.image}, user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        file = FileContext.objects.get(author=self.teacher.pk, file_name=self.image.name)
        assert file, 'The student should have succesfully created a temp user file.'

    def test_establish(self):
        to_establish = api.post(
            self, 'files', params={'file': self.image}, user=self.teacher, content_type=MULTIPART_CONTENT, status=201)

        self.assertRaises(VLEPermissionError, file_handling.establish_file, self.student, to_establish['id'])

        file_handling.establish_file(self.teacher, to_establish['id'], assignment=self.assignment)
        # Cannot establish twice
        self.assertRaises(
            VLEBadRequest, file_handling.establish_file, self.teacher, to_establish['id'])

    def test_file_upload_needs_actual_file(self):
        response = api.post(
            self,
            'files',
            params={
                'file': 'not an actual file'
            },
            user=self.student,
            status=400,
            content_type=MULTIPART_CONTENT,
        )
        assert 'No accompanying file found in the request.' in response['description']
