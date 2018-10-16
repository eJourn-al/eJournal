
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class GDPRThrottle(SimpleRateThrottle):
    rate = api_settings.DEFAULT_THROTTLE_RATES['gdpr']
    history = []

    def allow_request(self, request, view):
        if request.path != '/users/0/GDPR/':
            return True
        if request.user.is_superuser:
            return True
        return super(GDPRThrottle, self).allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
