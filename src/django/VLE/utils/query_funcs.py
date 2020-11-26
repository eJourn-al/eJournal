from django.db.models import Func


class Round2(Func):
    """Postgres specific"""
    function = 'ROUND'
    template = '%(function)s(%(expressions)s::numeric, 2)'
