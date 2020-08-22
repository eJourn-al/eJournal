from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestMigration0045(MigratorTestCase):
    """This class is used to test direct migrations."""

    migrate_from = ('VLE', '0047_dynamic_filename')
    migrate_to = ('VLE', '0048_notifications')

    def prepare(self):
        """Prepare some data before the migration."""
        User = self.old_state.apps.get_model('VLE', 'User')
        Preferences = self.old_state.apps.get_model('VLE', 'Preferences')
        user_off = User.objects.create(username='test1', email='test1@mail.com')
        user_on = User.objects.create(username='test2', email='test2@mail.com')
        Preferences.objects.create(user_id=user_off.pk, upcoming_deadline_notifications=False)
        Preferences.objects.create(user_id=user_on.pk, upcoming_deadline_notifications=True)

    def test_migration_0045(self):
        """Run the test itself."""
        User = self.old_state.apps.get_model('VLE', 'User')
        Preferences = self.new_state.apps.get_model('VLE', 'Preferences')
        user_off = User.objects.get(username='test1', email='test1@mail.com')
        user_on = User.objects.get(username='test2', email='test2@mail.com')
        assert Preferences.objects.filter(user_id=user_off.pk, upcoming_deadline_reminder='o').exists()
        assert Preferences.objects.filter(user_id=user_on.pk, upcoming_deadline_reminder='p').exists()
