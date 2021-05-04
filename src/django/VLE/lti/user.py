
import sentry_sdk
from django.conf import settings
from django.db.utils import IntegrityError
from django.utils import timezone

import VLE.lti as lti
from VLE import factory
from VLE.models import Group, Participation, Role, User
from VLE.utils.error_handling import VLEBadRequest, VLEProgrammingError


class UserData(lti.utils.PreparedData):
    model = User
    _is_test_student = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.find_keys = [
            'sis_id',
            'username',
            'email',
        ]
        self.debug_keys = [
            'roles',
            'role_name',
        ]

    @property
    def lti_id(self):
        return None

    @property
    def sis_id(self):
        return None

    @property
    def full_name(self):
        return None

    @property
    def profile_picture(self):
        return None

    @property
    def roles(self):
        return None

    @property
    def email(self):
        return None

    @property
    def username(self):
        return None

    @property
    def verified_email(self):
        return bool(self.email)

    @property
    def is_teacher(self):
        # NOTE: from tests: Teacher should stay teacher, even when roles change
        # If role is teacher, return true
        if self.role_name == 'Teacher':
            return True

        # Else if user already exists, return the currect flag
        if self.find_in_db():
            return self.find_in_db().is_teacher

        # By default user should not get the teacher role
        return False

    @property
    def role_name(self):
        if hasattr(self, 'roles'):
            return lti.roles.to_ejournal_role_name(self.roles)
        else:
            return 'Student'

    @property
    def grade_url(self):
        return self.data.get('lis_outcome_service_url', None)

    @property
    def sourcedid(self):
        return self.data.get('lis_result_sourcedid', None)

    @property
    def is_test_student(self):
        # If this function was already performed, return the cached value
        if self._is_test_student is not None:
            return self._is_test_student

        # TODO EXPANSION: this is Canvas specific, should be changed to also work with other LTI hosts
        self._is_test_student = not self.email

        # When we have a test student that does not have a full name like a test student, create a sentry warning
        if self._is_test_student and self.full_name not in settings.LTI_TEST_STUDENT_FULL_NAMES:
            with sentry_sdk.push_scope() as scope:
                scope.set_context('user', self.asdict())
                sentry_sdk.capture_message(f'Unusual test student created, called {self.full_name}', level='warning')

        return self._is_test_student

    def normalize_profile_picture(self, picture):
        # TODO EXPANSION: this is Canvas specific, should be changed to also work with other LTI hosts
        if not picture or '/avatar-50.png' in picture:
            return settings.DEFAULT_PROFILE_PICTURE

        return picture

    def add_groups_if_not_exists(self, participation):
        """Add the lti groups to a participant.

        This will only be done if there are no other groups already bound to the participant.
        """
        def get_name_from_lms_id(lms_id, group_names, i):
            if lms_id in group_names:
                return group_names[lms_id]
            elif lms_id.isnumeric() and int(lms_id) in group_names:
                return group_names[int(lms_id)]
            else:
                return 'Group {:d}'.format(n_groups + i + 1)

        group_ids = [str(g) for g in self.groups]

        # Get all existing groups passed by lti that are also in the course
        groups = Group.objects.filter(lms_id__in=group_ids, course=participation.course)
        # Get all to-be-created groups
        non_existing_group_ids = set(group_ids) - set(group.lms_id for group in groups)
        # Get the groups of the course which the user is not participating in
        non_participating_groups = groups.exclude(pk__in=participation.groups.all())

        # Create new groups
        if non_existing_group_ids:
            group_names = factory.get_lti_groups_with_name(participation.course)
            n_groups = Group.objects.filter(course=participation.course).count()

            new_groups = [
                Group(
                    name=get_name_from_lms_id(lms_id, group_names, i),
                    course=participation.course,
                    lms_id=lms_id
                )
                for i, lms_id in enumerate(non_existing_group_ids)
            ]
            new_groups = Group.objects.bulk_create(new_groups)
        else:
            new_groups = []

        # Add missing newly-created and existing groups
        if new_groups or non_participating_groups:
            participation.groups.add(*new_groups, *non_participating_groups)

        return participation.groups

    def create_or_update_participation(self, user=None, course=None):
        if user is None:
            user = self.find_in_db()
        if course is None:
            course = self.CourseData(self.data).find_in_db()
        if not (user and course):
            return None
        # QUESTION: should we also update the user role and/or groups?
        participation = Participation.objects.filter(user=user, course=course).first()
        if not participation:
            participation = Participation.objects.create(
                user=user,
                course=course,
                role=Role.objects.get(
                    course=course,
                    name=self.role_name,
                ),
            )
        else:
            if self.role_name != participation.role.name:
                participation.role = Role.objects.get(
                    course=course,
                    name=self.role_name,
                )
                participation.save()

        if hasattr(self, 'groups'):
            print(self.groups)
            self.add_groups_if_not_exists(participation)

        return participation

    def handle_test_student(self, course=None):
        if not course:
            course = self.CourseData(self.data).find_in_db()
        if not course:
            return

        users = User.objects.filter(participation__course=course, is_test_student=True)
        if self.find_in_db():
            users = users.exclude(pk=self.find_in_db().pk)
        print('DELETED USERS', users.delete())

    def do_password(self, user, password):
        if password and not self.is_test_student:
            user.set_password(password)
        else:
            user.set_unusable_password()

    def create(self, password=None, course=None):
        if not self.is_test_student and self.find_in_db():
            raise VLEBadRequest('User already exists')

        if not course:
            course = self.CourseData(self.data).find_in_db()

        if self.is_test_student:
            self.handle_test_student(course=course)

        user = User(**self.create_dict())
        self.do_password(user, password)
        user.save()
        if course:
            self.create_or_update_participation(user=user, course=course)

        return user

    def update(self, obj=None, password=None, course=None):
        if not course:
            course = self.CourseData(self.data).find_in_db()

        user = obj
        if not user:
            user = self.find_in_db()
        if not user:
            raise VLEProgrammingError('User does not exist, so it cannot be updated')

        # When a user used to be a test student, it should not be able to magically change to a normal user
        # This could happen when a test student gets an email, there is no valid way
        if user.is_test_student and not self.is_test_student:
            raise VLEProgrammingError(
                'This account was previously configured as a test student, which no longer seems to be the case.'
                f' Please contact {settings.EMAILS.support.email}.'
            )

        if self.is_test_student:
            self.handle_test_student(course=course)

        for key in self.update_keys:
            if getattr(self, key) is not None:
                setattr(user, key, getattr(self, key))

        user.last_login = timezone.now()
        self.do_password(user, password)
        try:
            user.save()
        except IntegrityError:
            raise VLEBadRequest('User already exists')

        if course:
            self.create_or_update_participation(user=user, course=course)

        return user


