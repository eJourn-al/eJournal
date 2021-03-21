
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

import VLE.lti1p3 as lti
from VLE.models import Participation, Role, User
from VLE.utils.error_handling import VLEProgrammingError


class UserData(lti.utils.PreparedData):
    def __init__(self, data):
        self.data = data

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
        return any(
            role in self.roles
            for role in [lti.roles.TEACHER, lti.roles.ADMIN, lti.roles.ADMIN_INST]
        )

    @property
    def is_test_student(self):
        # TODO LTI: this is Canvas specific, should be changed to also work with other LTI hosts
        return (
            self.email == ''
            and self.full_name == 'Test Student'.lower()
        )

    def normalize_profile_picture(self, picture):
        # TODO LTI: this is Canvas specific, should be changed to also work with other LTI hosts
        if not picture or '/avatar-50.png' in picture:
            return settings.DEFAULT_PROFILE_PICTURE

        return picture

    def create_participation(self, user, course):
        # TODO LTI: add groups
        # TODO LTI: should we update roles and or groups?
        participation = Participation.objects.filter(user=user, course=course).first()
        if participation:
            return participation

        return Participation.objects.create(
            user=user,
            course=course,
            role=Role.objects.get(
                course=course,
                name=lti.roles.to_ejournal_role(self.roles),
            ),
        )

    def handle_test_student(self, course=None):
        if not course:
            course = lti.course.Lti1p3CourseData(self.data).find_in_db()
        if not course:
            return

        User.objects.filter(participation__course=course, is_test_student=True).delete()

    def find_in_db(self):
        # QUESTION LTI: What should we automatically do with usernames / emails that already exists?
        # This may be executed in the background, dont want to bother the user
        # I for now just select the email with that email / username and update the values for that user
        user_qry = Q(lti_id=self.lti_id)
        if self.email:
            user_qry.add(Q(email=self.email), Q.OR)
        if self.username:
            user_qry.add(Q(username=self.username), Q.OR)
        if self.sis_id:
            user_qry.add(Q(sis_id=self.sis_id), Q.OR)

        return User.objects.filter(user_qry).first()

    def create(self, password=None, course=None):
        if not course:
            course = lti.course.Lti1p3CourseData(self.data).find_in_db()

        if self.is_test_student:
            self.handle_test_student(course=course)

        user = User(**self.create_dict)

        if password and not self.is_test_student:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save()

        if course:
            self.create_participation(user, course=course)

        return user

    def update(self, obj=None, course=None):
        if not course:
            course = lti.course.Lti1p3CourseData(self.data).find_in_db()

        user = obj
        if not user:
            user = self.find_in_db()
        if not user:
            raise VLEProgrammingError('User does not exist, so it cannot be updated')

        for key in self.update_keys:
            if getattr(self, key) is not None:
                setattr(user, key, getattr(self, key))

        user.last_login = timezone.now()
        user.save()

        if course:
            self.create_participation(user, course=course)

        return user


class Lti1p3UserData(UserData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'lti_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            'email',
            'username',
            'is_test_student',
            'verified_email',
            'is_teacher',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'lti_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            'email',
            'username',
            # 'is_test_student',
            'verified_email',
            'is_teacher',
        ]

    @property
    def lti_id(self):
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
    def username(self):
        if lti.claims.CUSTOM not in self.data or \
           'username' not in self.data[lti.claims.CUSTOM]:
            return None

        return self.data[lti.claims.CUSTOM]['username']


class NRSUserData(UserData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_keys = [
            'lti_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            'email',
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'lti_id',
            'sis_id',
            'full_name',
            'profile_picture',
            # 'roles',
            'email',
        ]

    @property
    def lti_id(self):
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
        ]
        # QUESTION LTI: are these valid settings?
        self.update_keys = [
            'sis_id',
            'full_name',
            'username',
        ]

    @property
    def sis_id(self):
        return self.data['sis_user_id']

    @property
    def full_name(self):
        return self.data.get('name', None)

    @property
    def username(self):
        return self.data['login_id']
