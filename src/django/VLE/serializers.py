"""
Serializers.

Functions to convert certain data to other formats.
"""
import datetime

from django.conf import settings
from django.db.models import Avg, Count, Prefetch, QuerySet, Sum
from rest_framework import serializers
from sentry_sdk import capture_message

import VLE.models
import VLE.permissions
import VLE.utils.generic_utils
import VLE.utils.statistics
from VLE.utils.error_handling import VLEProgrammingError


def prefetched_objects(instance, name, default=None):
    """
    Use when Django does not make use of an queries instance cache (prefetch_related) when it should.

    E.g. the queryset is modified but the prefetch is still valid.

    Args:
        instance (model instance)
        name (str), key expected to be present in the instance cache
        default, value to be returned if the key is not preset in the cache, None by default

    Returns a tuple
        0: values of the cache keyed by name, None by default (or the given default)
        1: (bool), whether the name was found in the instance cache and it was populated sucesfully
    """
    if hasattr(instance, '_prefetched_objects_cache') and name in instance._prefetched_objects_cache:
        return instance._prefetched_objects_cache[name], bool(instance._prefetched_objects_cache[name])

    return default, False


class EagerLoadingMixin:
    """
    Mixin Class that performs eager loading for serializers with O2O, O2M and M2M relationships.
    """
    @classmethod
    def setup_eager_loading(cls, queryset):
        """
        Perform eager loading of model data for nested serializers.

        Args:
        queryset (Queryset): the model queryset

        Returns: queryset containing a prefetch cache
        """
        if hasattr(cls, 'select_related'):
            queryset = queryset.select_related(*cls.select_related)

        if hasattr(cls, 'prefetch_related'):
            queryset = queryset.prefetch_related(*cls.prefetch_related)

        if hasattr(cls, 'order_by'):
            queryset = queryset.order_by(*cls.order_by)

        return queryset


class WriteOnceMixin:
    """
    Adds support for write once fields to serializers.

    To use it, specify a list of fields as `write_once_fields` on the
    serializer's Meta:
    ```
    class Meta:
        model = SomeModel
        fields = '__all__'
        write_once_fields = ('collection', )
    ```

    Now the fields in `write_once_fields` can be set during POST (create),
    but cannot be changed afterwards via PUT or PATCH (update).
    """
    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()

        # We're only interested in PATCH/PUT.
        if 'update' in getattr(self.context.get('view'), 'action', ''):
            return self._set_write_once_fields(extra_kwargs)

        return extra_kwargs

    def _set_write_once_fields(self, extra_kwargs):
        """Set all fields in `Meta.write_once_fields` to read_only."""
        write_once_fields = getattr(self.Meta, 'write_once_fields', None)
        if not write_once_fields:
            return extra_kwargs

        if not isinstance(write_once_fields, (list, tuple)):
            raise TypeError(
                'The `write_once_fields` option must be a list or tuple. '
                'Got {}.'.format(type(write_once_fields).__name__)
            )

        for field_name in write_once_fields:
            kwargs = extra_kwargs.get(field_name, {})
            kwargs['read_only'] = True
            extra_kwargs[field_name] = kwargs

        return extra_kwargs


class ExtendedModelSerializer(serializers.ModelSerializer):
    """
    Enforces context to be set if defined as 'enforced_context' on the class

    NOTE: Cannot be shifted to __init__ or __new__, nested serializer fields are initialized but receive context later.
    """

    def enforce_context(self):
        if hasattr(self, 'enforced_context'):
            for context in self.enforced_context:
                if context not in self.context:
                    raise VLEProgrammingError(f'Enforced context `{context}` not set')

    def to_representation(self, instance):
        """Read operations"""
        self.enforce_context()
        return super().to_representation(instance)

    def to_internal_value(self, data):
        """Write operations"""
        self.enforce_context()
        return super().to_internal_value(data)


