import json
import uuid
from django.test import TestCase, Client, override_settings
from catalog.models import Category, Product, Variant
from core.models import StoreSettings
from integrations.models import IntegrationSettings, Notification
from .models import Order, PromoCode


class PurchaseTests(TestCase):
    def setUp(self):
        StoreSettings.get()
        IntegrationSettings.get()
        category = Category.objects.create(name="Рубашки", slug="shirts")
        self.product = Product.objects.create(
            name="Рубашка", slug="shirt", category=category, description="Хлопок"
        )
        self.variant = Variant.objects.create(
            product=self.product,
            sku="SHIRT-M",
            size="M",
            color="Чёрный",
            price="1000.00",
            stock=3,
        )
        PromoCode.objects.create(code="FORM10", percent=10)
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get("/api/csrf/").json()["csrfToken"]

    def post(self, path, data):
        return self.client.post(
            path,
            json.dumps(data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf,
        )

    def payload(self, quantity=1):
        return {
            "items": [{"variant_id": self.variant.pk, "quantity": quantity}],
            "request_key": str(uuid.uuid4()),
            "name": "Анна Тестовая",
            "email": "buyer@example.test",
            "phone": "+79991234567",
            "city": "Москва",
            "city_code": 44,
            "delivery_method": "pickup",
            "pickup_code": "LOCAL-44-0",
            "consent": True,
            "promo": "FORM10",
        }

    def test_csrf_is_required_even_without_buyer_account(self):
        response = Client(enforce_csrf_checks=True).post(
            "/api/orders/", json.dumps(self.payload()), content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_reserves_stock_calculates_discount_and_delivers_three_local_notifications(
        self,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.post("/api/orders/", self.payload(2))
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["subtotal"], "2000.00")
        self.assertEqual(data["discount"], "200.00")
        self.assertEqual(data["total"], "2190.00")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.reserved, 2)
        self.assertEqual(self.variant.available, 1)
        self.assertEqual(Notification.objects.filter(status="simulated").count(), 3)
        self.assertIn(
            "ATELIER NOIR", Notification.objects.get(audience="customer").html
        )

    def test_double_submit_returns_same_order_and_changed_payload_is_rejected(self):
        payload = self.payload()
        first = self.post("/api/orders/", payload)
        second = self.post("/api/orders/", payload)
        self.assertEqual(first.json()["token"], second.json()["token"])
        self.assertEqual(Order.objects.count(), 1)
        payload["name"] = "Другой покупатель"
        self.assertEqual(self.post("/api/orders/", payload).status_code, 400)

    def test_second_order_cannot_take_reserved_quantity(self):
        self.assertEqual(self.post("/api/orders/", self.payload(3)).status_code, 201)
        self.assertEqual(self.post("/api/orders/", self.payload()).status_code, 400)
        self.assertEqual(Order.objects.count(), 1)

    def test_payment_is_idempotent_and_releases_reserved_stock_once(self):
        data = self.post("/api/orders/", self.payload()).json()
        url = f"/api/orders/{data['token']}/local-payment/"
        for _ in range(2):
            with self.captureOnCommitCallbacks(execute=True):
                result = self.post(url, {})
            self.assertEqual(result.json()["status"], "paid")
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 2)
        self.assertEqual(self.variant.reserved, 0)
        self.assertEqual(Notification.objects.filter(event="paid").count(), 3)

    def test_tampered_prices_are_ignored(self):
        payload = self.payload()
        payload["total"] = "0.01"
        payload["items"][0]["price"] = "0.01"
        self.assertEqual(self.post("/api/orders/", payload).json()["total"], "1290.00")

    def test_foreign_pickup_point_and_invalid_consent_are_rejected(self):
        payload = self.payload()
        payload["pickup_code"] = "LOCAL-137-0"
        self.assertEqual(self.post("/api/orders/", payload).status_code, 400)
        payload = self.payload()
        payload["consent"] = False
        self.assertEqual(self.post("/api/orders/", payload).status_code, 400)

    def test_guest_cannot_access_staff_or_guess_orders(self):
        self.assertEqual(self.client.get("/admin/orders/order/").status_code, 302)
        self.assertEqual(
            self.client.get("/api/orders/not-a-real-token/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/orders/").status_code, 405)
        self.assertNotIn("local_test_mode", self.client.get("/api/settings/").json())

    @override_settings(LOCAL_DEVELOPMENT=False)
    def test_production_blocks_local_payment(self):
        response = self.post("/api/orders/unknown/local-payment/", {})
        self.assertEqual(response.status_code, 503)

    def test_wrong_payment_amount_does_not_mark_order_paid(self):
        from .services import mark_paid
        from integrations.providers import ProviderError

        data = self.post("/api/orders/", self.payload()).json()
        order = Order.objects.get(token=data["token"])
        with self.assertRaises(ProviderError):
            mark_paid(
                order,
                {"status": "succeeded", "amount": {"value": "0.01", "currency": "RUB"}},
            )
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_combined_filters_apply_to_same_variant(self):
        Variant.objects.create(
            product=self.product,
            sku="SHIRT-L-WHITE",
            size="L",
            color="Молочный",
            price=2000,
            stock=3,
        )
        data = self.client.get("/api/catalog/?size=M&color=Молочный").json()
        self.assertEqual(data["count"], 0)

    def test_facets_do_not_duplicate_sizes_and_colors(self):
        Variant.objects.create(
            product=self.product,
            sku="SHIRT-S",
            size="S",
            color="Чёрный",
            price=1000,
            stock=2,
        )
        data = self.client.get("/api/catalog/facets/").json()
        self.assertEqual(sorted(data["sizes"]), ["M", "S"])
        self.assertEqual(len(data["colors"]), 1)

    def test_real_payment_uses_stable_key_and_webhook_checks_provider_status(self):
        import httpx
        from unittest.mock import patch
        from integrations.secrets import encrypt

        result = self.post("/api/orders/", self.payload()).json()
        store = StoreSettings.get()
        store.local_test_mode = False
        store.save()
        config = IntegrationSettings.get()
        config.yookassa_enabled = True
        config.shop_id = "test-shop"
        config.payment_secret_encrypted = encrypt("test-secret")
        config.save()
        payment_id = str(uuid.uuid4())
        payment_result = {
            "id": payment_id,
            "status": "pending",
            "amount": {"value": "1290.00", "currency": "RUB"},
            "metadata": {"order_id": str(Order.objects.get().pk)},
            "confirmation": {"confirmation_url": "https://yookassa.ru/checkout/test"},
        }
        with patch(
            "integrations.providers.httpx.request",
            return_value=httpx.Response(
                200,
                json=payment_result,
                request=httpx.Request("POST", "https://api.yookassa.ru/v3/payments"),
            ),
        ) as network:
            response = self.post("/api/orders/" + result["token"] + "/payment/", {})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                network.call_args.kwargs["headers"]["Idempotence-Key"],
                str(Order.objects.get().payment_key),
            )
        forged = {
            "event": "payment.succeeded",
            "object": {"id": payment_id, "status": "succeeded"},
        }
        with patch(
            "integrations.providers.httpx.request",
            return_value=httpx.Response(
                200,
                json=payment_result,
                request=httpx.Request(
                    "GET", "https://api.yookassa.ru/v3/payments/" + payment_id
                ),
            ),
        ):
            self.assertEqual(
                self.post("/api/webhooks/yookassa/", forged).status_code, 200
            )
        self.assertEqual(Order.objects.get().status, "pending")
        payment_result["status"] = "succeeded"
        with patch(
            "integrations.providers.httpx.request",
            return_value=httpx.Response(
                200,
                json=payment_result,
                request=httpx.Request(
                    "GET", "https://api.yookassa.ru/v3/payments/" + payment_id
                ),
            ),
        ):
            self.assertEqual(
                self.post("/api/webhooks/yookassa/", forged).status_code, 200
            )
        self.assertEqual(Order.objects.get().status, "paid")
