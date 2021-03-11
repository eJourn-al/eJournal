"""
apps.py.

Setup the app.
"""
from django.apps import AppConfig
from django.conf import settings
from django.db.utils import ProgrammingError


class VLEConfig(AppConfig):
    """VLEconfig.

    VLE global config.
    """

    name = 'VLE'
    verbose_name = 'Virtual Learning Environment'

    def ready(self):
        '''Perform initialization tasks such as registering signals.
        It is called as soon as the registry is fully populated.'''
        try:
            # Ensure the existens of an instance
            Instance = self.get_model('Instance')
            instance = Instance.objects.get_or_create(pk=1)[0]

            # Update the tool configuration to the database settings
            settings.TOOL_CONF.update_config(instance=instance)
        except ProgrammingError:
            # Doesn't work on preset db as the db is not yet migrated
            pass
