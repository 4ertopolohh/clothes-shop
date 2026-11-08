import hashlib
import json
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from catalog.models import Variant
from core.models import StoreSettings
from integrations.providers import shipping, payment, ProviderError
from .models import Order, OrderItem, PromoCode


def money(value):
    return Decimal(value).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def cancel_order(order):
    if not Order.objects.filter(pk=order.pk, status="pending").update(
        status="canceled"
    ):
        return False
    for item in order.items.all():
        Variant.objects.filter(pk=item.variant_id, reserved__gte=item.quantity).update(
            reserved=F("reserved") - item.quantity
        )
    if order.promo_id:
        PromoCode.objects.filter(pk=order.promo_id, uses__gt=0).update(
            uses=F("uses") - 1
        )
    return True


def expire_reservations():
    for order in Order.objects.filter(
        status="pending", expires_at__lt=timezone.now()
    ).prefetch_related("items")[:200]:
        # A created external payment may have succeeded while its notification was delayed.
        # Preserve that reserve until payment reconciliation; never release potentially paid stock.
        if order.payment_id and not order.payment_id.startswith("local-"):
            continue
        cancel_order(order)


def cart_lines(items):
    totals = {}
    for item in items:
        totals[item["variant_id"]] = (
            totals.get(item["variant_id"], 0) + item["quantity"]
        )
    variants = {
        v.pk: v
        for v in Variant.objects.filter(
            pk__in=totals, active=True, product__active=True
        ).select_related("product")
    }
    if len(variants) != len(totals):
        raise ValidationError(
            {"items": "Один из товаров больше недоступен. Обновите корзину."}
        )
    lines = []
    for pk, quantity in totals.items():
        v = variants[pk]
        if quantity > 30 or quantity > v.available:
            raise ValidationError(
                {
                    "items": f"{v.product.name}, {v.size}, {v.color}: доступно {v.available} шт."
                }
            )
        lines.append((v, quantity))
    return sorted(lines, key=lambda pair: pair[0].pk)


def calculate(items, promo_code="", city_code=None, method="pickup"):
    lines = cart_lines(items)
    subtotal = sum((v.price * q for v, q in lines), Decimal("0"))
    promo = None
    if promo_code:
        promo = PromoCode.objects.filter(
            code=promo_code.strip().upper(), active=True
        ).first()
        if (
            not promo
            or promo.minimum > subtotal
            or (promo.valid_until and promo.valid_until < timezone.now())
            or (promo.max_uses is not None and promo.uses >= promo.max_uses)
        ):
            raise ValidationError(
                {"promo": "Промокод недействителен или не подходит к этой сумме."}
            )
    rate = Decimal(100 - promo.percent) / 100 if promo else Decimal(1)
    discounted = sum((money(v.price * rate) * q for v, q in lines), Decimal(0))
    delivery = {"cost": "0.00", "days": ""}
    if city_code:
        packages = [
            {
                "weight": v.product.weight * q,
                "length": v.product.length,
                "width": v.product.width,
                "height": v.product.height * q,
            }
            for v, q in lines
        ]
        delivery = shipping().quote(city_code, method, packages)
    return {
        "lines": lines,
        "promo_obj": promo,
        "rate": rate,
        "subtotal": money(subtotal),
        "discount": money(subtotal - discounted),
        "shipping_cost": money(delivery["cost"]),
        "total": money(discounted + Decimal(delivery["cost"])),
        "delivery_days": delivery["days"],
    }


def public_quote(result):
    return {
        k: str(result[k])
        for k in ("subtotal", "discount", "shipping_cost", "total", "delivery_days")
    }


