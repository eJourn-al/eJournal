import os
import test.factory as factory
from pathlib import Path
from test.utils import api

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

import VLE.tasks.beats.cleanup
from VLE.models import Content, Entry, Field, FileContext, User
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
            'content': {},
        }

    def tearDown(self):
        """Cleans any remaining user_files on the file system (remnants from failed tests) assumes user_file instance
        infact deletes corresponding files"""
        FileContext.objects.all().delete()

    def test_file_context_factory(self):
        u_count = User.objects.count()

        fc = factory.FileContext()
        assert u_count + 1 == User.objects.count(), 'One user is generated'
        assert User.objects.last().pk == fc.author.pk, 'The generated user is indeed the author of the fc'
        assert fc.file_name in fc.file.name, 'The instance file name is sensible in comparison to the underlying file.'
        assert os.path.exists(fc.file.path), 'An actual file is created for the file context test instance'

        author = factory.Student()
        u_count = User.objects.count()

        fc = factory.FileContext(author=author)
        assert u_count == User.objects.count(), 'No user is generated if the author is specified'

    def test_file_content_file_context_factory(self):
        entry = factory.UnlimitedEntry()
        u_count = User.objects.count()

        file_content_fc = factory.FileContentFileContext(author=entry.author, content__entry=entry)
        assert u_count == User.objects.count(), 'No additional user is created if the author is specified'
        assert entry.author.pk == file_content_fc.author.pk, 'The entry user is indeed the author of the fc'

        entry = factory.UnlimitedEntry()
        u_count = User.objects.count()

        file_content_fc = factory.FileContentFileContext(content__entry=entry)
        assert u_count == User.objects.count(), 'No additional user is created if the entry is specified'
        assert entry.author.pk == file_content_fc.author.pk, 'The entry user is indeed the author of the fc'

        entry = factory.UnlimitedEntry()
        u_count = User.objects.count()
        c_count = Content.objects.count()

        file_content = factory.Content(field__type=Field.FILE, entry=entry)
        assert file_content.filecontext_set.count() == 1
        fc = file_content.filecontext_set.first()

        assert c_count + 1 == Content.objects.count(), 'A single content instance is generated'
        assert u_count == User.objects.count(), 'No additional user is generated'
        assert entry.author.pk == fc.author.pk, 'The entries user should be used as the author of the fc'

    def test_establish_files_entry_update(self):
        assignment = factory.Assignment()
        template = factory.FilesTemplate(format=assignment.format)
        entry = factory.UnlimitedEntry(template=template, node__journal__assignment=assignment)
        student = entry.node.journal.authors.first().user

        image = SimpleUploadedFile('file.png', b'image_content', content_type='image/png')
        new_image = api.post(
            self, 'files', params={'file': image}, user=student, content_type=MULTIPART_CONTENT, status=201)['file']

        patch = {
            'pk': entry.pk,
            'template_id': template.pk,
            'journal_id': entry.node.journal.pk,
            'content': {
                template.field_set.first().pk: new_image,
            },
        }
        api.update(self, 'entries', params=patch, user=student)

    def test_file_retrieve(self):
        file = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)
        other_teacher = factory.Teacher()

        # Test get unestablished files
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=200)
        api.get(self, 'files', params={'pk': file.pk}, user=self.teacher, status=403)
        api.get(self, 'files', params={'pk': file.pk}, user=other_teacher, status=403)

        # Test teacher can see after establishing in journal
        file_handling.establish_file(author=self.student, file_context=file, journal=self.journal)
        api.get(self, 'files', params={'pk': file.pk}, user=self.teacher, status=200)

        # Test only teacher can see own unpublished comment
        file = FileContext.objects.create(file=self.video, author=self.teacher, file_name=self.video.name)
        hidden_comment = factory.TeacherComment(
            author=self.teacher, entry=factory.UnlimitedEntry(node__journal=self.journal), published=False)
        file_handling.establish_file(author=self.teacher, file_context=file, comment=hidden_comment)
        api.get(self, 'files', params={'pk': file.pk}, user=other_teacher, status=403)
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=403)
        api.get(self, 'files', params={'pk': file.pk}, user=self.teacher, status=200)

        # Test student can see after comment publish
        hidden_comment.published = True
        hidden_comment.save()
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=200)

        file = FileContext.objects.create(file=self.video, author=self.teacher, file_name=self.video.name)
        file_handling.establish_file(author=self.teacher, file_context=file, assignment=self.assignment)
        api.get(self, 'files', params={'pk': file.pk}, user=self.student, status=200)
        api.get(self, 'files', params={'pk': file.pk}, user=other_teacher, status=403)

        # Test non related user on file without context (e.g. profile picture)
        file = FileContext.objects.create(file=self.video, author=self.student, file_name=self.video.name)
        # Student should be able to get its own file
        api.get(self, 'files', params={'pk': file.pk}, user=self.student)
        # Unrelated teacher should not be able to get students file
        api.get(self, 'files', params={'pk': file.pk}, user=other_teacher, status=403)
        # Unrelated teacher should be able to get students file with the use of access_id
        api.get(self, 'files', params={'pk': file.pk, 'access_id': file.access_id}, user=other_teacher)
        # Unrelated teacher should be able to get students file using the dedicated access endpoint
        api.get(self, 'files/access_id', params={'pk': file.access_id}, user=other_teacher)

    def test_file_context_model(self):
        # Dedicated file due to possible race conditions across tests
        isolated_file = SimpleUploadedFile('isolted_file.mp4', b'file_content', content_type='video/mp4')

        file = FileContext.objects.filter(author=self.student.pk, file_name=self.video.name)
        assert not file.exists(), "Assumes the student has no apriori user files."

        file = FileContext.objects.create(file=isolated_file, author=self.student, file_name=isolated_file.name)

        file_get = FileContext.objects.filter(author=self.student.pk, file_name=isolated_file.name).first()
        assert file, "The student should have successfully created a temp user file."
        assert file == file_get, "The created user file should be equal to the gotten user file from db."
        path = file.file.path
        actual_file_name = Path(path).name

        assert os.path.exists(path) and os.path.isfile(path), \
            "The file should be created on file styem as an actual file."

        assert actual_file_name == file.file_name, "The user file name field should match the actual file name."

        assert file_handling.get_file_path(file, file.file_name) in file.file.path, \
            "The user file's file path should follow the get_path logic"

        file.delete()
        assert not FileContext.objects.filter(author=self.student.pk, file_name=isolated_file.name).exists(), \
            "User file should be deleted from DB."
        assert not os.path.exists(path), \
            "Deleting a user file instance should delete the corresponding file as well."

        # Check if path moves after establishing
        file = FileContext.objects.create(file=isolated_file, author=self.student, file_name=isolated_file.name)
        file_handling.establish_file(author=self.student, file_context=file, assignment=self.assignment)
        file = FileContext.objects.get(author=self.student, file_name=isolated_file.name)

        assert file_handling.get_file_path(file, file.file_name) in file.file.path, \
            "The user file's file path should follow the get_path logic once made a permanent file"

        # Two files with the same name should be able to be established to the same folder
        file1 = FileContext.objects.create(file=isolated_file, author=self.student, file_name=isolated_file.name)
        file2 = FileContext.objects.create(file=isolated_file, author=self.student, file_name=isolated_file.name)
        file_handling.establish_file(author=self.student, file_context=file1, assignment=self.assignment)
        file_handling.establish_file(author=self.student, file_context=file2, assignment=self.assignment)
        # After established files, another file with same name should be able to be established
        file3 = FileContext.objects.create(file=isolated_file, author=self.student, file_name=isolated_file.name)
        file_handling.establish_file(author=self.student, file_context=file3, assignment=self.assignment)

        # Files should be on their own
        assert FileContext.objects.get(pk=file1.pk).file.path != FileContext.objects.get(pk=file2.pk).file.path
        assert FileContext.objects.get(pk=file2.pk).file.path != FileContext.objects.get(pk=file3.pk).file.path

    def test_remove_unused_files_content(self):
        # Test uploading two files, then post entry, 1 gets removed
        content_fake = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201,
        )['file']
        content_real = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201,
        )['file']
        post = self.create_params
        post['content'] = {self.img_field.pk: content_real}
        api.post(self, 'entries', params=post, user=self.student, status=201)
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())

        assert self.student.filecontext_set.filter(pk=content_real['id']).exists(), 'real file should stay'
        assert not self.student.filecontext_set.filter(pk=content_fake['id']).exists(), 'fake file should be removed'

        # Rich text fields also need to be checked to not be deleted
        content_fake = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)['file']
        content_real = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)['file']
        content_rt = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)['file']
        post = self.create_params
        post['content'] = {
            self.img_field.pk: content_real,
            self.rt_field.pk: "<p>hello!<img src='{}'/></p>".format(content_rt['download_url']),
        }
        entry_with_rt = api.post(self, 'entries', params=post, user=self.student, status=201)['entry']
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())
        assert self.student.filecontext_set.filter(pk=content_real['id']).exists(), 'real file should stay'
        assert self.student.filecontext_set.filter(pk=content_rt['id']).exists(), 'rich text shoud stay'
        assert not self.student.filecontext_set.filter(pk=content_fake['id']).exists(), 'fake file should be removed'

        # When file in entry updates, old file needs to be removed
        content_old = content_real
        content_new = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201,
        )['file']
        patch = {
            'pk': entry_with_rt['id'],
            'content': post['content'],
        }
        patch['content'][list(patch['content'].keys())[0]] = content_new
        api.update(self, 'entries', params=patch, user=self.student)
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())
        assert self.student.filecontext_set.filter(pk=content_new['id']).exists(), 'new file should exist'
        assert not self.student.filecontext_set.filter(pk=content_old['id']).exists(), 'old file should be removed'

        # When file in rich text updates, old file needs to be removed
        content_old_rt = content_rt
        content_new_rt = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)['file']
        content_new_rt2 = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True},
            user=self.student, content_type=MULTIPART_CONTENT, status=201)['file']
        rt_field_id = next(field for field in self.template.field_set.all() if field.type == 'rt').id
        patch['content'][rt_field_id] = "<p>hello!<img src='{}' /><img src='{}' /></p>".format(
            content_new_rt['download_url'], content_new_rt2['download_url'])
        api.update(self, 'entries', params=patch, user=self.student)
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())
        assert self.student.filecontext_set.filter(pk=content_new_rt['id']).exists(), 'new file should exist'
        assert self.student.filecontext_set.filter(pk=content_new_rt2['id']).exists(), 'new file should exist'
        assert not self.student.filecontext_set.filter(pk=content_old_rt['id']).exists(), 'old file should be removed'

    def test_remove_unused_files_comment(self):
        # Test uploading two files, then post comment, 1 gets removed
        content_fake = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True}, user=self.student,
            content_type=MULTIPART_CONTENT, status=201)['file']
        content_real = api.post(
            self, 'files', params={'file': self.image, 'in_rich_text': True}, user=self.student,
            content_type=MULTIPART_CONTENT, status=201)['file']
        params = {
            'entry_id': factory.UnlimitedEntry(node__journal=self.journal).pk,
            'text': '<p><img src="{}"</p>'.format(content_real['download_url']),
            'published': True,
            'files': [],
        }
        api.create(self, 'comments', params=params, user=self.student)
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())
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
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())
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
        VLE.tasks.beats.cleanup.remove_unused_files(older_lte=timezone.now())
        assert not FileContext.objects.filter(access_id=deleted).exists(), 'old journal image should be deleted'
        assert FileContext.objects.filter(access_id=new).exists(), 'new journal image should not be deleted'

    def test_file_upload(self):
        api.post(
            self, 'files', params={'file': self.image}, user=self.teacher, content_type=MULTIPART_CONTENT, status=201)
        file = FileContext.objects.get(author=self.teacher.pk, file_name=self.image.name)
        assert file, 'The student should have successfully created a temp user file.'

    def test_establish(self):
        to_establish = api.post(
            self, 'files', params={'file': self.image}, user=self.teacher, content_type=MULTIPART_CONTENT, status=201
        )['file']

        self.assertRaises(
            VLEPermissionError, file_handling.establish_file, author=self.student, identifier=to_establish['id'])

        file_handling.establish_file(author=self.teacher, identifier=to_establish['id'], assignment=self.assignment)
        # Cannot establish twice
        self.assertRaises(
            VLEBadRequest, file_handling.establish_file, author=self.teacher, identifier=to_establish['id'])

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
        template = factory.Template(format=self.format, add_fields=[{'type': Field.TEXT}])
        deadline = factory.DeadlinePresetNode(format=self.format, forced_template=template)
        deadline_node = self.journal.node_set.get(preset=deadline)
        entry = factory.PresetEntry(node=deadline_node)

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
            user=author, content_type=MULTIPART_CONTENT, status=201)['file']
        content = {f.pk: 'abcd' for f in node.preset.forced_template.field_set.exclude(pk=field.pk)}
        content[field.pk] = resp.copy()
        entry = api.create(
            self, 'entries', params={
                'journal_id': node.journal.pk, 'node_id': node.pk, 'template_id': node.preset.forced_template.pk,
                'content': content
            },
            user=author)['entry']
        Entry.objects.get(pk=entry['id']).delete()
        # over 255 should give a proper response
        long_name = SimpleUploadedFile('f' * 256 + '.png', b'image_content', content_type='image/png')
        resp = api.post(
            self, 'files', params={'file': long_name, 'in_rich_text': False},
            user=author, content_type=MULTIPART_CONTENT, status=400)
        assert 'filename' in resp['description']
