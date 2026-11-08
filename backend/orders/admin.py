import csv
from django.contrib import admin, messages
from django.http import HttpResponse
from .models import Order, OrderItem, PromoCode
from .services import cancel_order, mark_paid
from integrations.providers import payment, ProviderError, local_mode


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = [
        "name",
        "sku",
        "size",
        "color",
        "quantity",
        "unit_price",
        "unit_price_after_discount",
    ]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "number",
        "created_at",
        "name",
        "email",
        "status",
        "total",
        "delivery_method",
        "city",
        "cdek_tracking",
    ]
    list_filter = ["status", "delivery_method", "created_at"]
    search_fields = ["name", "email", "phone", "payment_id", "cdek_tracking"]
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    actions = [
        "cancel_pending",
        "verify_payments",
        "export_csv",
        "mark_shipped",
        "mark_complete",
    ]
    readonly_fields = [
        f.name
        for f in Order._meta.fields
        if f.name not in ("id", "cdek_tracking", "comment")
    ] + ["number"]
    fieldsets = [
        (
            "Заказ",
            {
                "fields": (
                    "number",
                    "status",
                    "created_at",
                    "expires_at",
                    "paid_at",
                    "comment",
                )
            },
        ),
        ("Покупатель", {"fields": ("name", "email", "phone", "consent_at")}),
        (
            "Доставка СДЭК",
            {
                "fields": (
                    "delivery_method",
                    "city",
                    "city_code",
                    "pickup_code",
                    "delivery_address",
                    "delivery_days",
                    "cdek_tracking",
                )
            },
        ),
        (
            "Суммы",
            {"fields": ("subtotal", "discount", "shipping_cost", "total", "promo")},
        ),
        (
            "Платёж и защита повторов",
            {
                "classes": ["collapse"],
                "fields": (
                    "payment_id",
                    "payment_url",
                    "request_key",
                    "payment_key",
                    "request_fingerprint",
                ),
            },
        ),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(
        description="Отменить неоплаченные заказы и освободить резерв",
        permissions=["change"],
    )
    def cancel_pending(self, request, queryset):
        count = 0
        for order in queryset:
            if order.payment_id and not order.payment_id.startswith("local-"):
                self.message_user(
                    request,
                    f"{order.number}: сначала проверьте статус платежа; автоматическая отмена отключена.",
                    messages.WARNING,
                )
                continue
            count += cancel_order(order)
        self.message_user(request, f"Отменено заказов: {count}.")

    @admin.action(description="Проверить оплату в ЮKassa", permissions=["change"])
    def verify_payments(self, request, queryset):
        for order in queryset.filter(status="pending").exclude(payment_id=""):
            try:
                if local_mode():
                    continue
                verified = payment().verify(order.payment_id)
                if verified.get("status") == "canceled":
                    cancel_order(order)
                else:
                    mark_paid(order, verified)
            except ProviderError:
                self.message_user(
                    request,
                    f"{order.number}: не удалось проверить платёж.",
                    messages.ERROR,
                )
        self.message_user(request, "Проверка завершена.")

    @admin.action(
        description="Передать оплаченные заказы в доставку", permissions=["change"]
    )
    def mark_shipped(self, request, queryset):
        count = (
            queryset.filter(status="paid")
            .exclude(cdek_tracking="")
            .update(status="shipped")
        )
        self.message_user(
            request,
            f"Передано: {count}. Требуется оплаченный заказ и номер отправления.",
        )

    @admin.action(description="Завершить доставленные заказы", permissions=["change"])
    def mark_complete(self, request, queryset):
        self.message_user(
            request,
            f"Завершено: {queryset.filter(status='shipped').update(status='complete')}.",
        )

    @admin.action(description="Экспорт выбранных заказов в CSV", permissions=["view"])
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="orders.csv"'
        response.write("\ufeff")
        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            [
                "Заказ",
                "Дата",
                "Покупатель",
                "Email",
                "Телефон",
                "Статус",
                "Сумма",
                "Адрес",
            ]
        )

        def safe(value):
            value = str(value)
            return (
                "'" + value
                if value.startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
            )

        for order in queryset:
            writer.writerow(
                [
                    safe(v)
                    for v in [
                        order.number,
                        order.created_at,
                        order.name,
                        order.email,
                        order.phone,
                        order.get_status_display(),
                        order.total,
                        order.delivery_address,
                    ]
                ]
            )
        return response


@admin.register(PromoCode)
class PromoAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "percent",
        "active",
        "minimum",
        "valid_until",
        "uses",
        "max_uses",
    ]
    list_filter = ["active"]
    search_fields = ["code"]
    readonly_fields = ["uses"]
