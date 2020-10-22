"""
Serializers.

Functions to convert certain data to other formats.
"""
import datetime

from django.conf import settings
from django.db.models import Avg, Count, Min, Q, Sum
from django.utils import timezone
from rest_framework import serializers
from sentry_sdk import capture_message

import VLE.models
import VLE.permissions
import VLE.utils.generic_utils
import VLE.utils.statistics


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Instance
        fields = ('allow_standalone_registration', 'name')
        read_only_fields = ('id',)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.User
        fields = ('username', 'full_name', 'profile_picture', 'id',
                  'role', 'groups', 'is_test_student')
        read_only_fields = ('id', 'is_test_student')

    def get_role(self, user):
        if 'course' not in self.context or not self.context['course']:
            return None
        try:
            role = VLE.models.Participation.objects.get(user=user, course=self.context['course']).role
        except VLE.models.Participation.DoesNotExist:
            return None
        if role:
            return role.name
        else:
            return None

    def get_username(self, user):
        if 'user' not in self.context or not self.context['user']:
            return None

        if not (self.context['user'].is_supervisor_of(user) or self.context['user'] == user or
                # Usernames are required to add users to a course (not supervisor yet)
                'course' in self.context and self.context['user'].participation_set.filter(
                    role__can_add_course_users=True, course=self.context['course']).exists()):
            return None

        return user.username

    def get_profile_picture(self, user):
        if 'user' not in self.context or not self.context['user']:
            return settings.DEFAULT_PROFILE_PICTURE

        if not self.context['user'].can_view(user):
            return settings.DEFAULT_PROFILE_PICTURE

        return user.profile_picture

    def get_groups(self, user):
        if 'course' not in self.context or not self.context['course']:
            return None
        try:
            groups = VLE.models.Participation.objects.get(user=user, course=self.context['course']).groups
            return GroupSerializer(groups, many=True, context=self.context).data
        except VLE.models.Participation.DoesNotExist:
            return None


class OwnUserSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.User
        fields = ('id', 'username', 'full_name', 'email', 'permissions', 'is_test_student',
                  'lti_id', 'profile_picture', 'is_teacher', 'verified_email', 'is_superuser')
        read_only_fields = ('id', 'permissions', 'lti_id', 'is_teacher', 'is_superuser',
                            'verified_email', 'username', 'is_test_student')

    def get_permissions(self, user):
        """Returns a dictionary with all user permissions.

        Arguments:
        user -- The user whose permissions are requested.

        Returns {all_permission:
            course{id}: permisions
            assignment{id}: permissions
            general: permissions
        }"""
        perms = {}
        courses = user.participations.all()

        perms['general'] = VLE.permissions.serialize_general_permissions(user)

        for course in courses:
            if user.can_view(course):
                perms[f'course{course.id}'] = VLE.permissions.serialize_course_permissions(user, course)

        assignments = set()
        for course in courses:
            for assignment in course.assignment_set.all():
                if user.can_view(assignment):
                    assignments.add(assignment)

        for assignment in assignments:
            perms[f'assignment{assignment.pk}'] = VLE.permissions.serialize_assignment_permissions(
                user, assignment)

        return perms


class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Preferences
        fields = (
            'user',
            # Toggle preferences
            'auto_select_ungraded_entry', 'auto_proceed_next_journal', 'group_only_notifications',
            # notification preferences
            'new_grade_notifications', 'new_comment_notifications', 'new_entry_notifications',
            'new_course_notifications', 'new_assignment_notifications', 'new_node_notifications',
            'new_journal_import_request_notifications',
            # reminder preferences
            'upcoming_deadline_reminder',
            # Hidden preferences
            'show_format_tutorial', 'hide_version_alert', 'grade_button_setting', 'comment_button_setting',
        )
        read_only_fields = ('user', )


class CourseSerializer(serializers.ModelSerializer):
    lti_linked = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Course
        fields = ('id', 'name', 'abbreviation', 'startdate', 'enddate', 'lti_linked')
        read_only_fields = ('id', )

    def get_lti_linked(self, course):
        return course.has_lti_link()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Group
        fields = ('id', 'name', 'course')
        read_only_fields = ('id', 'course')


class AssignmentParticipationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    needs_lti_link = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.AssignmentParticipation
        fields = ('id', 'journal', 'assignment', 'user', 'needs_lti_link')
        read_only_fields = ('id', 'journal', 'assignment')

    def get_user(self, ap):
        return UserSerializer(ap.user, context=self.context).data

    def get_needs_lti_link(self, ap):
        return ap.needs_lti_link()


class ParticipationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Participation
        fields = ('id', 'user', 'course', 'role', 'groups',)
        read_only_fields = ('id', )

    def get_user(self, participation):
        return UserSerializer(participation.user, context=self.context).data

    def get_course(self, participation):
        return CourseSerializer(participation.course, context=self.context).data

    def get_role(self, participation):
        return RoleSerializer(participation.role, context=self.context).data

    def get_groups(self, participation):
        return GroupSerializer(participation.groups, many=True, context=self.context).data


class AssignmentSerializer(serializers.ModelSerializer):
    deadline = serializers.SerializerMethodField()
    journal = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    course_count = serializers.SerializerMethodField()
    journals = serializers.SerializerMethodField()
    active_lti_course = serializers.SerializerMethodField()
    lti_courses = serializers.SerializerMethodField()
    has_teacher_entries = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Assignment
        fields = (
            # Method fields
            'deadline', 'journal', 'stats', 'course', 'courses', 'course_count', 'journals', 'active_lti_course',
            'lti_courses', 'has_teacher_entries',
            # Model fields
            'id', 'name', 'description', 'is_published', 'points_possible', 'unlock_date', 'due_date', 'lock_date',
            'is_group_assignment', 'remove_grade_upon_leaving_group', 'can_set_journal_name', 'can_set_journal_image',
            'can_lock_journal',
            # Not used / missing: active_lti_id, lti_id_set, assigned_groups, format
        )
        read_only_fields = ('id', 'has_teacher_entries')

    def get_is_group_assignment(self, assignment):
        return assignment.is_group_assignment

    def get_deadline(self, assignment):
        # Student deadlines
        if 'user' in self.context and self.context['user'] and \
           self.context['user'].has_permission('can_have_journal', assignment):
            journal = VLE.models.Journal.objects.filter(
                assignment=assignment, authors__user=self.context['user']).first()
            deadline, name = self._get_student_deadline(journal, assignment)

            return {
                'date': deadline,
                'name': name
            }
        # Teacher deadline
        else:
            return {
                'date': self._get_teacher_deadline(assignment),
            }

    def _get_teacher_deadline(self, assignment):
        return VLE.models.Journal.objects.filter(assignment=assignment) \
            .filter(
                Q(node__entry__grade__grade__isnull=True) | Q(node__entry__grade__published=False),
                node__entry__isnull=False) \
            .values('node__entry__last_edited') \
            .aggregate(Min('node__entry__last_edited'))['node__entry__last_edited__min']

    def _get_student_deadline(self, journal, assignment):
        """Get student deadline.

        This function gets the first upcoming deadline.
        It checks for the first entrydeadline that still need to submitted and still can be, or for the first
        progressnode that is not yet fullfilled.
        """
        t_grade = 0
        deadline = None
        name = None

        if journal is not None:
            for node in VLE.utils.generic_utils.get_sorted_nodes(journal):
                if node.entry:
                    grade = node.entry.grade
                else:
                    grade = None

                # Sum published grades to check if PROGRESS node is fullfiled
                if node.type in [VLE.models.Node.ENTRY, VLE.models.Node.ENTRYDEADLINE] and grade and grade.grade:
                    if grade.published:
                        t_grade += grade.grade
                # Set the deadline to the first unfilled ENTRYDEADLINE node date
                elif node.type == VLE.models.Node.ENTRYDEADLINE \
                        and not node.entry and node.preset.due_date > timezone.now():
                    deadline = node.preset.due_date
                    name = node.preset.forced_template.name
                    break
                # Set the deadline to first not completed PROGRESS node date
                elif node.type == VLE.models.Node.PROGRESS:
                    if node.preset.target > t_grade and node.preset.due_date > timezone.now():
                        deadline = node.preset.due_date
                        name = "{:g}/{:g} points".format(t_grade, node.preset.target)
                        break

        # If no deadline is found, but the points possible has not been reached, make assignment due date the deadline
        if deadline is None and t_grade < assignment.points_possible:
            if assignment.due_date or \
               assignment.lock_date and assignment.lock_date < timezone.now():
                deadline = assignment.due_date
                name = 'End of assignment'

        return deadline, name

    def get_journal(self, assignment):
        if not ('user' in self.context and self.context['user']):
            return None
        if not self.context['user'].has_permission('can_have_journal', assignment):
            return None
        try:
            journal = VLE.models.Journal.objects.get(assignment=assignment, authors__user=self.context['user'])
            if not self.context['user'].can_view(journal):
                return None
            return journal.pk
        except VLE.models.Journal.DoesNotExist:
            return None

    def get_journals(self, assignment):
        """Retrieves the journals of an assignment."""
        if 'journals' in self.context and 'course' in self.context \
           and self.context['journals'] and self.context['course']:
            # Group assignment retrieves all journals
            if assignment.is_group_assignment:
                # First select all journals with authors, then add journals without any author
                journals = VLE.models.Journal.objects.filter(
                    Q(assignment=assignment, authors__isnull=False) |
                    Q(assignment=assignment, authors__isnull=True)
                )
            # Normal assignments should only get the journals of users that should have a journal
            else:
                journals = VLE.models.Journal.objects.filter(assignment=assignment)
            course = self.context['course']
            users = course.participation_set.filter(role__can_have_journal=True).values('user')
            return JournalSerializer(
                journals.filter(Q(authors__user__in=users) | Q(authors__isnull=True)).annotate(
                    author_count=Count('authors', distinct=True)
                ).distinct(), many=True,
                context={
                    **self.context,
                    'can_view_usernames': self.context['user'].has_permission('can_view_all_journals', assignment),
                    'can_manage_journal_import_requests': self.context['user'].has_permission(
                        'can_manage_journal_import_requests', assignment)
                }).data
        else:
            return None

    def get_stats(self, assignment):
        if 'user' not in self.context or not self.context['user']:
            return None

        course = self.context.get('course', None)
        if course is None:
            # Get the stats from only the course that it's linked to, when no courses are supplied.
            course = self._get_course(assignment)

        stats = {}

        # Upcoming specifically requests stats for all of the assignment's courses
        if 'course' in self.context and self.context['course'] is settings.EXPLICITLY_WITHOUT_CONTEXT:
            relevant_stat_users = VLE.utils.statistics.get_user_lists_with_scopes(
                assignment, self.context['user'])
        else:
            # We are not dealing explicitly without context, and we have no specific course, stats should not be needed.
            if course is None:
                return None
            relevant_stat_users = VLE.utils.statistics.get_user_lists_with_scopes(
                assignment, self.context['user'], course=course)

        all_j = VLE.models.Journal.objects.filter(assignment=assignment, authors__user__in=relevant_stat_users['all'])
        own_j = VLE.models.Journal.objects.filter(assignment=assignment, authors__user__in=relevant_stat_users['own'])

        all_j_stats = all_j.aggregate(
            average_points=Avg('grade'),
            needs_marking=Sum('needs_marking'),
            unpublished=Sum('unpublished'),
            import_requests=Sum('import_requests'),
        )
        own_j_stats = own_j.aggregate(
            needs_marking=Sum('needs_marking'),
            unpublished=Sum('unpublished'),
            import_requests=Sum('import_requests'),
        )

        # Grader stats
        if self.context['user'].has_permission('can_grade', assignment):
            stats.update({
                'needs_marking': all_j_stats['needs_marking'] or 0,
                'unpublished': all_j_stats['unpublished'] or 0,
                'needs_marking_own_groups': own_j_stats['needs_marking'] or 0,
                'unpublished_own_groups': own_j_stats['unpublished'] or 0,
            })
        if self.context['user'].has_permission('can_manage_journal_import_requests', assignment):
            stats.update({
                'import_requests': all_j_stats['import_requests'] or 0,
                'import_requests_own_groups': own_j_stats['import_requests'] or 0,
            })
        # Other stats
        stats['average_points'] = all_j_stats['average_points']

        return stats

    def get_course(self, assignment):
        return CourseSerializer(self._get_course(assignment)).data

    def _get_course(self, assignment):
        course = self.context.get('course', None)
        if course is None or course == settings.EXPLICITLY_WITHOUT_CONTEXT:
            if self.context.get('user', None) is not None:
                return assignment.get_active_course(self.context['user'])
            else:
                return None
        elif not self.context['course'] in assignment.courses.all():
            raise VLE.utils.error_handling.VLEProgrammingError('Wrong course is supplied.')
        elif not self.context['user'].can_view(self.context['course']):
            raise VLE.utils.error_handling.VLEParticipationError(self.context['course'], self.context['user'])

        return self.context['course']

    def get_courses(self, assignment):
        if 'course' in self.context and self.context['course'] \
                and not self.context['course'] == settings.EXPLICITLY_WITHOUT_CONTEXT:
            return None
        return CourseSerializer(assignment.courses, many=True).data

    def get_active_lti_course(self, assignment):
        if 'user' in self.context and self.context['user'] and \
           self.context['user'].can_view(assignment):
            c = assignment.get_active_lti_course()
            if c:
                return {'cID': c.pk, 'name': c.name}
            return None
        return None

    def get_lti_courses(self, assignment):
        if 'user' in self.context and self.context['user'] and \
           self.context['user'].has_permission('can_edit_assignment', assignment):
            courses = assignment.courses.filter(assignment_lti_id_set__overlap=assignment.lti_id_set)
            return {c.pk: c.name for c in courses}
        return None

    def get_course_count(self, assignment):
        return assignment.courses.count()

    def get_has_teacher_entries(self, assignment):
        if 'user' not in self.context or not self.context['user'] or not self.context['user'].has_permission(
            'can_post_teacher_entries', assignment
        ):
            return False
        return assignment.teacherentry_set.exists()