class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Instance
        fields = ('allow_standalone_registration', 'name', 'kaltura_url')
        read_only_fields = ()


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Role
        # Get name, course, and all permissions
        fields = ('id', 'name', 'course',) + tuple(VLE.models.Role.PERMISSIONS)
        read_only_fields = ('course',)


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Field
        fields = ('id', 'type', 'title', 'description', 'options', 'location', 'required',)
        read_only_fields = fields


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.FileContext
        fields = ('download_url', 'file_name', 'id',)
        read_only_fields = fields

    download_url = serializers.SerializerMethodField()

    def get_download_url(self, file):
        # Get access_id if file is in rich text
        return file.download_url(access_id=file.in_rich_text)


class TemplateConcreteFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Template
        fields = (
            'id',
            'name',
            'format',
            'preset_only',
            'archived',
        )
        read_only_fields = fields


class CategoryConcreteFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Category
        fields = (
            'id',
            'name',
            'description',
            'color',
        )
        read_only_fields = fields


class CategorySerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Category
        fields = (
            *CategoryConcreteFieldsSerializer.Meta.fields,
            'templates',
        )
        read_only_fields = ()

    prefetch_related = [
        Prefetch('templates', queryset=VLE.models.Template.objects.filter(archived=False)),
    ]

    templates = TemplateConcreteFieldsSerializer(many=True, read_only=True)


class TemplateSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Template
        fields = (
            *TemplateConcreteFieldsSerializer.Meta.fields,
            'allow_custom_categories',
            'allow_custom_title',
            'title_description',
            'default_grade',
            'field_set',
            'categories',
        )
        read_only_fields = ()

    select_related = [
        'chain',
    ]

    prefetch_related = [
        'categories',
        Prefetch('field_set', queryset=VLE.models.Field.objects.order_by('location')),
    ]

    allow_custom_categories = serializers.BooleanField(source='chain.allow_custom_categories')
    allow_custom_title = serializers.BooleanField(source='chain.allow_custom_title')
    title_description = serializers.CharField(source='chain.title_description')
    default_grade = serializers.FloatField(source='chain.default_grade')
    field_set = FieldSerializer(many=True, read_only=True)
    categories = CategoryConcreteFieldsSerializer(many=True, read_only=True)


