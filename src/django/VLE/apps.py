"""
apps.py.

Setup the app.
"""
from django.apps import AppConfig
from django.conf import settings


class VLEConfig(AppConfig):
    """VLEconfig.

    VLE global config.
    """

    name = 'VLE'
    verbose_name = 'Virtual Learning Environment'

    def ready(self):
        '''Perform initialization tasks such as registering signals.
        It is called as soon as the registry is fully populated.'''
        # Ensure the existens of an instance
        Instance = self.get_model('Instance')
        Instance.objects.get_or_create(pk=1)

        # Update the tool configuration to the database settings
        settings.TOOL_CONF.update_config()