class AssignmentFormatSerializer(AssignmentSerializer):
    lti_count = serializers.SerializerMethodField()
    can_change_type = serializers.SerializerMethodField()
    assigned_groups = serializers.SerializerMethodField()
    all_groups = serializers.SerializerMethodField()
    templates = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Assignment
        fields = ('id', 'name', 'description', 'points_possible', 'unlock_date', 'due_date', 'lock_date',
                  'is_published', 'course_count', 'lti_count', 'active_lti_course', 'is_group_assignment',
                  'can_set_journal_name', 'can_set_journal_image', 'can_lock_journal', 'can_change_type',
                  'remove_grade_upon_leaving_group', 'assigned_groups', 'all_groups', 'templates')
        read_only_fields = ('id', )

    def get_assigned_groups(self, assignment):
        if self.context.get('course', None):
            return GroupSerializer(assignment.assigned_groups.filter(course=self.context['course']), many=True).data
        return GroupSerializer(assignment.assigned_groups, many=True).data

    def get_all_groups(self, assignment):
        if self.context.get('course', None):
            return GroupSerializer(VLE.models.Group.objects.filter(course=self.context['course']), many=True).data
        return GroupSerializer(VLE.models.Group.objects.filter(course__in=assignment.courses.all()), many=True).data

    def get_lti_count(self, assignment):
        if 'user' in self.context and self.context['user'] and \
           self.context['user'].has_permission('can_edit_assignment', assignment):
            return len(assignment.lti_id_set)
        return None

    def get_can_change_type(self, assignment):
        return not assignment.has_entries()

    def get_templates(self, assignment):
        return list(assignment.format.template_set.values('id', 'name'))


