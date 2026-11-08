import json
from pathlib import Path
from django.core.management.base import BaseCommand
from core.api import SettingsView
from catalog.api import FacetsView, product_data
from catalog.models import Product
from core.models import Page
from integrations.models import IntegrationSettings


class Command(BaseCommand):
    help = "Снимок только публичного контента для предрендеринга. Заказы, ключи и приватные настройки исключены."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        products = [
            product_data(p)
            for p in Product.objects.filter(active=True)
            .select_related("category")
            .prefetch_related("variants", "images")
        ]
        data = {
            "/settings/": SettingsView().get(None).data,
            "/catalog/facets/": FacetsView().get(None).data,
            "/catalog/?&page=1": {
                "count": len(products),
                "next": 2 if len(products) > 9 else None,
                "results": products[:9],
            },
        }
        for product in products:
            data["/products/" + product["slug"] + "/"] = product
        for page in Page.objects.filter(published=True):
            data["/pages/" + page.slug + "/"] = {
                "title": page.title,
                "description": page.description,
                "body": page.body,
            }
        target = Path(options["output"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {"data": data, "site_url": IntegrationSettings.get().site_url},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.stdout.write(f"Экспортировано публичных товаров: {len(products)}.")
