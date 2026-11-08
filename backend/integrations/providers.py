"""Fixed provider hosts; secrets and external failures never enter public responses."""

from decimal import Decimal
import httpx
from django.conf import settings
from django.core.cache import cache
from core.models import StoreSettings
from .models import IntegrationSettings
from .secrets import decrypt


class ProviderError(Exception):
    pass


def local_mode():
    enabled = StoreSettings.get().local_test_mode
    if enabled and not settings.LOCAL_DEVELOPMENT:
        raise ProviderError("Локальный режим заблокирован конфигурацией сервера.")
    return enabled and settings.LOCAL_DEVELOPMENT


MOCK_CITIES = [
    {"code": 44, "city": "Москва"},
    {"code": 137, "city": "Санкт-Петербург"},
    {"code": 250, "city": "Екатеринбург"},
    {"code": 424, "city": "Казань"},
    {"code": 270, "city": "Новосибирск"},
]


class MockShipping:
    def cities(self, query):
        return [x for x in MOCK_CITIES if query.casefold() in x["city"].casefold()]

    def points(self, city_code):
        city = next((x["city"] for x in MOCK_CITIES if x["code"] == city_code), None)
        if not city:
            raise ProviderError("Выберите город из списка.")
        return [
            {
                "code": f"LOCAL-{city_code}-{i}",
                "name": f"Пункт выдачи {i + 1}",
                "address": f"{city}, {street}",
                "hours": "Пн–Вс 10:00–20:00",
                "city_code": city_code,
            }
            for i, street in enumerate(
                ["ул. Центральная, 12", "ул. Садовая, 28", "проспект Мира, 42"]
            )
        ]

    def quote(self, city_code, method, packages):
        if city_code not in [x["code"] for x in MOCK_CITIES]:
            raise ProviderError("Выберите город из списка.")
        price = Decimal("390") if city_code == 44 else Decimal("590")
        return {
            "cost": str(price + (Decimal("250") if method == "courier" else 0)),
            "days": "2–5 рабочих дней",
        }


class RealShipping:
    def __init__(self, config):
        self.config = config
        if (
            not config.cdek_enabled
            or not config.cdek_account
            or not config.cdek_secret_encrypted
        ):
            raise ProviderError("СДЭК не настроен. Свяжитесь с магазином.")
        self.base = (
            "https://api.edu.cdek.ru/v2"
            if config.cdek_sandbox
            else "https://api.cdek.ru/v2"
        )

    def request(self, method, path, **kwargs):
        token_key = f"cdek-token:{self.config.pk}:{self.config.cdek_sandbox}:{self.config.cdek_account}"
        token = cache.get(token_key)
        try:
            if not token:
                response = httpx.post(
                    self.base + "/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.config.cdek_account,
                        "client_secret": decrypt(self.config.cdek_secret_encrypted),
                    },
                    timeout=12,
                )
                response.raise_for_status()
                auth = response.json()
                token = auth["access_token"]
                cache.set(
                    token_key, token, min(int(auth.get("expires_in", 300)) - 30, 1800)
                )
            response = httpx.request(
                method,
                self.base + path,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError, KeyError):
            raise ProviderError(
                "СДЭК временно недоступен. Попробуйте ещё раз."
            ) from None

    def cities(self, query):
        if len(query) < 2:
            return []
        data = self.request(
            "GET",
            "/location/cities",
            params={"city": query, "country_codes": "RU", "size": 20},
        )
        return [
            {"code": x["code"], "city": x["city"], "region": x.get("region", "")}
            for x in data
        ][:20]

    def points(self, city_code):
        data = self.request(
            "GET",
            "/deliverypoints",
            params={"city_code": city_code, "type": "PVZ", "is_handout": True},
        )
        return [
            {
                "code": x["code"],
                "name": x.get("name", "Пункт выдачи"),
                "address": x["location"].get(
                    "address_full", x["location"].get("address", "")
                ),
                "hours": x.get("work_time", ""),
                "city_code": city_code,
            }
            for x in data
            if x.get("is_handout", True)
        ][:300]

    def quote(self, city_code, method, packages):
        result = self.request(
            "POST",
            "/calculator/tariff",
            json={
                "type": 1,
                "currency": 1,
                "tariff_code": self.config.courier_tariff
                if method == "courier"
                else self.config.pickup_tariff,
                "from_location": {"code": self.config.origin_city_code},
                "to_location": {"code": city_code},
                "packages": packages,
            },
        )
        if "delivery_sum" not in result:
            raise ProviderError(
                "Не удалось рассчитать доставку по выбранному направлению."
            )
        return {
            "cost": str(result["delivery_sum"]),
            "days": f"{result.get('period_min', 2)}–{result.get('period_max', 7)} рабочих дней",
        }