class SmallAssignmentSerializer(AssignmentSerializer):
    class Meta:
        model = VLE.models.Assignment
        fields = (
            'id', 'name', 'is_group_assignment', 'is_published', 'points_possible', 'unlock_date', 'due_date',
            'lock_date', 'deadline', 'journal', 'stats', 'course', 'courses', 'active_lti_course')
        read_only_fields = fields


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    last_edited_by = serializers.SerializerMethodField()
    last_edited = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Comment
        fields = ('id', 'entry', 'author', 'text', 'published', 'creation_date', 'last_edited', 'last_edited_by',
                  'can_edit', 'files')
        read_only_fields = ('id', 'entry', 'author', 'creation_date', 'last_edited')

    def get_author(self, comment):
        return UserSerializer(comment.author, context=self.context).data

    def get_last_edited_by(self, comment):
        if comment.last_edited > comment.creation_date + datetime.timedelta(minutes=3):
            return comment.last_edited_by.full_name

    def get_last_edited(self, comment):
        if comment.last_edited > comment.creation_date + datetime.timedelta(minutes=3):
            return comment.last_edited

    def get_files(self, comment):
        return FileSerializer(comment.attached_files, many=True).data

    def get_can_edit(self, comment):
        user = self.context.get('user', None)
        if not user:
            return False

        return comment.can_edit(user)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Role
        # Get name, course, and all permissions
        fields = ('id', 'name', 'course', ) + tuple(VLE.models.Role.PERMISSIONS)
        read_only_fields = ('id', 'course')


