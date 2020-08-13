import test.factory as factory

from django.test import TestCase

import VLE.validators
from VLE.models import Content, Field, FileContext, Journal
from VLE.utils.error_handling import VLEProgrammingError


class ContentTest(TestCase):
    def test_content_factory(self):
        entry = factory.Entry()
        c_count = Content.objects.count()
        content = factory.Content(entry=entry, field__type=Field.TEXT, field__template=entry.template)

        # assert False, 'The content is attached to the template of the entry'
        assert content.entry.pk == entry.pk, 'Content should chain upto entry'
        assert Journal.objects.count() == 1, 'Generating content for a given entry generates a single journal'
        assert c_count + 1 == Content.objects.count(), 'No additional content is created'
        assert entry.template.pk == content.field.template.pk, \
            'The template of the entry is equal to the template of the content'

        for type in [t for (t, _) in Field.TYPES if t != Field.NO_SUBMISSION]:
            content = factory.Content(field__type=type, entry=content.entry, field__template=entry.template)
            assert content.field.type == type, 'Content type should be specifiable via its field'
            VLE.validators.validate_entry_content(content.data, content.field)

        with self.assertRaises(VLEProgrammingError):
            factory.Content(entry=content.entry, field__type=Field.NO_SUBMISSION, field__template=entry.template)

        # It should not be possible to create content for the same field of the same entry
        with self.assertRaises(VLEProgrammingError):
            factory.Content(entry=entry, field__type=Field.TEXT, field__template=entry.template, field=content.field)

    def test_file_content_factory(self):
        entry = factory.Entry()
        content = factory.Content(entry=entry, field__type=Field.FILE, field__template=entry.template)
        # Exactly one FileContext should be generated for the file content
        fc = FileContext.objects.get(content=content, journal=content.entry.node.journal, in_rich_text=False)

        assert content.data == str(fc.pk), 'The data should be equal to the pk of the generated fc'

        content = factory.Content(
            field__type=Field.FILE, field__options='jpg', entry=content.entry, field__template=entry.template)
        fc = FileContext.objects.get(content=content, journal=content.entry.node.journal, in_rich_text=False)

        # TODO JIR: Enable tests once _gen_file_field_file works
        # assert fc.file_name.split('.')[-1] in content.field.options, \
        #     'The generated fc file_name conforms to the extension options'
        # assert fc.file.path.split('.')[-1] in content.field.options, \
        #     'The generated fc file path conforms to the extension options'

    def test_rich_text_content_factory(self):
        entry = factory.Entry()
        number_of_files_in_rich_text = 2
        content = factory.Content(
            entry=entry,
            field__template=entry.template,
            field__type=Field.RICH_TEXT,
            data__n_files=number_of_files_in_rich_text,
        )
        fcs = FileContext.objects.filter(content=content, journal=content.entry.node.journal, in_rich_text=True)

        assert fcs.count() == number_of_files_in_rich_text
        for fc in fcs:
            assert fc.download_url(access_id=fc.access_id) in content.data, \
                'The file context download url should be present in the data of the RichText content'
