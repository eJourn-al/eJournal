from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestMigration0065(MigratorTestCase):
    """This class is used to test direct migrations."""

    migrate_from = ('VLE', '0064_use_ejournal_default_profile_picture')
    migrate_to = ('VLE', '0065_entry_grade_set')

    def prepare(self):
        """Prepare some data before the migration."""
        Entry = self.old_state.apps.get_model('VLE', 'Entry')
        Grade = self.old_state.apps.get_model('VLE', 'Grade')

        entry = Entry.objects.create()
        grade = Grade.objects.create(entry=entry, grade=4, published=True)
        entry.grade = grade
        entry.save()

    def test_migration_0065(self):
        """Run the test itself."""
        Entry = self.new_state.apps.get_model('VLE', 'Entry')
        Grade = self.new_state.apps.get_model('VLE', 'Grade')
        entry = Entry.objects.first()
        grade = Grade.objects.last()

        assert entry.grade_set.filter(pk=grade.pk).exists()
        assert not entry.grade_set.exclude(pk=grade.pk).exists()
        assert entry.grade == grade
