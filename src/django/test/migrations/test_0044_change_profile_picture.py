from django.conf import settings
from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestMigration0042(MigratorTestCase):
    """This class is used to test direct migrations."""

    migrate_from = ('VLE', '0043_comment_files')
    migrate_to = ('VLE', '0044_change_profile_picture')

    def prepare(self):
        """Prepare some data before the migration."""
        User = self.old_state.apps.get_model('VLE', 'User')
        pf = 'https://canvas.instructure.com/images/messages/avatar-50.png'
        User.objects.create(username='test', profile_picture=pf, email='test@mail.com')

    def test_migration_0042(self):
        """Run the test itself."""
        User = self.new_state.apps.get_model('VLE', 'User')
        Instance = self.new_state.apps.get_model('VLE', 'Instance')
        pf = Instance.objects.get_or_create(pk=1)[0].default_lms_profile_picture

        assert not User.objects.filter(profile_picture=pf).exists()
        assert User.objects.filter(profile_picture=settings.DEFAULT_PROFILE_PICTURE).exists()
