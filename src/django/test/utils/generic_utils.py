from django.db.models.fields.related import ManyToManyField


def _to_dict(instance, ignore=[]):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if f.name in ignore:
            continue
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                data[f.name] = list(f.value_from_object(instance).values_list('pk', flat=True))
        else:
            data[f.name] = f.value_from_object(instance)

    return data


def _equal_dicts(d1, d2, ignore=[]):
    for k, v in d1.items():
        if d2[k] != v:
            return False

    return True


def equal_models(m1, m2, ignore=[]):
    d1, d2 = _to_dict(m1, ignore), _to_dict(m2, ignore)
    return _equal_dicts(d1, d2, ignore)
