from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class ExtendedPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        """Ensure code_version is part of the paginated response."""
        response = super().get_paginated_response(data)
        response.data['code_version'] = settings.CODE_VERSION

        return response
