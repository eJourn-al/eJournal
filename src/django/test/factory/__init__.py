from test.factory.assignment import AssignmentFactory, GroupAssignmentFactory, LtiAssignmentFactory
from test.factory.comment import StudentCommentFactory, TeacherCommentFactory
from test.factory.course import CourseFactory, LtiCourseFactory
from test.factory.entry import EntryFactory, PresetEntryFactory
from test.factory.file_context import (AttachedCommentFileContextFactory, FileContextFactory,
                                       RichTextCommentFileContextFactory)
from test.factory.format import FormatFactory
from test.factory.grade import GradeFactory
from test.factory.group import GroupFactory, LtiGroupFactory
from test.factory.instance import InstanceFactory
from test.factory.journal import (GroupJournalFactory, JournalFactory, JournalImportRequestFactory, LtiJournalFactory,
                                  PopulatedJournalFactory)
from test.factory.params import JWTParamsFactory, JWTTestUserParamsFactory, UserParamsFactory
from test.factory.participation import AssignmentParticipationFactory, GroupParticipationFactory, ParticipationFactory
from test.factory.presetnode import EntrydeadlineNodeFactory, ProgressNodeFactory
from test.factory.role import RoleFactory, StudentRoleFactory
from test.factory.template import TemplateAllTypesFactory, TemplateFactory
from test.factory.user import (AdminFactory, LtiStudentFactory, LtiTeacherFactory, TeacherFactory, TestUserFactory,
                               UserFactory)

Instance = InstanceFactory
Assignment = AssignmentFactory
LtiAssignment = LtiAssignmentFactory
GroupAssignment = GroupAssignmentFactory
Course = CourseFactory
LtiCourse = LtiCourseFactory

Student = UserFactory
TestUser = TestUserFactory
LtiStudent = LtiStudentFactory
LtiTeacher = LtiTeacherFactory
Teacher = TeacherFactory
Admin = AdminFactory
Role = RoleFactory
StudentRole = StudentRoleFactory

Group = GroupFactory
LtiGroup = LtiGroupFactory

Participation = ParticipationFactory
GroupParticipation = GroupParticipationFactory
AssignmentParticipation = AssignmentParticipationFactory

Journal = JournalFactory
LtiJournal = LtiJournalFactory
GroupJournal = GroupJournalFactory
PopulatedJournal = PopulatedJournalFactory
Format = FormatFactory
Template = TemplateFactory
TemplateAllTypes = TemplateAllTypesFactory
ProgressNode = ProgressNodeFactory
EntrydeadlineNode = EntrydeadlineNodeFactory

Entry = EntryFactory
PresetEntry = PresetEntryFactory
StudentComment = StudentCommentFactory
TeacherComment = TeacherCommentFactory
Grade = GradeFactory

UserParams = UserParamsFactory
JWTParams = JWTParamsFactory
JWTTestUserParams = JWTTestUserParamsFactory

JournalImportRequest = JournalImportRequestFactory

FileContext = FileContextFactory
RichTextCommentFileContext = RichTextCommentFileContextFactory
AttachedCommentFileContext = AttachedCommentFileContextFactory