class JournalSerializer(serializers.ModelSerializer):
    author_count = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    usernames = serializers.SerializerMethodField()
    import_requests = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Journal
        fields = (
            # Normal fields
            'id', 'bonus_points', 'author_limit', 'locked',
            # Computed fields
            'grade', 'name', 'image', 'needs_lti_link', 'unpublished', 'needs_marking', 'full_names', 'groups',
            # Serialized fields
            'author_count', 'import_requests', 'usernames'
        )
        read_only_fields = ('id', 'assignment', 'authors', 'grade', 'import_requests')

    def get_author_count(self, journal):
        # If annotated in the query, get that, else query here
        if ('author_count' in journal.__dict__):
            return journal.__dict__.get('author_count')
        return journal.authors.count()

    def get_usernames(self, journal):
        # If annotated that it is allowed, immediatly get it, else check for can_view_all_journals
        if self.context.get('can_view_usernames', False) or \
           'user' in self.context and self.context['user'].has_permission('can_view_all_journals', journal.assignment):
            return journal.usernames

        return None

    def get_groups(self, journal):
        if 'course' not in self.context:
            return None
        return journal.groups

    def get_import_requests(self, journal):
        if self.context.get('can_manage_journal_import_requests', False) or \
            'user' in self.context and self.context['user'] and self.context['user'].has_permission(
                'can_manage_journal_import_requests', journal.assignment):
            return journal.import_requests
        return None


class FormatSerializer(serializers.ModelSerializer):
    presets = serializers.SerializerMethodField()
    templates = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Format
        fields = ('id', 'templates', 'presets', )
        read_only_fields = ('id', )

    def get_templates(self, format):
        return TemplateSerializer(format.template_set.filter(archived=False).order_by('name'), many=True).data

    def get_presets(self, format):
        return PresetNodeSerializer(format.presetnode_set.all().order_by('due_date'), many=True).data


class PresetNodeSerializer(serializers.ModelSerializer):
    unlock_date = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()
    lock_date = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.PresetNode
        fields = ('id', 'description', 'type', 'unlock_date', 'due_date', 'lock_date', 'target', 'template',
                  'files')
        read_only_fields = ('id', 'type')

    def get_unlock_date(self, node):
        if node.type == VLE.models.Node.ENTRYDEADLINE and node.unlock_date is not None:
            return node.unlock_date.strftime('%Y-%m-%dT%H:%M')
        return None

    def get_due_date(self, node):
        return node.due_date.strftime('%Y-%m-%dT%H:%M:%S')

    def get_lock_date(self, node):
        if node.type == VLE.models.Node.ENTRYDEADLINE and node.lock_date is not None:
            return node.lock_date.strftime('%Y-%m-%dT%H:%M:%S')
        return None

    def get_target(self, node):
        if node.type == VLE.models.Node.PROGRESS:
            return node.target
        return None

    def get_template(self, node):
        if node.type == VLE.models.Node.ENTRYDEADLINE:
            return TemplateSerializer(node.forced_template).data
        return None

    def get_files(self, node):
        return FileSerializer(node.attached_files, many=True).data


class EntrySerializer(serializers.ModelSerializer):
    template = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    last_edited_by = serializers.SerializerMethodField()
    jir = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Entry
        fields = ('id', 'creation_date', 'template', 'title', 'content', 'editable',
                  'grade', 'last_edited', 'comments', 'author', 'last_edited_by', 'jir')
        read_only_fields = ('id', 'template', 'creation_date', 'content', 'grade')

    def get_author(self, entry):
        return entry.author.full_name if entry.author is not None else 'Unknown or deleted account'

    def get_last_edited_by(self, entry):
        return entry.last_edited_by.full_name if entry.last_edited_by else 'Unknown or deleted account'

    def get_template(self, entry):
        return TemplateSerializer(entry.template).data

    def get_title(self, entry):
        if (entry.teacher_entry and entry.teacher_entry.show_title_in_timeline):
            return entry.teacher_entry.title

        return entry.template.name

    def get_content(self, entry):
        def _get_content(entry):
            content_dict = {}
            for content in entry.content_set.all():
                # Only include the actual content (so e.g. text).
                if content.field.type == VLE.models.Field.FILE and content.data:
                    try:
                        content_dict[content.field.id] = FileSerializer(
                            VLE.models.FileContext.objects.get(pk=content.data)).data
                    except VLE.models.FileContext.DoesNotExist:
                        capture_message(
                            f'FILE content {content.pk} refers to unknown file in data: {content.data}', level='error')
                        return {}
                else:
                    content_dict[content.field.id] = content.data

            return content_dict
        content_dict = {}
        # If it is a teacher entry, initialize the content with the content of the teacher entry
        # Only when a user changed the content, set the new content
        if entry.teacher_entry:
            content_dict.update(_get_content(entry.teacher_entry))
        content_dict.update(_get_content(entry))
        return content_dict

    def get_editable(self, entry):
        return entry.is_editable()

    def get_grade(self, entry):
        # TODO: Add permission can_view_grade
        if 'user' not in self.context or not self.context['user']:
            return None
        grade = entry.grade
        if grade and (grade.published or
                      self.context['user'].has_permission('can_grade', entry.node.journal.assignment)):
            return GradeSerializer(grade).data
        return None

    def get_comments(self, entry):
        if 'comments' not in self.context or not self.context['comments']:
            return None
        return CommentSerializer(entry.comment_set.all(), many=True).data

    def get_jir(self, entry):
        if entry.jir:
            return {
                'source': {
                    'assignment': AssignmentSerializer(entry.jir.source.assignment, context=self.context).data,
                },
                'processor': UserSerializer(entry.jir.processor, context=self.context).data
            }
        return None


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Grade
        fields = ('id', 'entry', 'grade', 'published')
        read_only_fields = fields


