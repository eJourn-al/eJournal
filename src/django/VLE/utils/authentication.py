from rest_framework_simplejwt.authentication import JWTAuthentication
from sentry_sdk import configure_scope

import VLE.models
import VLE.serializers


def set_sentry_user_scope(user):
    with configure_scope() as scope:
        scope.user = {
            **VLE.serializers.OwnUserSerializer(user).data,
            'id': user.pk,
        }


class SentryContextAwareJWTAuthentication(JWTAuthentication):
    """Sets context data related to the user authenticated via JWT."""
    def authenticate(self, request):
        authenticated_user = super().authenticate(request)

        if authenticated_user and isinstance(authenticated_user[0], VLE.models.User):
            set_sentry_user_scope(authenticated_user[0])

        return authenticated_user
