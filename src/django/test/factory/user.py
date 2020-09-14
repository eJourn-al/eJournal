import factory
from django.conf import settings

DEFAULT_PASSWORD = 'Pass123!'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'VLE.User'

    username = factory.Sequence(lambda x: f"user{x + 1}")
    full_name = factory.Sequence(lambda x: f"Normal user {x + 1}")
    email = factory.Sequence(lambda x: f'email{x + 1}@example.com')
    password = factory.PostGenerationMethodCall('set_password', DEFAULT_PASSWORD)
    verified_email = True

    profile_picture = settings.DEFAULT_PROFILE_PICTURE

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

    @factory.post_generation
    def preferences(self, create, extracted, **kwargs):
        """
        Allows deep syntax for a users preferences

        Preferences is OneToOne with User, where the user fk is its primary key. This results in Django
        auto generating the preferences on creation of a user. Emulating this with a User SubFactory for
        PreferencesFactory and a RelatedFactory for UserFactory caused a duplicate Preferences instance
        to be generated.
        """
        if not create:
            return

        if isinstance(extracted, dict):
            self.preferences.__dict__.update(extracted)
        self.preferences.__dict__.update(kwargs)
        self.preferences.save()


class LtiStudentFactory(UserFactory):
    lti_id = factory.Sequence(lambda x: "id{}".format(x))


class TestUserFactory(LtiStudentFactory):
    email = None
    username = factory.Sequence(lambda x: f"305c9b180a9ce9684ea62aeff2b2e97052cf2d4b{x + 1}")
    full_name = settings.LTI_TEST_STUDENT_FULL_NAME
    verified_email = False
    is_test_student = True
    factory.PostGenerationMethodCall('set_unusable_password')


class TeacherFactory(UserFactory):
    username = factory.Sequence(lambda x: f"teacher{x + 1}")
    full_name = factory.Sequence(lambda x: f"Teacher user {x + 1}")
    is_teacher = True


class LtiTeacherFactory(TeacherFactory):
    lti_id = factory.Sequence(lambda x: "id{}".format(x))


class AdminFactory(UserFactory):
    username = factory.Sequence(lambda x: f"admin{x + 1}")
    full_name = factory.Sequence(lambda x: f"Admin user {x + 1}")
    is_superuser = True