class Lti1p3UserData(UserData):
    CourseData = lti.course.Lti1p3CourseData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'lti_1p3_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            # 'groups',
            'email',
            'username',
            'is_test_student',
            'verified_email',
            'is_teacher',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'lti_1p3_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            # 'groups',
            'email',
            'username',
            # 'is_test_student',
            'verified_email',
            'is_teacher',
        ]
        self.find_keys.append('lti_1p3_id')

    @property
    def lti_1p3_id(self):
        return self.data['sub']

    @property
    def sis_id(self):
        return self.data[lti.claims.LIS]['person_sourcedid']

    @property
    def full_name(self):
        return self.data.get('name', None)

    @property
    def profile_picture(self):
        return self.normalize_profile_picture(self.data.get('picture', None))

    @property
    def roles(self):
        return self.data[lti.claims.ROLES]

    @property
    def email(self):
        return self.data.get('email', None)

    @property
    def groups(self):
        # Because ''.split(',') => ['']
        if self.data.get('custom_section_id', ''):
            return self.data.get('custom_section_id', '').split(',')
        return []

    @property
    def username(self):
        if lti.claims.CUSTOM not in self.data or \
           'username' not in self.data[lti.claims.CUSTOM]:
            return None

        return self.data[lti.claims.CUSTOM]['username']


class Lti1p0UserData(UserData):
    CourseData = lti.course.Lti1p0CourseData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'lti_1p0_id',
            'username',
            'full_name',
            'profile_picture',
            # 'roles',
            # 'groups',
            'email',
            'is_test_student',
            'verified_email',
            'is_teacher',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'lti_1p0_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            # 'groups',
            'email',
            'username',
            # 'is_test_student',
            'verified_email',
            'is_teacher',
        ]
        self.find_keys.append('lti_1p0_id')

    @property
    def lti_1p0_id(self):
        return self.data['user_id']

    @property
    def username(self):
        return self.data['custom_username']

    @property
    def full_name(self):
        return self.data.get('custom_user_full_name', None)

    @property
    def profile_picture(self):
        return self.normalize_profile_picture(self.data.get('custom_user_image', None))

    @property
    def roles(self):
        roles = []
        if self.data.get('ext_roles', ''):
            roles += self.data.get('ext_roles', '').split(',')
        if self.data.get('roles', ''):
            roles += self.data.get('roles', '').split(',')
        return roles

    @property
    def groups(self):
        if self.data.get('custom_section_id', ''):
            return self.data.get('custom_section_id', '').split(',')
        return []

    @property
    def email(self):
        return self.data.get('custom_user_email', None)


class NRSUserData(UserData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'lti_1p3_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            'email',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'lti_1p3_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            'email',
        ]

    @property
    def lti_1p3_id(self):
        return self.data['user_id']

    @property
    def sis_id(self):
        return self.data.get('lis_person_sourcedid', None)

    @property
    def full_name(self):
        return self.data.get('name', None)

    @property
    def profile_picture(self):
        return self.normalize_profile_picture(self.data.get('picture', None))

    @property
    def roles(self):
        return self.data.get('roles', [])

    @property
    def email(self):
        return self.data.get('email', None)


class CanvasAPIUserData(UserData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'sis_id',
            'full_name',
            'username',
            'profile_picture',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'sis_id',
            'full_name',
            'username',
        ]

    @property
    def sis_id(self):
        return self.get_required(self.data, 'sis_user_id')

    @property
    def full_name(self):
        return self.data.get('name', None)

    @property
    def username(self):
        return self.get_required(self.data, 'login_id')

    @property
    def profile_picture(self):
        return settings.DEFAULT_PROFILE_PICTURE
