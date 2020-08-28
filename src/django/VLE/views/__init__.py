from rest_framework import routers

from VLE.views.assignment import AssignmentView
from VLE.views.comment import CommentView
from VLE.views.course import CourseView
from VLE.views.entry import EntryView
from VLE.views.file import FileView
from VLE.views.format import FormatView
from VLE.views.grade import GradeView
from VLE.views.group import GroupView
from VLE.views.instance import InstanceView
from VLE.views.journal import JournalView
from VLE.views.journal_import_request import JournalImportRequestView
from VLE.views.member import MemberView
from VLE.views.node import NodeView
from VLE.views.participation import ParticipationView
from VLE.views.preferences import PreferencesView
from VLE.views.role import RoleView
from VLE.views.user import UserView

router = routers.DefaultRouter()
router.register(r'instance', InstanceView, basename='instance')
router.register(r'courses', CourseView, basename='course')
router.register(r'groups', GroupView, basename='group')
router.register(r'members', MemberView, basename='member')
router.register(r'roles', RoleView, basename='role')
router.register(r'users', UserView, basename='user')
router.register(r'assignments', AssignmentView, basename='assignment')
router.register(r'nodes', NodeView, basename='node')
router.register(r'comments', CommentView, basename='comment')
router.register(r'participations', ParticipationView, basename='participation')
router.register(r'preferences', PreferencesView, basename='preferences')
router.register(r'journals', JournalView, basename='journal')
router.register(r'entries', EntryView, basename='entry')
router.register(r'grades', GradeView, basename='grades')
router.register(r'formats', FormatView, basename='format')
router.register(r'files', FileView, basename='file')
router.register(r'journal_import_request', JournalImportRequestView, basename='journal_import_request')

urlpatterns = router.urls
