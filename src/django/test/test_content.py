import os
import test.factory as factory

from django.core.exceptions import ValidationError
from django.test import TestCase

import VLE.validators
from VLE.models import Content, Field, FileContext, Journal
from VLE.utils.error_handling import VLEProgrammingError


class ContentTest(TestCase):
    def test_temp_todo_remove(self):
        journal = factory.Journal(entries__n=0, assignment__format__templates=[{'type': Field.RICH_TEXT}])
        entry = factory.UnlimitedEntry(node__journal=journal)

        for c in entry.content_set.all():
            VLE.validators.validate_entry_content(c.data, c.field)

    def test_content_factory(self):
        entry = factory.UnlimitedEntry()
        n_template_fields = entry.template.field_set.count()
        c_count = Content.objects.count()
        content = factory.Content(entry=entry, field__type=Field.TEXT)

        # assert False, 'The content is attached to the template of the entry'
        assert content.entry.pk == entry.pk, 'Content should chain upto entry'
        assert Journal.objects.count() == 1, 'Generating content for a given entry generates a single journal'
        assert c_count + 1 == Content.objects.count(), 'No additional content is created'
        assert entry.template.pk == content.field.template.pk, \
            'The template of the entry is equal to the template of the content'
        assert n_template_fields + 1 == entry.template.field_set.count(), \
            'If no field is specified for the content, the content creates a field'

        assignment = factory.Assignment(format__templates=False)
        factory.TemplateAllTypes(format=assignment.format)
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment)

        for c in entry.content_set.all():
            # FILE type content data does not match its expected validation data input (dict vs string)
            if c.field.type == Field.FILE:
                VLE.validators.validate_entry_content({'id': c.data}, c.field)
            else:
                VLE.validators.validate_entry_content(c.data, c.field)

        file_content = factory.Content(field__type=Field.FILE, entry=content.entry)
        assert file_content.filecontext_set.count() == 1, 'A single File is created'
        fc = file_content.filecontext_set.first()
        assert int(file_content.data) == fc.pk, 'file content data should be equal to the fc\'s pk'

        with self.assertRaises(VLEProgrammingError):
            factory.Content(entry=content.entry, field__type=Field.NO_SUBMISSION)

        # It should not be possible to create content for the same field of the same entry
        with self.assertRaises(ValidationError):
            factory.Content(entry=entry, field__type=Field.TEXT, field=content.field)

    def test_file_content_factory(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.FILE}])
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment)

        assert entry.content_set.count() == 1, 'Entry contains content for the single template FILE field'
        content = entry.content_set.first()
        # Exactly one FileContext should be generated for the file content
        fc = FileContext.objects.get(content=content, journal=content.entry.node.journal, in_rich_text=False)

        assert content.data == str(fc.pk), 'The data should be equal to the pk of the generated fc'

        content = factory.Content(
            field__type=Field.FILE, field__options='jpg', entry=content.entry, field__template=entry.template)
        fc = FileContext.objects.get(content=content, journal=content.entry.node.journal, in_rich_text=False)

        assert fc.file_name.split('.')[-1] in content.field.options, \
            'The generated fc file_name conforms to the extension options'
        assert fc.file.path.split('.')[-1] in content.field.options, \
            'The generated fc file path conforms to the extension options'

    def test_rich_text_content_factory(self):
        journal = factory.Journal(assignment__format__templates=[{'type': Field.RICH_TEXT}])
        entry = factory.UnlimitedEntry(node__journal=journal)
        content = entry.content_set.first()
        fcs = FileContext.objects.filter(content=content, journal=content.entry.node.journal, in_rich_text=True)

        for fc in fcs:
            assert fc.download_url(access_id=fc.access_id) in content.data, \
                'The file context download url should be present in the data of the RichText content'

        journal = factory.Journal(assignment__format__templates=[{'type': Field.RICH_TEXT}])
        entry = factory.UnlimitedEntry(gen_content=True, node__journal=journal)
        content = entry.content_set.first()
        assert content.field.type == Field.RICH_TEXT, 'Content is only generated for the template with a single field'

        journal = factory.Journal(assignment__format__templates=[{'type': Field.RICH_TEXT}])
        entry = factory.UnlimitedEntry(gen_content=False, node__journal=journal)

        assert not entry.content_set.exists(), 'Content generation can be toggled off'

    def test_content_factory_with_deep_field_syntax(self):
        assignment = factory.Assignment()
        default_template = assignment.format.template_set.first()
        template2 = factory.MentorgesprekTemplate(format=assignment.format)

        journal = factory.Journal(entries__n=0)
        entry = factory.UnlimitedEntry(template=default_template, gen_content=False, node__journal=journal)
        content = factory.Content(entry=entry, field__template=entry.template)
        assert content.field.template == default_template, 'Directly setting the field via content factory works'

        content = factory.Content(entry=entry, field__type=Field.URL)
        assert content.field.type == Field.URL, 'Deep syntax works for the field type'

        # Content will cause entry to be generated upwards, but that entry does not know which template to select
        # since the content itself is not generated. A problem in our DB layer.
        self.assertRaises(ValidationError, factory.Content, entry__node__journal=journal, field__template=template2)

        assert factory.Content(entry__node__journal=journal, field__template=template2, entry__template=template2), \
            'Deep syntax works for the template of the content'

    def test_entry_file_content_from_file_factory(self):
        assignment = factory.Assignment(format__templates=[{'type': Field.FILE}])
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment, gen_content__from_file=True)

        content = entry.content_set.first()
        fc = content.filecontext_set.first()
        assert os.path.exists(fc.file.path), 'An actual file is created when working from file object'

        assignment = factory.Assignment(format__templates=[{'type': Field.RICH_TEXT}])
        entry = factory.UnlimitedEntry(node__journal__assignment=assignment, gen_content__from_file=True)

        content = entry.content_set.first()
        fc = content.filecontext_set.first()
        assert os.path.exists(fc.file.path), 'An actual file is created when working from file object'
