"""Discard personal form input before it reaches application serializers.

Only enabled in the dedicated public demonstration deployment. Admin requests
and the local source databases are never changed by this middleware.
"""
import json

from django.conf import settings
from django.http import JsonResponse


class PublicDemoInputMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'PUBLIC_DEMO', False):
            return self.get_response(request)
        if request.method == 'POST' and request.path in {
            '/api/checkout/', '/api/orders/', '/api/orders/checkout/', '/api/v1/leads/',
        }:
            safe = {
                'name': 'Демонстрационный покупатель',
                'contact_name': 'Демонстрационный посетитель',
                'email': 'guest@example.invalid',
                'phone': '+70000000000',
                'organization': 'Вымышленная организация',
                'address': 'Вымышленный демонстрационный адрес',
                'comment': 'Демонстрационный запрос',
                'description': 'Демонстрационный запрос',
                'details': 'Демонстрационный запрос',
                'site_city': 'Демонстрационный город',
            }
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    if isinstance(data, dict):
                        data.update({key: value for key, value in safe.items() if key in data})
                        request._body = json.dumps(data).encode('utf-8')
                        request.META['CONTENT_LENGTH'] = str(len(request._body))
                except (ValueError, UnicodeError):
                    pass  # The application's normal validation rejects malformed JSON.
            # Multipart input is sanitized inside the conditioners view after its
            # bounded upload handler has parsed it. Reading POST here would lock
            # upload handlers before the view can install its limits.
        response = self.get_response(request)
        response['X-Demo-Mode'] = 'public-synthetic-data-only'
        return response
