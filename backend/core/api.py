from django.http import Http404
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import StoreSettings, Page


class CsrfView(APIView):
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class SettingsView(APIView):
    def get(self, request):
        store = StoreSettings.get()
        fields = [
            "brand",
            "tagline",
            "announcement",
            "hero_title",
            "hero_text",
            "about_title",
            "about_text",
            "email",
            "phone",
            "address",
            "legal_details",
        ]
        result = {k: getattr(store, k) for k in fields}
        for k in ["hero_image", "about_image"]:
            result[k] = getattr(store, k).url if getattr(store, k) else ""
        result["pages"] = list(
            Page.objects.filter(published=True).values("slug", "title")
        )
        return Response(result)


class PageView(APIView):
    def get(self, request, slug):
        page = Page.objects.filter(slug=slug, published=True).first()
        if not page:
            raise Http404
        return Response(
            {"title": page.title, "description": page.description, "body": page.body}
        )
