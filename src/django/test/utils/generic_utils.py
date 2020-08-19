import re

from deepdiff import DeepDiff
from django.conf import settings
from django.db import models
from django.db.models.fields.related import ManyToManyField


def _model_instance_to_dict(instance, ignore=[]):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if f.name in ignore:
            continue
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                try:
                    data[f.name] = list(f.value_from_object(instance).values_list('pk', flat=True))
                except AttributeError:
                    data[f.name] = [inst.pk for inst in f.value_from_object(instance)]
        else:
            data[f.name] = f.value_from_object(instance)

    return data


def _keys_to_path_ignore_regex(ignore_keys=[]):
    '''
    Creates a regex which ignore_keys top level path keys matching the ignore_keys list
    '''
    ignore_keys = list(map(lambda k: re.escape(k), ignore_keys))

    return None if not ignore_keys else re.compile(rf"^root(?:\[.*\])*\['(?:{'|'.join(ignore_keys)})'\]$")


def _equal_dicts(d1, d2, ignore_keys=[], exclude_regex_paths=[], return_diff=False):
    k_ignore_r = _keys_to_path_ignore_regex(ignore_keys)
    exclude_regex_paths = list(map(lambda r: re.compile(r), exclude_regex_paths))

    if k_ignore_r:
        exclude_regex_paths += [k_ignore_r]
    if not exclude_regex_paths:
        exclude_regex_paths = None  # Default

    diff = DeepDiff(d1, d2, exclude_regex_paths=exclude_regex_paths)

    if diff != {} and settings.ENVIRONMENT == 'LOCAL':
        print(diff)

    if return_diff:
        return diff
    return diff == {}


def instance_conrete_fields_dict(instance):
    concrete_fields = instance._meta.concrete_fields
    return {field.name: field.value_from_object(instance) for field in concrete_fields}


def equal_models(m1, m2, ignore_keys=[], exclude_regex_paths=[], return_diff=False):
    if issubclass(m1.__class__, models.Model):
        return _equal_dicts(
            _model_instance_to_dict(m1, ignore_keys),
            _model_instance_to_dict(m2, ignore_keys),
            ignore_keys,
            exclude_regex_paths,
            return_diff
        )
    return _equal_dicts(m1, m2, ignore_keys, exclude_regex_paths, return_diff)
