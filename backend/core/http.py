from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from integrations.providers import ProviderError


def provider_result(fn):
    try:
        return fn()
    except ProviderError as exc:
        error = APIException(str(exc))
        error.status_code = 503
        raise error from None


@method_decorator(csrf_protect, name="dispatch")
class MutationView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response
