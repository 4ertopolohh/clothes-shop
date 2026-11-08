from django.http import Http404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.throttling import ScopedRateThrottle
from orders.models import Order
from orders.serializers import QuoteInput, OrderInput
from orders.services import (
    calculate,
    public_quote,
    create_order,
    expire_reservations,
    start_payment,
    mark_paid,
)
from integrations.providers import payment, local_mode


from core.http import provider_result, MutationView


class QuoteView(MutationView):
    def post(self, request):
        expire_reservations()
        s = QuoteInput(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            provider_result(
                lambda: public_quote(
                    calculate(
                        s.validated_data["items"],
                        s.validated_data.get("promo", ""),
                        s.validated_data.get("city_code"),
                        s.validated_data["delivery_method"],
                    )
                )
            )
        )


def order_data(order):
    return {
        "number": order.number,
        "token": order.token,
        "status": order.status,
        "status_label": order.get_status_display(),
        "created_at": order.created_at,
        "expires_at": order.expires_at,
        "delivery_address": order.delivery_address,
        "delivery_method": order.get_delivery_method_display(),
        "delivery_days": order.delivery_days,
        "tracking": order.cdek_tracking,
        "subtotal": str(order.subtotal),
        "discount": str(order.discount),
        "shipping_cost": str(order.shipping_cost),
        "total": str(order.total),
        "items": [
            {
                "name": i.name,
                "size": i.size,
                "color": i.color,
                "quantity": i.quantity,
                "price": str(i.unit_price_after_discount),
                "total": str(i.line_total),
            }
            for i in order.items.all()
        ],
    }


def find_order(token):
    order = Order.objects.filter(token=token).prefetch_related("items").first()
    if not order:
        raise Http404
    return order


class CheckoutView(MutationView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "checkout"

    def post(self, request):
        s = OrderInput(data=request.data)
        s.is_valid(raise_exception=True)
        from django.db import IntegrityError, OperationalError

        try:
            order = provider_result(lambda: create_order(s.validated_data))
        except IntegrityError:
            order = Order.objects.filter(
                request_key=s.validated_data["request_key"]
            ).first()
            if not order:
                raise ValidationError("Не удалось оформить заказ. Проверьте корзину.")
            # Re-enter the normal idempotency check, including its payload fingerprint.
            order = create_order(s.validated_data)
        except OperationalError:
            error = APIException("Магазин обрабатывает другой заказ. Повторите запрос.")
            error.status_code = 409
            raise error from None
        return Response(order_data(order), status=201)


class OrderView(APIView):
    def get(self, request, token):
        expire_reservations()
        order = find_order(token)
        if (
            order.status == "pending"
            and order.payment_id
            and not order.payment_id.startswith("local-")
        ):

            def verify():
                result = payment().verify(order.payment_id)
                if result.get("status") == "succeeded":
                    mark_paid(order, result)
                elif result.get("status") == "canceled":
                    from orders.services import cancel_order

                    cancel_order(order)

            provider_result(verify)
            order.refresh_from_db()
        return Response(order_data(order), headers={"Cache-Control": "no-store"})


class PaymentView(MutationView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    def post(self, request, token):
        return Response(
            {"url": provider_result(lambda: start_payment(find_order(token)))}
        )


class LocalPaymentView(MutationView):
    def get(self, request, token):
        if not provider_result(local_mode):
            raise Http404
        return Response(order_data(find_order(token)))

    def post(self, request, token):
        if not provider_result(local_mode):
            raise Http404
        order = find_order(token)
        if order.expires_at < timezone.now():
            from orders.services import cancel_order

            cancel_order(order)
            raise ValidationError("Срок резерва истёк.")
        provider_result(
            lambda: mark_paid(
                order,
                {
                    "status": "succeeded",
                    "amount": {"value": str(order.total), "currency": "RUB"},
                },
            )
        )
        order.refresh_from_db()
        return Response(order_data(order), headers={"Cache-Control": "no-store"})


class WebhookView(APIView):
    authentication_classes = []

    def post(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError("Ожидается объект уведомления.")
        if provider_result(local_mode):
            return Response({"accepted": True})
        payment_id = (
            request.data.get("object", {}).get("id", "")
            if isinstance(request.data.get("object"), dict)
            else ""
        )
        order = (
            Order.objects.filter(payment_id=payment_id).exclude(payment_id="").first()
        )
        if order:

            def process():
                verified = payment().verify(payment_id)
                if verified.get("status") == "canceled":
                    from orders.services import cancel_order

                    cancel_order(order)
                else:
                    mark_paid(order, verified)

            provider_result(process)
        return Response({"accepted": True})