class TeacherEntryGradeSerializer(serializers.ModelSerializer):
    journal_id = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    published = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    usernames = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Entry
        fields = ('journal_id', 'grade', 'published', 'name', 'usernames')
        read_only_fields = fields

    def get_journal_id(self, entry):
        return entry.node.journal.pk

    def get_grade(self, entry):
        return entry.grade.grade if entry.grade else None

    def get_published(self, entry):
        return entry.grade.published if entry.grade else False

    def get_name(self, entry):
        return entry.node.journal.name

    def get_usernames(self, entry):
        return entry.node.journal.usernames


class GradeHistorySerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Grade
        fields = ('grade', 'published', 'creation_date', 'author')
        read_only_fields = ('grade', 'published', 'creation_date', 'author')

    def get_author(self, grade):
        if grade.author is not None:
            return grade.author.full_name

        return 'Unknown or deleted account'


class TeacherEntrySerializer(EntrySerializer):
    journals = serializers.SerializerMethodField()
    # This is to overwrite the EntrySerializer serializedmethod title field, and use the db variable instead
    title = None

    class Meta:
        model = VLE.models.TeacherEntry
        fields = ('id', 'title', 'template', 'content', 'journals')
        read_only_fields = fields

    def get_journals(self, teacher_entry):
        return TeacherEntryGradeSerializer(
            teacher_entry.entry_set.all().select_related('node__journal', 'grade').order_by('node__journal__name'),
            many=True
        ).data


class TemplateSerializer(serializers.ModelSerializer):
    field_set = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.Template
        fields = ('id', 'name', 'preset_only', 'archived', 'field_set')
        read_only_fields = ('id', )

    def get_field_set(self, template):
        return FieldSerializer(template.field_set.all().order_by('location'), many=True).data


class FileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.FileContext
        fields = ('download_url', 'file_name', 'id', )
        read_only_fields = fields

    def get_download_url(self, file):
        # Get access_id if file is in rich text
        return file.download_url(access_id=file.in_rich_text)


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Field
        fields = ('id', 'type', 'title', 'description', 'options', 'location', 'required', )
        read_only_fields = fields


class JournalImportRequestSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    processor = serializers.SerializerMethodField()

    class Meta:
        model = VLE.models.JournalImportRequest
        fields = ('id', 'source', 'target', 'author', 'processor')
        read_only_fields = ('id', 'source', 'target', 'author', 'processor')

    def get_author(self, jir):
        return UserSerializer(jir.author, context=self.context).data

    def get_processor(self, jir):
        return UserSerializer(jir.processor, context=self.context).data

    def get_source(self, jir):
        if jir.source is None:
            return 'Source journal no longer exists.'

        return {
            'journal': JournalSerializer(jir.source, context=self.context).data,
            'assignment': SmallAssignmentSerializer(jir.source.assignment, context=self.context).data,
        }

    def get_target(self, jir):
        return {
            'journal': JournalSerializer(jir.target, context=self.context).data,
            'assignment': SmallAssignmentSerializer(jir.target.assignment, context=self.context).data,
        }
