from django.db.models import Min, Q
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from catalog.models import Product, Category, Variant
from orders.services import (
    expire_reservations,
)


def product_data(product):
    variants = [
        {
            "id": v.pk,
            "sku": v.sku,
            "size": v.size,
            "color": v.color,
            "color_hex": v.color_hex,
            "price": str(v.price),
            "available": v.available,
        }
        for v in product.variants.all()
        if v.active
    ]
    return {
        "id": product.pk,
        "name": product.name,
        "slug": product.slug,
        "category": product.category.name,
        "category_slug": product.category.slug,
        "description": product.description,
        "characteristics": product.characteristics,
        "badge": product.badge,
        "is_new": product.is_new,
        "price": str(
            min((v.price for v in product.variants.all() if v.active), default=0)
        ),
        "images": [
            {"url": i.image.url, "alt": i.alt or product.name}
            for i in product.images.all()
        ],
        "variants": variants,
    }


class CatalogView(APIView):
    def get(self, request):
        expire_reservations()
        params = request.query_params
        qs = (
            Product.objects.filter(active=True, variants__active=True)
            .select_related("category")
            .prefetch_related("images", "variants")
            .distinct()
        )
        if params.get("q"):
            qs = qs.filter(name__icontains=params["q"][:150])
        if params.get("category"):
            qs = qs.filter(category__slug__in=params["category"].split(",")[:20])
        if params.get("new") == "1":
            qs = qs.filter(is_new=True)
        variant_filters = {"active": True}
        if params.get("size"):
            variant_filters["size__in"] = params["size"].split(",")[:20]
        if params.get("color"):
            variant_filters["color__in"] = params["color"].split(",")[:20]
        if params.get("max_price"):
            try:
                variant_filters["price__lte"] = max(
                    0, min(100000000, int(params["max_price"]))
                )
            except ValueError:
                raise ValidationError("Некорректная цена.")
        if len(variant_filters) > 1:
            qs = qs.filter(
                pk__in=Variant.objects.filter(**variant_filters).values("product_id")
            )
        sort = params.get("sort", "default")
        if sort in ("price_asc", "price_desc"):
            qs = qs.annotate(
                min_price=Min("variants__price", filter=Q(variants__active=True))
            ).order_by("min_price" if sort == "price_asc" else "-min_price", "id")
        elif sort == "new":
            qs = qs.order_by("-is_new", "-id")
        count = qs.count()
        try:
            page = max(1, int(params.get("page", "1")))
        except ValueError:
            raise ValidationError("Некорректная страница.")
        return Response(
            {
                "count": count,
                "next": page + 1 if page * 9 < count else None,
                "results": [product_data(p) for p in qs[(page - 1) * 9 : page * 9]],
            }
        )


class FacetsView(APIView):
    def get(self, request):
        qs = Variant.objects.filter(active=True, product__active=True)
        return Response(
            {
                "categories": list(
                    Category.objects.filter(products__active=True)
                    .distinct()
                    .values("name", "slug")
                ),
                "sizes": list(qs.order_by().values_list("size", flat=True).distinct()),
                "colors": list(qs.order_by().values("color", "color_hex").distinct()),
                "max_price": max(
                    40000, int(max(qs.values_list("price", flat=True), default=40000))
                ),
            }
        )


class ProductView(APIView):
    def get(self, request, slug):
        expire_reservations()
        product = (
            Product.objects.filter(slug=slug, active=True)
            .select_related("category")
            .prefetch_related("images", "variants")
            .first()
        )
        if not product:
            raise Http404
        return Response(product_data(product))
