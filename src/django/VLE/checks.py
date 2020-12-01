import django.core.checks


@django.core.checks.register('rest_framework.serializers')
def check_missing_read_only_fields_serializers(app_configs, **kwargs):
    """
    Triggers a warning for each ModelSerializer which does not define 'read_only_fields'

    This forces developers to consider what fields can be treated as read only. This is important since each non read
    only field is validated upon serialization, which hurts performance significantly.
    """

    import inspect
    from rest_framework.serializers import ModelSerializer
    from VLE.serializers import ExtendedModelSerializer
    import django.conf.urls  # noqa, force import of all serializers.

    for serializer in ModelSerializer.__subclasses__():

        # Skip third-party apps.
        path = inspect.getfile(serializer)
        if path.find('site-packages') > -1:
            continue

        # ExtendedModelSerializer is practically an abstract class
        if serializer is ExtendedModelSerializer:
            continue

        if hasattr(serializer.Meta, 'read_only_fields'):
            continue

        yield django.core.checks.Warning(
            'ModelSerializer must define read_only_fields.',
            hint='Set read_only_fields in ModelSerializer.Meta',
            obj=serializer,
            id='VLE.W001',
        )