class UserSerializer(ExtendedModelSerializer):
    class Meta:
        model = VLE.models.User

        user_fields = (
            'id',
            'is_test_student',
            'full_name',
            'username',
            'profile_picture',
        )
        course_specific_fields = (
            'role',
            'groups',
        )
        fields = (
            *user_fields,
            *course_specific_fields,
        )
        read_only_fields = ('is_test_student',)

    enforced_context = [
        'user',
    ]

    username = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        """
        Addresses some issues (in conjunction with `many_init`) with using the same serializer for two types:
            UserSerializer (generic user serializer, no course context specified)
            CourseUserSerializer (serialize a user as part of a specific course)
        """
        super(UserSerializer, self).__init__(*args, **kwargs)

        if 'course' not in self.context:
            for field in self.Meta.course_specific_fields:
                self.fields.pop(field)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        Called when many=True, used to initialize a ListSerializer which will handle each of the elems in turn.
        For read operations, it is important repeated information is added to the queryset before the ListSerializer
        is initialized, otherwise each child will execute the same logic or queries.
        """
        if args and isinstance(args[0], QuerySet):
            course = kwargs.get('context', {}).get('course')
            if course:
                qry, *rest = args
                qry = qry.prefetch_course_groups(course)
                qry = qry.annotate_course_role(course)
                args = (qry, *rest)

        return super().many_init(*args, **kwargs)

    def get_username(self, user):
        course = self.context.get('course')
        request_user = self.context.get('user')

        if not (request_user == user or request_user.is_supervisor_of(user) or course
                # Usernames are required to add users to a course (not supervisor yet)
                and request_user.participation_set.filter(role__can_add_course_users=True, course=course).exists()):
            return None

        return user.username

    def get_role(self, user):
        """Only serialized if course is set in context"""
        if hasattr(user, 'role_name'):
            return user.role_name

        try:
            role = VLE.models.Participation.objects.get(user=user, course=self.context['course']).role
        except VLE.models.Participation.DoesNotExist:
            return None
        return role.name if role else None

    def get_groups(self, user):
        """Only serialized if course is set in context"""
        values, prefetched = prefetched_objects(user, 'participation_set')
        # The participation_set is prefetched filtered on the course so we can simply take the first element if found.
        if prefetched:
            participation = values[0]
        else:
            try:
                participation = VLE.models.Participation.objects.get(user=user, course=self.context['course'])
            except VLE.models.Participation.DoesNotExist:
                return None

        return GroupSerializer(participation.groups.all(), many=True, context=self.context, read_only=True).data


class OwnUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.User
        fields = ('id', 'username', 'full_name', 'email', 'permissions', 'is_test_student',
                  'lti_id', 'profile_picture', 'is_teacher', 'verified_email', 'is_superuser')
        read_only_fields = ('lti_id', 'is_teacher', 'is_superuser', 'verified_email', 'username', 'is_test_student')

    permissions = serializers.SerializerMethodField()

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
            # Notification preferences
            'new_grade_notifications', 'new_comment_notifications', 'new_entry_notifications',
            'new_course_notifications', 'new_assignment_notifications', 'new_node_notifications',
            'new_journal_import_request_notifications',
            # Reminder preferences
            'upcoming_deadline_reminder',
            # Hidden preferences
            'show_format_tutorial', 'hide_version_alert', 'grade_button_setting', 'comment_button_setting',
            'hide_past_deadlines_of_assignments',
        )
        read_only_fields = ('user',)

    hide_past_deadlines_of_assignments = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=False,
        queryset=VLE.models.Assignment.objects.all(),
    )


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Course
        fields = ('id', 'name', 'abbreviation', 'startdate', 'enddate', 'lti_linked')
        read_only_fields = ()

    lti_linked = serializers.BooleanField(source='has_lti_link')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Group
        fields = ('id', 'name', 'course')
        read_only_fields = ('course',)


class AssignmentParticipationSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.AssignmentParticipation
        fields = ('id', 'journal', 'assignment', 'user', 'needs_lti_link')
        read_only_fields = ('journal', 'assignment',)

    select_related = [
        'assignment',
        'user',
    ]

    user = UserSerializer(read_only=True)
    needs_lti_link = serializers.BooleanField()


class ParticipationSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Participation
        fields = ('id', 'user', 'course', 'role', 'groups',)
        read_only_fields = ()

    select_related = [
        'user',
        'course',
        'role',
    ]

    prefetch_related = [
        'groups'
    ]

    user = UserSerializer()
    course = CourseSerializer()
    role = RoleSerializer()
    groups = GroupSerializer(many=True)


class PresetNodeSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.PresetNode
        fields = (
            'id',
            'description',
            'type',
            'unlock_date',
            'due_date',
            'lock_date',
            'target',
            'template',
            'attached_files',
            'display_name',
        )
        read_only_fields = ('type',)

    select_related = []

    prefetch_related = [
        Prefetch('forced_template', queryset=TemplateSerializer.setup_eager_loading(VLE.models.Template.objects.all())),
        'attached_files',
    ]

    order_by = [
        'due_date',
    ]

    unlock_date = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()
    lock_date = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    attached_files = FileSerializer(many=True, read_only=True)

    def get_unlock_date(self, node):
        if node.is_deadline and node.unlock_date is not None:
            return node.unlock_date.strftime(settings.ALLOWED_DATETIME_FORMAT)
        return None

    def get_due_date(self, node):
        return node.due_date.strftime(settings.ALLOWED_DATETIME_FORMAT)

    def get_lock_date(self, node):
        if node.is_deadline and node.lock_date is not None:
            return node.lock_date.strftime(settings.ALLOWED_DATETIME_FORMAT)
        return None

    def get_target(self, node):
        if node.is_progress:
            return node.target
        return None

    def get_template(self, node):
        if node.is_deadline:
            return TemplateSerializer(node.forced_template, read_only=True, context=self.context).data
        return None


class AssignmentSerializer(ExtendedModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Assignment
        fields = (
            # Method fields
            'deadline',
            'journal',
            'stats',
            'course',
            'courses',
            'journals',
            'active_lti_course',
            'lti_courses',
            'has_teacher_entries',
            'can_change_type',
            # Model fields
            'id',
            'name',
            'description',
            'is_published',
            'points_possible',
            'unlock_date',
            'due_date',
            'lock_date',
            'is_group_assignment',
            'remove_grade_upon_leaving_group',
            'can_set_journal_name',
            'can_set_journal_image',
            'can_lock_journal',
            # Not used / missing: active_lti_id, lti_id_set, assigned_groups, format
        )
        read_only_fields = (
            'active_lti_course',
            'lti_id',
        )

    select_related = []

    prefetch_related = [
        'courses',
        Prefetch(
            'format__presetnode_set',
            queryset=PresetNodeSerializer.setup_eager_loading(
                VLE.models.PresetNode.objects.order_by('due_date')
            ),
        ),
        Prefetch(
            'format__template_set',
            queryset=TemplateSerializer.setup_eager_loading(
                VLE.models.Template.objects.filter(archived=False).order_by('name')
            ),
        ),
    ]

    enforced_context = [
        'user',
    ]

    deadline = serializers.SerializerMethodField()
    journal = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    course = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    journals = serializers.SerializerMethodField()
    active_lti_course = serializers.SerializerMethodField()
    lti_courses = serializers.SerializerMethodField()
    has_teacher_entries = serializers.SerializerMethodField()
    can_change_type = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(AssignmentSerializer, self).__init__(*args, **kwargs)

        user = self.context.get('user')
        permissions = [
            'can_have_journal',
            'can_grade',
            'can_view_all_journals',
            'can_edit_assignment',
            'can_post_teacher_entries',
            'can_manage_journal_import_requests',
        ]

        if user and isinstance(self.instance, VLE.models.Assignment):
            for permission in permissions:
                if permission not in self.context:
                    self.context[permission] = user.has_permission(permission, self.instance)

    def permission_from_context(self, permission, assignment):
        if permission in self.context:
            return self.context[permission]
        return self.context['user'].has_permission(permission, assignment)

    def get_deadline(self, assignment):
        user = self.context.get('user')

        # Student deadlines
        if self.permission_from_context('can_have_journal', assignment):
            journal = VLE.models.Journal.objects.filter(assignment=assignment, authors__user=user).first()
            deadline, name = assignment.get_student_deadline(journal)

            return {'date': deadline, 'name': name}
        # Teacher deadline
        else:
            return {'date': assignment.get_teacher_deadline()}

    def get_journal(self, assignment):
        user = self.context.get('user')

        if not self.permission_from_context('can_have_journal', assignment):
            return None

        try:
            journal = VLE.models.Journal.objects.get(assignment=assignment, authors__user=user)
            if not user.can_view(journal):
                return None
            return journal.pk
        except VLE.models.Journal.DoesNotExist:
            return None

    def get_journals(self, assignment):
        """
        The assignment is serialized from the perspective of a specific course. This impacts which users and journals
        should be used in queries.
        """
        journals = self.context.get('serialize_journals', False)
        course = self.context.get('course')

        if journals and course:
            if assignment.is_group_assignment:
                journals = VLE.models.Journal.objects.filter(assignment=assignment).order_by_authors_first()
            else:
                journals = VLE.models.Journal.objects.filter(assignment=assignment)

            journals = journals.for_course(course)
            journals = journals.annotate(
                author_count=Count('authors', distinct=True)
            ).distinct()

            return JournalSerializer(journals, many=True, context={**self.context, 'assignment': assignment}).data
        else:
            return None

    def get_stats(self, assignment):
        user = self.context.get('user')
        course = self.context.get('course', self._get_course(assignment))
        stats = {}

        # Upcoming specifically requests stats for all of the assignment's courses
        if course == settings.EXPLICITLY_WITHOUT_CONTEXT:
            relevant_stat_users = VLE.utils.statistics.get_user_lists_with_scopes(assignment, user)
        else:
            # We are not dealing explicitly without context, and we have no specific course, stats should not be needed.
            if course is None:
                return None
            relevant_stat_users = VLE.utils.statistics.get_user_lists_with_scopes(assignment, user, course=course)

        # Evaluation needs to be forced to play nice with ArrayAgg annotations (needs_lti_link, groups)
        relevant_stat_users_all = list(relevant_stat_users['all'])
        relevant_stat_users_own = list(relevant_stat_users['own'])

        all_j = VLE.models.Journal.objects.filter(assignment=assignment, authors__user__in=relevant_stat_users_all)
        own_j = VLE.models.Journal.objects.filter(assignment=assignment, authors__user__in=relevant_stat_users_own)

        all_j_stats = all_j.aggregate(
            average_points=Avg('grade'),
            needs_marking_sum=Sum('needs_marking'),
            unpublished_sum=Sum('unpublished'),
            import_requests_sum=Sum('import_requests'),
        )
        own_j_stats = own_j.aggregate(
            needs_marking_sum=Sum('needs_marking'),
            unpublished_sum=Sum('unpublished'),
            import_requests_sum=Sum('import_requests'),
        )

        # Grader stats
        if self.permission_from_context('can_grade', assignment):
            stats.update({
                'needs_marking': all_j_stats['needs_marking_sum'] or 0,
                'unpublished': all_j_stats['unpublished_sum'] or 0,
                'needs_marking_own_groups': own_j_stats['needs_marking_sum'] or 0,
                'unpublished_own_groups': own_j_stats['unpublished_sum'] or 0,
            })
        if self.permission_from_context('can_manage_journal_import_requests', assignment):
            stats.update({
                'import_requests': all_j_stats['import_requests_sum'] or 0,
                'import_requests_own_groups': own_j_stats['import_requests_sum'] or 0,
            })
        # Other stats
        stats['average_points'] = all_j_stats['average_points']

        return stats

    def get_course(self, assignment):
        return CourseSerializer(self._get_course(assignment), read_only=True, context=self.context).data

    def _get_course(self, assignment):
        course = self.context.get('course', None)
        user = self.context.get('user', None)

        if course is None or course == settings.EXPLICITLY_WITHOUT_CONTEXT:
            if user is not None:
                return assignment.get_active_course(user)
            else:
                return None
        elif course not in assignment.courses.all():
            raise VLE.utils.error_handling.VLEProgrammingError('Wrong course is supplied.')
        elif not user.can_view(course):
            raise VLE.utils.error_handling.VLEParticipationError(course, user)

        return course

    def get_courses(self, assignment):
        course = self.context.get('course')

        if course and not course == settings.EXPLICITLY_WITHOUT_CONTEXT:
            return None
        return CourseSerializer(assignment.courses, many=True, read_only=True).data

    def get_active_lti_course(self, assignment):
        if self.context['user'].can_view(assignment):
            course = assignment.get_active_lti_course()
            if course:
                return {'cID': course.pk, 'name': course.name}
        return None

    def get_lti_courses(self, assignment):
        if self.permission_from_context('can_edit_assignment', assignment):
            courses = assignment.courses.filter(assignment_lti_id_set__overlap=assignment.lti_id_set)
            return {c.pk: c.name for c in courses}
        return None

    def get_has_teacher_entries(self, assignment):
        if self.permission_from_context('can_post_teacher_entries', assignment):
            return assignment.teacherentry_set.exists()
        return False

    def get_can_change_type(self, assignment):
        return not assignment.has_entries()


class SmallAssignmentSerializer(AssignmentSerializer):
    class Meta:
        model = VLE.models.Assignment
        fields = (
            'id', 'name', 'is_group_assignment', 'is_published', 'points_possible', 'unlock_date', 'due_date',
            'lock_date', 'deadline', 'journal', 'stats', 'course', 'courses', 'active_lti_course')
        read_only_fields = fields

    select_related = []

    prefetch_related = [
        'courses',
    ]


class CommentSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Comment
        fields = ('id', 'entry', 'author', 'text', 'published', 'creation_date', 'last_edited', 'last_edited_by',
                  'can_edit', 'files')
        read_only_fields = ('entry', 'author', 'creation_date', 'last_edited',)

    select_related = [
        'author',
        'last_edited_by',
    ]

    prefetch_related = [
        'files',
    ]

    files = FileSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    last_edited_by = serializers.SerializerMethodField()
    last_edited = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    def get_last_edited_by(self, comment):
        if comment.last_edited > comment.creation_date + datetime.timedelta(minutes=3):
            return comment.last_edited_by.full_name

    def get_last_edited(self, comment):
        if comment.last_edited > comment.creation_date + datetime.timedelta(minutes=3):
            return comment.last_edited

    def get_can_edit(self, comment):
        user = self.context.get('user', None)
        if not user:
            return False

        return comment.can_edit(user)


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Journal
        fields = (
            # Normal fields
            'id',
            'bonus_points',
            'author_limit',
            'locked',
            # Annotated fields
            'full_names',
            'usernames',
            'name',
            'author_count',  # NOTE: Will be fetched if missing
            'import_requests',
            'image',
            'grade',
            'unpublished',
            'needs_marking',
            'needs_lti_link',
            'groups',
        )
        read_only_fields = (
            'assignment',
            'authors',
            'import_requests',
            'full_names',
            'usernames',
            'name',
            'image',
            'grade',
            'unpublished',
            'needs_marking',
            'needs_lti_link',
            'groups',
        )

    author_count = serializers.SerializerMethodField()
    # Annotated fields need to be explicitly declared as they can't be derived from the Meta model
    usernames = serializers.SerializerMethodField()
    full_names = serializers.CharField()
    name = serializers.CharField()
    import_requests = serializers.SerializerMethodField()
    image = serializers.CharField()
    grade = serializers.FloatField()
    unpublished = serializers.IntegerField()
    needs_marking = serializers.IntegerField()
    needs_lti_link = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(JournalSerializer, self).__init__(*args, **kwargs)

        user = self.context.get('user')
        assignment = self.context.get('assignment')

        permissions = [
            'can_view_all_journals',
            'can_manage_journal_import_requests',
        ]

        if not assignment:
            if isinstance(self.instance, VLE.models.Journal):
                assignment = self.instance.assignment
            elif isinstance(self.instance, VLE.models.JournalQuerySet) and self.instance.exists():
                if VLE.models.Assignment.objects.filter(journal__in=self.instance).distinct().count() > 1:
                    capture_message('Serializing journals from multiple assignments', level='warning')
                assignment = self.instance[0].assignment

        if user and assignment:
            for permission in permissions:
                if permission not in self.context:
                    self.context[permission] = user.has_permission(permission, assignment)

    def get_author_count(self, journal):
        """Make use of 'author_count' annotation if provided."""
        if hasattr(journal, 'author_count'):
            return journal.author_count
        return journal.authors.count()

    def get_usernames(self, journal):
        if self.context.get('can_view_all_journals', False):
            return journal.usernames
        return None

    def get_groups(self, journal):
        if 'course' not in self.context:
            return None
        return journal.groups

    def get_import_requests(self, journal):
        if self.context.get('can_manage_journal_import_requests', False):
            return journal.import_requests
        return None

    def get_needs_lti_link(self, journal):
        return journal.needs_lti_link


# Would massively benefit from top down serialization (many=True)
class EntrySerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Entry
        fields = (
            'id',
            'creation_date',
            'template',
            'title',
            'content',
            'editable',
            'grade',
            'last_edited',
            'comments',
            'author',
            'last_edited_by',
            'jir',
            'categories',
            'is_draft',
        )
        read_only_fields = (
            'creation_date',
        )

    select_related = [
        'author',
        'template',
        'template__chain',
        'last_edited_by',
        'teacher_entry',
        'grade',
        'node__journal__assignment',  # used in permission check can grade and locked check
        'jir__source__assignment',
        'jir__processor',
        'node',
        'node__preset',
    ]

    # NOTE: Comments (comment_set) are only serialized via GDPR, which prefetches the comment_set itself.
    prefetch_related = [
        'content_set',
        'content_set__field',
        # Order the file context set from new to old to ensure the first element of the prefetch cache contains
        # the most recent FC (e.g. after updating an existing file field)
        Prefetch(
            'content_set__filecontext_set',
            queryset=VLE.models.FileContext.objects.order_by('-creation_date'),
        ),
        'categories',
        Prefetch('template', queryset=TemplateSerializer.setup_eager_loading(VLE.models.Template.objects.all())),
        # NOTE: Too uncommon, not worth the additional prefetch.
        # 'jir__source__assignment__courses',
    ]

    template = TemplateSerializer(read_only=True)
    categories = CategoryConcreteFieldsSerializer(read_only=True, many=True)
    editable = serializers.BooleanField(read_only=True, source='is_editable')
    author = serializers.CharField(source='author.full_name', default=VLE.models.User.UNKNOWN_STR)
    last_edited_by = serializers.CharField(source='last_edited_by.full_name', default=VLE.models.User.UNKNOWN_STR)
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    jir = serializers.SerializerMethodField()

    def get_title(self, entry):
        if entry.title:
            return entry.title

        if (entry.teacher_entry and entry.teacher_entry.show_title_in_timeline):
            return entry.teacher_entry.title

        if entry.node.preset:
            return entry.node.preset.display_name

        return entry.template.name

    def get_content(self, entry):
        def _get_content(entry):
            content_dict = {}

            for content in entry.content_set.all():
                # Only include the actual content (so e.g. text).
                if content.field.type == VLE.models.Field.FILE and content.data:
                    try:
                        values, prefetched = prefetched_objects(content, 'filecontext_set')
                        # The prefetch cache is ordered on FC creation date, so we can directly access the first element
                        # if available to retrieve the matching FC (multiple FCs can match one content,
                        # e.g. between cleanup cycles and after updating a file field).
                        fc = values[0] if prefetched else VLE.models.FileContext.objects.get(pk=content.data)
                        content_dict[content.field.id] = FileSerializer(fc).data
                    except VLE.models.FileContext.DoesNotExist:
                        capture_message(
                            f'FILE content {content.pk} refers to unknown file in data: {content.data}', level='error')
                        return {}
                else:
                    content_dict[content.field.id] = content.data

            return content_dict

        content_dict = {}

        # If it is a teacher entry, initialize the content with the content of the teacher entry
        # Only when a user edits the content, set the new content
        if entry.teacher_entry:
            content_dict.update(_get_content(entry.teacher_entry))

        content_dict.update(_get_content(entry))
        return content_dict

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

        return CommentSerializer(
            CommentSerializer.setup_eager_loading(entry.comment_set.all()),
            many=True,
            context=self.context
        ).data

    def get_jir(self, entry):
        if entry.jir:
            jir_source_course = entry.jir.source.assignment.get_active_course(self.context['user'])
            return {
                'source': {
                    'assignment': {
                        'name': entry.jir.source.assignment.name,
                        'course': {
                            'abbreviation': jir_source_course.abbreviation if jir_source_course else ''
                        },
                    },
                },
                'processor': {
                    'full_name': entry.jir.processor.full_name
                }
            }
        return None


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VLE.models.Grade
        fields = ('id', 'entry', 'grade', 'published')
        read_only_fields = fields


class TeacherEntryGradeSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Entry
        fields = (
            'journal_id',
            'grade',
            'published',
            # Annotations
            'usernames',
            'name',
        )
        read_only_fields = fields

    select_related = [
        'grade',
        'node__journal',
    ]

    journal_id = serializers.IntegerField(source='node.journal_id')
    grade = serializers.FloatField(source='grade.grade', default=None)
    published = serializers.BooleanField(source='grade.published', default=False)
    # Annotated fields need to be explicitly declared as they can't be derived from the Meta model
    usernames = serializers.CharField()
    name = serializers.CharField()


class GradeHistorySerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Grade
        fields = ('grade', 'published', 'creation_date', 'author')
        read_only_fields = fields

    select_related = [
        'author',
    ]

    author = serializers.CharField(source='author.full_name', default=VLE.models.User.UNKNOWN_STR)


class TeacherEntrySerializer(EntrySerializer):
    class Meta:
        model = VLE.models.TeacherEntry
        fields = (
            'id',
            'title',
            'template',
            'content',
            'journals',
            'categories',
        )
        read_only_fields = fields

    journals = TeacherEntryGradeSerializer(many=True, read_only=True, source='entry_set')
    categories = CategoryConcreteFieldsSerializer(many=True, read_only=True)
    # This is to overwrite the EntrySerializer serializedmethod title field, and use the db variable instead
    title = None

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = EntrySerializer.setup_eager_loading(queryset)

        # Fetch everything the TeacherEntryGradeSerializer requires
        queryset = queryset.prefetch_related(
            Prefetch(
                'entry_set',
                queryset=VLE.models.Entry.objects.select_related(
                    *TeacherEntryGradeSerializer.select_related
                )
                .annotate_teacher_entry_grade_serializer_fields()
                .order_by('name')
            )
        )

        # Fetch everthing the TemplateSerializer requires
        queryset = queryset.select_related(
            'template',
            'template__chain',
        )

        return queryset


class JournalImportRequestSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.JournalImportRequest
        fields = ('id', 'source', 'target', 'author', 'processor')
        read_only_fields = fields

    select_related = [
        'author',
        'processor',
        'source',
        'source__assignment',
        'target',
        'target__assignment',
        *[f'source__assignment__{related}' for related in SmallAssignmentSerializer.select_related],
        *[f'target__assignment__{related}' for related in SmallAssignmentSerializer.select_related],
    ]

    prefetch_related = [
        *[f'source__assignment__{related}' for related in SmallAssignmentSerializer.prefetch_related],
        *[f'target__assignment__{related}' for related in SmallAssignmentSerializer.prefetch_related],
    ]

    author = UserSerializer(read_only=True)
    processor = UserSerializer(read_only=True)
    source = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    def get_source(self, jir):
        if jir.source is None:
            return 'Source journal no longer exists.'

        source = jir.source
        if source.missing_annotated_field:
            source = VLE.models.Journal.objects.get(pk=source.pk)

        return {
            'journal': JournalSerializer(source, context=self.context, read_only=True).data,
            'assignment': SmallAssignmentSerializer(jir.source.assignment, context=self.context, read_only=True).data,
        }

    def get_target(self, jir):
        target = jir.target
        if target.missing_annotated_field:
            target = VLE.models.Journal.objects.get(pk=target.pk)

        return {
            'journal': JournalSerializer(target, context=self.context, read_only=True).data,
            'assignment': SmallAssignmentSerializer(jir.target.assignment, context=self.context, read_only=True).data,
        }


class LevelSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Level
        fields = (
            'id',
            'points',
            'initial_feedback',
            'location',
        )
        read_only_fields = ()


class CriterionSerializer(serializers.ModelSerializer, EagerLoadingMixin):
    class Meta:
        model = VLE.models.Criterion
        fields = (
            'id',
            'name',
            'description',
            'long_description',
            'score_as_range',
            'location',
            'levels',
        )
        read_only_fields = ()

    prefetch_related = [
        'levels',
    ]

    levels = LevelSerializer(many=True, read_only=True)


class RubricSerializer(serializers.ModelSerializer, EagerLoadingMixin, WriteOnceMixin):
    class Meta:
        model = VLE.models.Rubric
        fields = (
            'id',
            'assignment',
            'name',
            'description',
            'visibility',
            'hide_score_from_students',
            'criteria',
        )
        read_only_fields = ()
        write_once_fields = ('assignment',)

    prefetch_related = [
        'criteria',
        *[f'criteria__{related}' for related in CriterionSerializer.prefetch_related],
    ]

    criteria = CriterionSerializer(many=True, read_only=True)
