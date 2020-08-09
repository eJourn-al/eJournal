import os
import test.factory as factory
from pathlib import Path
from test.utils import api

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from VLE.models import Entry, Field, FileContext, PresetNode, Template
from VLE.utils import file_handling
from VLE.utils.error_handling import VLEBadRequest, VLEPermissionError

MULTIPART_CONTENT = 'multipart/form-data; boundary=BoUnDaRyStRiNg'


class FileHandlingTest(TestCase):
    def setUp(self):
        self.journal = factory.Journal()
        self.student = self.journal.authors.first().user
        self.assignment = self.journal.assignment
        self.format = self.journal.assignment.format
        self.teacher = self.journal.assignment.courses.first().author
        self.unrelated_assignment = factory.Assignment()
        self.video = SimpleUploadedFile('file.mp4', b'file_content', content_type='video/mp4')
        self.image = SimpleUploadedFile('file.png', b'image_content', content_type='image/png')
        self.template = factory.TemplateAllTypes(format=self.format)
        self.img_field = Field.objects.get(template=self.template, type=Field.FILE, options__contains='png')
        self.rt_field = Field.objects.get(template=self.template, type=Field.RICH_TEXT)
        self.file_field = Field.objects.get(template=self.template, type=Field.FILE, options=None)

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

    def test_remove_unused_files_content(self):
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

    def test_remove_unused_files_comment(self):
        # Test uploading two files, then post comment, 1 gets removed
        content_fake = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True}, user=self.student,
            content_type=MULTIPART_CONTENT, status=201)
        content_real = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True}, user=self.student,
            content_type=MULTIPART_CONTENT, status=201)
        params = {
            'entry_id': factory.Entry(node__journal=self.journal).pk,
            'text': '<p><img src="{}"</p>'.format(content_real['download_url']),
            'published': True,
            'files': [],
        }
        api.create(self, 'comments', params=params, user=self.student)
        assert self.student.filecontext_set.filter(pk=content_real['id']).exists(), 'real file should stay'
        assert not self.student.filecontext_set.filter(pk=content_fake['id']).exists(), 'fake file should be removed'

    def test_remove_profile_picture(self):
        user = factory.Student()
        blank_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAfQAAAH0CAYAAADL1t+KAAAD30lEQVR4nO3BAQEAAACC' + \
                      'IP+vbkhAAQ{}8GJFFQABGYPuoAAAAABJRU5ErkJggg=='.format('A'*1290)
        resp = api.post(
            self, 'users/set_profile_picture', params={'file': blank_image},
            content_type=MULTIPART_CONTENT, user=user, status=201)
        deleted = resp['download_url'].split('access_id=')[1]
        resp = api.post(
            self, 'users/set_profile_picture', params={'file': blank_image},
            content_type=MULTIPART_CONTENT, user=user, status=201)
        new = resp['download_url'].split('access_id=')[1]
        assert not FileContext.objects.filter(access_id=deleted).exists(), 'old journal image should be deleted'
        assert FileContext.objects.filter(access_id=new).exists(), 'new journal image should not be deleted'

    def test_remove_journal_image(self):
        journal = factory.GroupJournal(assignment__can_set_journal_image=True)
        blank_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAfQAAAH0CAYAAADL1t+KAAAD30lEQVR4nO3BAQEAAACC' + \
                      'IP+vbkhAAQ{}8GJFFQABGYPuoAAAAABJRU5ErkJggg=='.format('A'*1290)
        resp = api.update(
            self, 'journals', params={'image': blank_image, 'pk': journal.pk}, user=journal.authors.first().user)
        deleted = resp['journal']['image'].split('access_id=')[1]
        resp = api.update(
            self, 'journals', params={'image': blank_image, 'pk': journal.pk}, user=journal.authors.first().user)
        new = resp['journal']['image'].split('access_id=')[1]
        assert not FileContext.objects.filter(access_id=deleted).exists(), 'old journal image should be deleted'
        assert FileContext.objects.filter(access_id=new).exists(), 'new journal image should not be deleted'

    def test_remove_unused_files_assignment(self):
        def update_and_check(description, field_description, preset_node_description):
            template = Template.objects.filter(format__assignment=self.assignment).order_by('pk').last()
            presetnode = PresetNode.objects.filter(format__assignment=self.assignment).first()
            update_params = {
                'pk': self.assignment.pk,
                'assignment_details': {
                    'description': '<p> <img src="{}" /> </p>'.format(description['download_url']),
                },
                'templates': [{
                    'field_set': [{
                        'type': 'rt',
                        'title': '',
                        'description': '<p><img src="{}" /></p>'.format(field_description['download_url']),
                        'options': None,
                        'location': 0,
                        'template': template.pk,
                        'id': template.field_set.first().pk,
                        'required': True
                    }],
                    'name': 'Entry',
                    'id': template.pk,
                    'format': self.assignment.format.pk,
                    'preset_only': False,
                    'archived': False
                }],
                'presets': [{
                    'description': '<p><img src="{}" /></p>'.format(preset_node_description['download_url']),
                    'due_date': str(self.assignment.due_date),
                    'id': presetnode.pk if presetnode else -1,
                    'target': self.assignment.points_possible,
                    'type': 'p',
                    'template': None,
                    'lock_date': None,
                    'unlock_date': None,
                }], 'removed_presets': [], 'removed_templates': [],
            }
            api.update(self, 'formats', params=update_params, user=self.teacher)
            assert FileContext.objects.filter(pk=description['id']).exists(), 'new file should exist'
            assert FileContext.objects.filter(pk=field_description['id']).exists(), 'new file should exist'
            assert FileContext.objects.filter(pk=preset_node_description['id']).exists(), \
                'new file should exist'

        # Remove non established images
        needs_removal = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        field_description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        preset_node_description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        update_and_check(description, field_description, preset_node_description)
        assert not self.teacher.filecontext_set.filter(pk=needs_removal['id']).exists(), 'old file should be removed'

        # Remove old images in rich rext
        new_description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        new_field_description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        new_preset_node_description = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        update_and_check(new_description, new_field_description, new_preset_node_description)
        assert not FileContext.objects.filter(pk=description['id']).exists(), \
            'old file should be removed'
        assert not FileContext.objects.filter(pk=field_description['id']).exists(), \
            'old file should be removed'
        assert not FileContext.objects.filter(pk=preset_node_description['id']).exists(), \
            'old file should be removed'

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

    def test_long_file_name(self):
        entry = factory.PresetEntry()
        node = entry.node
        author = entry.author
        entry.delete()
        field = node.preset.forced_template.field_set.order_by('pk').first()
        field.type = Field.FILE
        field.save()
        # under 255 should work
        # NOTE: this is including:
        #  - the whole filepath,
        #  - extension
        #  - and the possible 36 extra hash to make it a unique filename
        long_name = SimpleUploadedFile('f' * 120 + '.png', b'image_content', content_type='image/png')
        resp = api.post(
            self, 'files', params={'file': long_name, 'in_rich_text': False},
            user=author, content_type=MULTIPART_CONTENT, status=201)
        entry = api.create(
            self, 'entries', params={
                'journal_id': node.journal.pk, 'node_id': node.pk, 'template_id': node.preset.forced_template.pk,
                'content': [{
                    'id': field.pk,
                    'data': resp.copy()
                }] + [{'id': f.pk, 'data': 'asdf'} for f in node.preset.forced_template.field_set.exclude(pk=field.pk)]
            },
            user=author)['entry']
        Entry.objects.get(pk=entry['id']).delete()
        # over 255 should give a proper response
        long_name = SimpleUploadedFile('f' * 256 + '.png', b'image_content', content_type='image/png')
        resp = api.post(
            self, 'files', params={'file': long_name, 'in_rich_text': False},
            user=author, content_type=MULTIPART_CONTENT, status=400)
        assert 'filename' in resp['description']

    def test_file_context_factory(self):
        fc = factory.FileContext()

        assert fc.file_name in fc.file.name, 'The instance file name is sensible in comparison to the underlying file.'
        assert os.path.exists(fc.file.path), 'An actual file is created for the file context test instance'