def create_order(data):
    expire_reservations()
    fingerprint = hashlib.sha256(
        json.dumps(
            {k: v for k, v in data.items() if k != "request_key"},
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    existing = Order.objects.filter(request_key=data["request_key"]).first()
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise ValidationError(
                {"request_key": "Этот запрос уже использован для другого заказа."}
            )
        return existing
    result = calculate(
        data["items"], data.get("promo", ""), data["city_code"], data["delivery_method"]
    )
    provider = shipping()
    cities = provider.cities(data["city"])
    city = next((x for x in cities if x["code"] == data["city_code"]), None)
    if not city:
        raise ValidationError({"city": "Выберите город из результатов поиска."})
    address = data.get("address", "").strip()
    if data["delivery_method"] == "pickup":
        point = next(
            (
                p
                for p in provider.points(data["city_code"])
                if p["code"] == data.get("pickup_code")
            ),
            None,
        )
        if not point:
            raise ValidationError({"pickup_code": "Выберите действующий пункт выдачи."})
        address = point["address"]
    elif len(address) < 8:
        raise ValidationError({"address": "Укажите улицу, дом и квартиру."})
    with transaction.atomic():
        order = Order.objects.create(
            request_key=data["request_key"],
            request_fingerprint=fingerprint,
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            city=city["city"],
            city_code=city["code"],
            delivery_method=data["delivery_method"],
            pickup_code=data.get("pickup_code", "")
            if data["delivery_method"] == "pickup"
            else "",
            delivery_address=address,
            comment=data.get("comment", ""),
            promo=result["promo_obj"],
            expires_at=timezone.now()
            + timedelta(minutes=StoreSettings.get().reservation_minutes),
            **{
                k: result[k]
                for k in (
                    "subtotal",
                    "discount",
                    "shipping_cost",
                    "total",
                    "delivery_days",
                )
            },
        )
        promo = result["promo_obj"]
        if promo:
            qs = PromoCode.objects.filter(pk=promo.pk, active=True).filter(
                Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now())
            )
            if promo.max_uses is not None:
                qs = qs.filter(uses__lt=promo.max_uses)
            if not qs.update(uses=F("uses") + 1):
                raise ValidationError({"promo": "Лимит промокода исчерпан."})
        for variant, quantity in result["lines"]:
            if not Variant.objects.filter(
                pk=variant.pk, active=True, stock__gte=F("reserved") + quantity
            ).update(reserved=F("reserved") + quantity):
                raise ValidationError(
                    {"items": "Количество изменилось. Обновите корзину."}
                )
            OrderItem.objects.create(
                order=order,
                variant=variant,
                name=variant.product.name,
                sku=variant.sku,
                size=variant.size,
                color=variant.color,
                quantity=quantity,
                unit_price=variant.price,
                unit_price_after_discount=money(variant.price * result["rate"]),
            )
        from integrations.notifications import queue_notifications

        transaction.on_commit(lambda: queue_notifications(order.pk, "created"))
    return order


def start_payment(order):
    if order.status != "pending":
        raise ValidationError("Этот заказ уже оплачен или отменён.")
    if order.expires_at < timezone.now() and not order.payment_id:
        cancel_order(order)
        raise ValidationError("Время резерва истекло. Оформите заказ повторно.")
    if order.payment_url:
        return order.payment_url
    response = payment().create(order)
    Order.objects.filter(pk=order.pk, status="pending").update(
        payment_id=response["id"], payment_url=response["url"]
    )
    return response["url"]


@transaction.atomic
def mark_paid(order, verification):
    if verification.get("status") != "succeeded":
        return False
    amount = verification.get("amount", {})
    if (
        amount.get("currency") != "RUB"
        or money(amount.get("value", "0")) != order.total
        or str(verification.get("metadata", {}).get("order_id", order.pk))
        != str(order.pk)
    ):
        raise ProviderError("Параметры подтверждённого платежа не совпадают с заказом.")
    if not Order.objects.filter(pk=order.pk, status="pending").update(
        status="paid", paid_at=timezone.now()
    ):
        return False
    for item in order.items.all():
        if not Variant.objects.filter(
            pk=item.variant_id, reserved__gte=item.quantity, stock__gte=item.quantity
        ).update(
            reserved=F("reserved") - item.quantity, stock=F("stock") - item.quantity
        ):
            raise ProviderError("Не удалось списать резерв. Обратитесь в магазин.")
    from integrations.notifications import queue_notifications

    transaction.on_commit(lambda: queue_notifications(order.pk, "paid"))
    return True
