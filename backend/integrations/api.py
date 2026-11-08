from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from integrations.providers import shipping


from core.http import provider_result


class CitiesView(APIView):
    def get(self, request):
        return Response(
            provider_result(
                lambda: shipping().cities(request.query_params.get("q", "")[:100])
            )
        )


class PickupView(APIView):
    def get(self, request):
        try:
            city = int(request.query_params.get("city_code", "0"))
        except ValueError:
            raise ValidationError("Некорректный город.")
        return Response(provider_result(lambda: shipping().points(city)))
