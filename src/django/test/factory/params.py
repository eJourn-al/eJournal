import random
import test.factory
from test.factory.content import gen_valid_non_file_data
from test.factory.file_context import _fc_to_rt_img_element
from test.factory.user import DEFAULT_PASSWORD

import factory
from django.conf import settings

import VLE.models
import VLE.serializers


class JWTParamsFactory(factory.Factory):
    class Meta:
        model = dict

    user_id = factory.Sequence(lambda x: 'LMS_user_id{}'.format(x))
    custom_user_full_name = 'full name of LMS user'
    custom_user_email = factory.Sequence(lambda x: 'valid_LMS_email{}@address.com'.format(x))
    custom_user_image = 'https://LMS.com/user_profile_image_link.png'
    custom_username = factory.Sequence(lambda x: 'LMS_username{}'.format(x))


class JWTTestUserParamsFactory(JWTParamsFactory):
    custom_user_email = ''
    user_id = factory.Sequence(lambda x: "305c9b180a9ce9684ea62aeff2b2e97052cf2d4b{}".format(x))
    custom_user_full_name = settings.LTI_TEST_STUDENT_FULL_NAME
    custom_username = factory.Sequence(lambda x: '305c9b180a9ce9684ea62aeff2b2e97052cf2d4c1{}'.format(x))


class UserParamsFactory(factory.Factory):
    class Meta:
        model = dict

    username = factory.Sequence(lambda x: 'user{}'.format(x))
    password = DEFAULT_PASSWORD


class EntryContentCreationParamsFactory(factory.Factory):
    """
    Creates valid VLE.models.Entry CONTENT parameters.
    kwargs:
        template: VLE.models.Template instance for which a content dict should be generated.
        author: VLE.models.User instance, user who creates the entry.
        node: VLE.models.Node instance, node related to entry, fallsback to nothing (unlimited entry)
    """
    class Meta:
        model = dict

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        template = kwargs.pop('template')
        author = kwargs.pop('author')
        node = kwargs.pop('node', None)

        if node:
            kwargs['node_id'] = node.pk

        content = {}
        for field in template.field_set.all():
            if field.type in VLE.models.Field.TYPES_WITHOUT_FILE_CONTEXT:
                if field.type == VLE.models.Field.NO_SUBMISSION:
                    continue
                content[field.pk] = gen_valid_non_file_data(field)

            elif field.type in VLE.models.Field.FILE:
                extention = random.choice(field.options.split(', ')) if field.options else None
                filename = factory.Faker('file_name', extension=extention).generate()
                fc = test.factory.TempFileContext(author=author, file__filename=filename)
                content[field.pk] = {'id': fc.pk}

            elif field.type in VLE.models.Field.RICH_TEXT:
                fc = test.factory.TempRichTextFileContext(author=author)
                content[field.pk] = f"<p>{factory.Faker('text').generate()}</p><p>{_fc_to_rt_img_element(fc)}</p>"
        kwargs['content'] = content

        return kwargs


class UnlimitedEntryCreationParamsFactory(factory.Factory):
    """
    Creates valid entry creation parameters by tweaking the provided kwargs.
    kwargs:
        journal: VLE.models.Journal instance, journal for which an unlimited entry should be created.
        template: VLE.models.Template instance, fallsback to a random template available to the provided journal.
        author: VLE.models.User instance, fallsback to a random author of the journal.
    """
    class Meta:
        model = dict

    title = None

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        journal = kwargs.pop('journal')
        kwargs['journal_id'] = journal.pk

        template = kwargs.pop('template', random.choice(journal.assignment.format.template_set.all()))
        kwargs['template_id'] = template.pk

        if 'author' in kwargs:
            author = kwargs.pop('author')
        else:
            author = random.choice(journal.authors.all()).user

        kwargs['content'] = test.factory.EntryContentCreationParams(template=template, author=author)['content']

        return kwargs


class PresetEntryCreationParamsFactory(factory.Factory):
    """
    Creates valid preset entry creation parameters by tweaking the provided kwargs.
    kwargs:
        journal: VLE.models.Journal instance, journal for which an unlimited entry should be created.
        template: VLE.models.Template instance, fallsback to a random template available to the provided journal.
        node: VLE.models.None instance, fallsback to a newly created ENTRYDEADLINE node
        author: VLE.models.User instance, fallsback to a random author of the journal.
    """
    class Meta:
        model = dict

    title = None

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        journal = kwargs.pop('journal')

        if 'node' in kwargs:
            node = kwargs['node']
        else:
            preset = test.factory.DeadlinePresetNode(format=journal.assignment.format)
            node = preset.node_set.filter(journal=journal).get()

        kwargs['node_id'] = node.pk
        kwargs['journal_id'] = journal.pk

        template = preset.forced_template
        kwargs['template_id'] = template.pk

        if 'author' in kwargs:
            author = kwargs['author']
        else:
            author = random.choice(journal.authors.all()).user

        kwargs['content'] = test.factory.EntryContentCreationParams(
            template=template, author=author, node=node
        )['content']

        return kwargs


class TeacherEntryCreationParamsFactory(factory.Factory):
    """
    Creates valid entry creation parameters by tweaking the provided kwargs.
    kwargs:
        assignment: VLE.models.Assignment instance, assignment for which the teacher entry should be created.
        template: VLE.models.Template instance, fallsback to a random template available to the provided assignment.
        author: VLE.models.User instance, fallsback the assignment author.
        content: Valid content for the selected template.
        journals: list, can contain elements structured as follows:
            {
                'journal_id': <int>,
                'grade': <float>,
                'published': <bool>,
            },
            OR a list of VLE.models.Journal instances.
            Defaults to all assignment's journal ids, with a published grade of one.
            Grade and published can be uniformly changed by providing a grade and published kwarg
        categories: list of VLE.models.Category instances
        category_ids: list if VLE.models.Category ids, has prio over categories.
    """
    class Meta:
        model = dict

    title = factory.Faker('sentence')
    show_title_in_timeline = True

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        assignment = kwargs.pop('assignment')
        kwargs['assignment_id'] = assignment.pk

        template = kwargs.pop('template', random.choice(assignment.format.template_set.all()))
        kwargs['template_id'] = template.pk

        author = kwargs.pop('author', assignment.author)
        kwargs['content'] = test.factory.EntryContentCreationParams(template=template, author=author)['content']

        categories = kwargs.pop('categories', [])
        if categories:
            kwargs['category_ids'] = [category.pk for category in categories]
        kwargs['category_ids'] = kwargs.pop('category_ids', categories)

        def journal_to_dict(journal):
            return {
                'journal_id': journal.pk,
                'grade': kwargs['grade'] if 'grade' in kwargs else 1,
                'published': kwargs['published'] if 'published' in kwargs else True,
            }

        journals = kwargs.pop('journals', None)
        if journals and isinstance(journals, list) and isinstance(journals[0], VLE.models.Journal):
            kwargs['journals'] = [journal_to_dict(j) for j in journals]
        elif journals:
            kwargs['journals'] = journals
        else:
            kwargs['journals'] = [journal_to_dict(j) for j in VLE.models.Journal.objects.filter(assignment=assignment)]

        return kwargs
