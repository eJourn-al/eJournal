import filecmp
import re

from deepdiff import DeepDiff
from django.conf import settings
from django.db import models
from django.db.models.fields.related import ManyToManyField

import VLE.models
import VLE.utils.file_handling as file_handling
from VLE.utils.error_handling import VLEProgrammingError


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

    Will ignore root['<key>|<key>'] etc.
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
        print(f"\n{80 * '-'}\n", diff, f"\n{80 * '-'}\n")

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


def check_equality_of_imported_file_context(fc1, fc2, ignore_keys):
    assert fc1.pk != fc2.pk, 'FC is not shared between imports'
    assert fc1.access_id != fc2.access_id, 'New access id is generated for the imported FC'
    assert fc1.file.path != fc2.file.path, 'A new underlying file is created'
    assert filecmp.cmp(fc1.file.path, fc2.file.path), 'For the rest the files are equal'
    assert equal_models(fc1, fc2, ignore_keys=ignore_keys)


def check_equality_of_imported_rich_text(source_rt, target_rt, model):
    '''
    Compares wether the rich text fields of the given models are equal bar the embedded download urls.
    Also checks if the embedded FCs are actually copied but mostly equal.
    '''
    if not any([model is handled_model for handled_model in [VLE.models.Content, VLE.models.Comment]]):
        raise VLEProgrammingError('Validating RT of unhandled model')

    fc_ignore_keys = ['last_edited', 'creation_date', 'update_date', 'id', 'access_id']

    if model is VLE.models.Content:
        fc_ignore_keys += ['content', 'journal']
    elif model is VLE.models.Comment:
        fc_ignore_keys += ['comment', 'journal']

    source_access_ids = file_handling.get_access_ids_from_rich_text(source_rt)
    target_access_ids = file_handling.get_access_ids_from_rich_text(target_rt)

    # We want equality in order, so we zip the ids, this will catch length and order mismatches
    for fc_source_id, fc_target_id in zip(source_access_ids, target_access_ids):
        source_fc = VLE.models.FileContext.objects.get(access_id=fc_source_id)
        target_fc = VLE.models.FileContext.objects.get(access_id=fc_target_id)

        check_equality_of_imported_file_context(source_fc, target_fc, ignore_keys=fc_ignore_keys)

        # Strip the RT of the download urls
        source_rt = source_rt.replace(source_fc.download_url(access_id=source_fc.download_url), '')
        target_rt = target_rt.replace(target_fc.download_url(access_id=target_fc.download_url), '')

    assert source_rt == target_rt, 'Without FC download urls the RT should remain equal after import'
