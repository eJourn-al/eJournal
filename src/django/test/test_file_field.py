import test.factory as factory
from test.utils import api

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from VLE.models import Field

MULTIPART_CONTENT = 'multipart/form-data; boundary=BoUnDaRyStRiNg'


class FileFieldTest(TestCase):
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

        self.create_params = {
            'journal_id': self.journal.pk,
            'template_id': self.template.pk,
            'content': {}
        }
        self.image = SimpleUploadedFile('file.png', b'image_content', content_type='image/png')
        self.txt = SimpleUploadedFile('file.txt', b'text_content', content_type='text/plain')

    def test_template_save(self):
        txt_field = Field.objects.create(
            type=Field.FILE, options=' txt,pdf,  doc  ', template=self.template, location=9, required=False)
        assert txt_field.options == 'txt, pdf, doc'

        all_field = Field.objects.create(type=Field.FILE, template=self.template, location=10, required=False)
        assert not all_field.options

        entry_file = api.post(
            self, 'files', params={'file': self.image}, user=self.student, content_type=MULTIPART_CONTENT, status=201)
        post = self.create_params
        post['content'] = {txt_field.pk: entry_file}
        resp = api.post(self, 'entries', params=post, user=self.student, status=400)
        assert 'is not allowed' in resp['description'], 'non txt file should not be able to be uploaded to txt field'

        post['content'] = {all_field.pk: entry_file}
        resp = api.post(self, 'entries', params=post, user=self.student, status=201)
        assert self.student.filecontext_set.filter(pk=entry_file['id']).exists(), 'File should exist after valid upload'

        entry_file = api.post(
            self, 'files', params={'file': self.txt}, user=self.student, content_type=MULTIPART_CONTENT, status=201)
        post['content'] = {txt_field.pk: entry_file}
        resp = api.post(self, 'entries', params=post, user=self.student, status=201)
        assert self.student.filecontext_set.filter(pk=entry_file['id']).exists(), \
            'Txt file should be able to be uploaded to txt field'