def shipping():
    return MockShipping() if local_mode() else RealShipping(IntegrationSettings.get())


class MockPayment:
    def create(self, order):
        return {
            "id": f"local-{order.pk}",
            "status": "pending",
            "url": f"/payment/{order.token}",
            "amount": {"value": str(order.total), "currency": "RUB"},
        }


class RealPayment:
    def __init__(self):
        self.config = IntegrationSettings.get()
        if (
            not self.config.yookassa_enabled
            or not self.config.shop_id
            or not self.config.payment_secret_encrypted
        ):
            raise ProviderError("Оплата пока недоступна. Свяжитесь с магазином.")

    def request(self, method, path, **kwargs):
        try:
            response = httpx.request(
                method,
                "https://api.yookassa.ru/v3" + path,
                auth=(
                    self.config.shop_id,
                    decrypt(self.config.payment_secret_encrypted),
                ),
                timeout=20,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ProviderError(
                "Платёжный сервис временно недоступен. Повторите попытку."
            ) from None

    def create(self, order):
        return_url = self.config.site_url.rstrip("/") + "/order/" + order.token
        payload = {
            "amount": {"value": str(order.total), "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": f"Заказ {order.number}",
            "metadata": {"order_id": str(order.pk)},
        }
        if self.config.receipts_enabled:
            items = [
                {
                    "description": i.name[:128],
                    "quantity": str(i.quantity),
                    "amount": {
                        "value": str(i.unit_price_after_discount),
                        "currency": "RUB",
                    },
                    "vat_code": self.config.vat_code,
                    "payment_subject": "commodity",
                    "payment_mode": "full_payment",
                }
                for i in order.items.all()
            ]
            if order.shipping_cost:
                items.append(
                    {
                        "description": "Доставка",
                        "quantity": "1",
                        "amount": {
                            "value": str(order.shipping_cost),
                            "currency": "RUB",
                        },
                        "vat_code": self.config.vat_code,
                        "payment_subject": "service",
                        "payment_mode": "full_payment",
                    }
                )
            payload["receipt"] = {
                "customer": {"email": order.email},
                "items": items,
                "tax_system_code": self.config.tax_system_code,
            }
        data = self.request(
            "POST",
            "/payments",
            json=payload,
            headers={"Idempotence-Key": str(order.payment_key)},
        )
        url = data.get("confirmation", {}).get("confirmation_url", "")
        if not url.startswith("https://"):
            raise ProviderError("Не удалось получить ссылку на оплату.")
        return {
            "id": data["id"],
            "status": data["status"],
            "url": url,
            "amount": data["amount"],
        }

    def verify(self, payment_id):
        if not payment_id or any(
            c not in "0123456789abcdef-" for c in payment_id.lower()
        ):
            raise ProviderError("Некорректный идентификатор платежа.")
        return self.request("GET", "/payments/" + payment_id)


def payment():
    return MockPayment() if local_mode() else RealPayment()


def readiness():
    c = IntegrationSettings.get()
    return {
        "Режим": "Локальный: внешние операции имитируются"
        if local_mode()
        else "Реальные сервисы",
        "СДЭК": "Настроен"
        if c.cdek_enabled and c.cdek_account and c.cdek_secret_encrypted
        else "Требуются Account и ключ",
        "ЮKassa": "Настроена"
        if c.yookassa_enabled and c.shop_id and c.payment_secret_encrypted
        else "Требуются shopId и ключ",
        "Email": "Настроен"
        if c.smtp_enabled and c.smtp_host
        else "Требуются настройки SMTP",
        "Telegram": "Настроен"
        if c.telegram_enabled and c.telegram_chat_id and c.telegram_secret_encrypted
        else "Требуются токен и ID чата",
    }
