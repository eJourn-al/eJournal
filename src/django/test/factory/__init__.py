# NOTE: Factory postgeneration methods and related factories are executed in reverse order compared to normal
# inheritence. So class A(), class B(A) -> The methods and related factories of A are executed first!
# Inherited post generation methods take presedence of inherited related factories, despite initial declaration order.
# If Params are defined (with traits), post generation methods take presedence over related factories (inc base class)
# This means traits cannot be combined with post generation methods and related factories, if the related factories
# set values required in the post generation methods.

# TODO JIR: CHeck if save in post generation methods is actually unneeded (and duplicate) cause
# save is called anyway ins post generation hook


# TODO JIR: use rel factory in factories
# # Should simply be callable as test.factory.rel_factory(self, create, extracted, 'grade', VLE.models.Grade)
def rel_factory(instance, create, extracted, key, model, factory=None, size=1, non_cond_kwargs={}, cond_kwargs={},
                default=None, **kwargs):
    '''
    Default RelatedFactory is lacking

    - Cannot pass size as a keyword to the related factory: https://github.com/FactoryBoy/factory_boy/issues/767
    - Cannot make a conditional related factory except using Traits, which do not support deep syntax

    Args:
        instance (VLE.model instance): created instance
        create (bool): Post generation flag indicating whether we are building the object or creating
        extracted (obj): Exact match for the post generation method name
        key (str): Model instance field (fk) key to update
        model (VLE.model): VLE.model of which the fk will be updated
        factory (factory.django.DjangoModelFactory): Factory used to created the instances field (fk) instance
        size (int): Number of fk field instances to initiate
        default (obj): If no exact match is found or deep syntax arguments are given, set instance attr to this value.
    '''
    if not create:
        return

    if isinstance(extracted, model):
        setattr(instance, key, extracted)
    elif not (kwargs or non_cond_kwargs or cond_kwargs) and default:
        setattr(instance, key, default)
    else:
        # TODO Handle size more cleanly
        if size == 1:
            setattr(instance, key, factory(**{**cond_kwargs, **kwargs, **non_cond_kwargs}))
        else:
            for _ in range(size):
                factory(**{**cond_kwargs, **kwargs, **non_cond_kwargs})

    instance.save()


from test.factory.assignment import AssignmentFactory as Assignment  # noqa: F401
from test.factory.assignment import LtiAssignmentFactory as LtiAssignment  # noqa: F401
from test.factory.comment import StudentCommentFactory as StudentComment  # noqa: F401
from test.factory.comment import TeacherCommentFactory as TeacherComment  # noqa: F401
from test.factory.content import ContentFactory as Content  # noqa: F401
from test.factory.course import CourseFactory as Course  # noqa: F401
from test.factory.course import LtiCourseFactory as LtiCourse  # noqa: F401
from test.factory.entry import PresetEntryFactory as PresetEntry  # noqa: F401
from test.factory.entry import UnlimitedEntryFactory as UnlimitedEntry  # noqa: F401
from test.factory.field import DateFieldFactory as DateField  # noqa: F401
from test.factory.field import DateTimeFieldFactory as DateTimeField  # noqa: F401
from test.factory.field import FieldFactory as Field  # noqa: F401
from test.factory.field import FileFieldFactory as FileField  # noqa: F401
from test.factory.field import NoSubmissionFieldFactory as NoSubmissionField  # noqa: F401
from test.factory.field import RichTextFieldFactory as RichTextField  # noqa: F401
from test.factory.field import SelectionFieldFactory as SelectionField  # noqa: F401
from test.factory.field import TextFieldFactory as TextField  # noqa: F401
from test.factory.field import UrlFieldFactory as UrlField  # noqa: F401
from test.factory.field import VideoFieldFactory as VideoField  # noqa: F401
from test.factory.file_context import AttachedCommentFileContextFactory as AttachedCommentFileContext  # noqa: F401
from test.factory.file_context import FileContentFileContextFactory as FileContentFileContext  # noqa: F401
from test.factory.file_context import FileContextFactory as FileContext  # noqa: F401
from test.factory.file_context import RichTextCommentFileContextFactory as RichTextCommentFileContext  # noqa: F401
from test.factory.file_context import RichTextContentFileContextFactory as RichTextContentFileContext  # noqa: F401
from test.factory.format import FormatFactory as Format  # noqa: F401
from test.factory.grade import GradeFactory as Grade  # noqa: F401
from test.factory.group import GroupFactory as Group  # noqa: F401
from test.factory.group import LtiGroupFactory as LtiGroup  # noqa: F401
from test.factory.instance import InstanceFactory as Instance  # noqa: F401
from test.factory.journal import GroupJournalFactory as GroupJournal  # noqa: F401
from test.factory.journal import JournalFactory as Journal  # noqa: F401
from test.factory.journal import JournalImportRequestFactory as JournalImportRequest  # noqa: F401
from test.factory.journal import LtiJournalFactory as LtiJournal  # noqa: F401
from test.factory.params import JWTParamsFactory as JWTParams  # noqa: F401
from test.factory.params import JWTTestUserParamsFactory as JWTTestUserParams  # noqa: F401
from test.factory.params import UserParamsFactory as UserParams  # noqa: F401
from test.factory.participation import AssignmentParticipationFactory as AssignmentParticipation  # noqa: F401
from test.factory.participation import GroupParticipationFactory as GroupParticipation  # noqa: F401
from test.factory.participation import ParticipationFactory as Participation  # noqa: F401
from test.factory.presetnode import DeadlinePresetNodeFactory as DeadlinePresetNode  # noqa: F401
from test.factory.presetnode import ProgressPresetNodeFactory as ProgressPresetNode  # noqa: F401
from test.factory.role import RoleFactory as Role  # noqa: F401
from test.factory.role import StudentRoleFactory as StudentRole  # noqa: F401
from test.factory.template import ColloquiumTemplateFactory as ColloquiumTemplate  # noqa: F401
from test.factory.template import TemplateAllTypesFactory as TemplateAllTypes  # noqa: F401
from test.factory.template import TemplateFactory as Template  # noqa: F401
from test.factory.template import TextTemplateFactory as TextTemplate  # noqa: F401
from test.factory.user import AdminFactory as Admin  # noqa: F401
from test.factory.user import LtiStudentFactory as LtiStudent  # noqa: F401
from test.factory.user import LtiTeacherFactory as LtiTeacher  # noqa: F401
from test.factory.user import TeacherFactory as Teacher  # noqa: F401
from test.factory.user import TestUserFactory as TestUser  # noqa: F401
from test.factory.user import UserFactory as Student  # noqa: F401
