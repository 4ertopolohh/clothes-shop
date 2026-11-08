from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.urls import path
from django.utils.html import format_html, format_html_join
from core.admin import SingletonAdmin
from .models import IntegrationSettings, OperationLog, Notification
from .secrets import encrypt
from .providers import readiness
from .notifications import deliver


class IntegrationForm(forms.ModelForm):
    cdek_secret = forms.CharField(
        label="СДЭК: новый ключ",
        required=False,
        widget=forms.PasswordInput,
        help_text="Пусто — сохранить текущий. Ключ хранится зашифрованным.",
    )
    payment_secret = forms.CharField(
        label="ЮKassa: новый секретный ключ",
        required=False,
        widget=forms.PasswordInput,
        help_text="Пусто — сохранить текущий.",
    )
    smtp_secret = forms.CharField(
        label="SMTP: новый пароль",
        required=False,
        widget=forms.PasswordInput,
        help_text="Пусто — сохранить текущий.",
    )
    telegram_secret = forms.CharField(
        label="Telegram: новый токен бота",
        required=False,
        widget=forms.PasswordInput,
        help_text="Пусто — сохранить текущий.",
    )
    clear_secrets = forms.MultipleChoiceField(
        label="Удалить сохранённые секреты",
        required=False,
        choices=[
            ("cdek", "СДЭК"),
            ("payment", "ЮKassa"),
            ("smtp", "SMTP"),
            ("telegram", "Telegram"),
        ],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = IntegrationSettings
        fields = "__all__"

    def save(self, commit=True):
        obj = super().save(commit=False)
        for key in ("cdek", "payment", "smtp", "telegram"):
            if key in self.cleaned_data.get("clear_secrets", []):
                setattr(obj, key + "_secret_encrypted", b"")
            value = self.cleaned_data.get(key + "_secret")
            if value:
                setattr(obj, key + "_secret_encrypted", encrypt(value))
        if commit:
            obj.save()
        return obj


@admin.register(IntegrationSettings)
class IntegrationAdmin(SingletonAdmin):
    form = IntegrationForm
    readonly_fields = ["connection_status", "saved_secrets"]
    fieldsets = [
        (
            "Готовность подключений",
            {"fields": ("connection_status", "saved_secrets", "site_url")},
        ),
        (
            "СДЭК · города, ПВЗ и расчёт тарифа",
            {
                "fields": (
                    "cdek_enabled",
                    "cdek_sandbox",
                    "cdek_account",
                    "cdek_secret",
                    "origin_city_code",
                    "pickup_tariff",
                    "courier_tariff",
                )
            },
        ),
        (
            "ЮKassa · оплата заказа",
            {
                "fields": (
                    "yookassa_enabled",
                    "shop_id",
                    "payment_secret",
                    "receipts_enabled",
                    "vat_code",
                    "tax_system_code",
                ),
                "description": "Webhook: /api/webhooks/yookassa/. Статус платежа перепроверяется запросом в ЮKassa. Настройте публичный HTTPS-адрес перед подключением.",
            },
        ),
        (
            "Email · покупатель и магазин",
            {
                "fields": (
                    "smtp_enabled",
                    "smtp_host",
                    "smtp_port",
                    "smtp_security",
                    "smtp_user",
                    "smtp_secret",
                    "from_email",
                    "admin_email",
                )
            },
        ),
        (
            "Telegram · администратор",
            {"fields": ("telegram_enabled", "telegram_secret", "telegram_chat_id")},
        ),
        ("Удаление ключей", {"classes": ["collapse"], "fields": ("clear_secrets",)}),
    ]

    @admin.display(description="Состояние")
    def connection_status(self, obj):
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "", "<li><strong>{}</strong>: {}</li>", readiness().items()
            ),
        )

    @admin.display(description="Сохранённые секреты")
    def saved_secrets(self, obj):
        return (
            " · ".join(
                f"{title}: {'сохранён' if getattr(obj, key + '_secret_encrypted') else 'не задан'}"
                for key, title in [
                    ("cdek", "СДЭК"),
                    ("payment", "ЮKassa"),
                    ("smtp", "SMTP"),
                    ("telegram", "Telegram"),
                ]
            )
            if obj
            else "Пока не заданы"
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from django.core.cache import cache

        cache.clear()


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


@admin.register(OperationLog)
class LogAdmin(ReadOnlyAdmin):
    list_display = [
        "created_at",
        "provider",
        "operation",
        "reference",
        "mock",
        "success",
    ]
    list_filter = ["provider", "mock", "success"]
    search_fields = ["reference"]


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdmin):
    list_display = [
        "created_at",
        "order",
        "audience",
        "subject",
        "status",
        "preview_link",
    ]
    list_filter = ["status", "audience"]
    search_fields = ["order__id", "recipient"]
    actions = ["retry"]
    exclude = ["html"]
    readonly_fields = ["preview_link"]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields if f.name != "html"] + [
            "preview_link"
        ]

    @admin.display(description="Письмо")
    def preview_link(self, obj):
        return (
            format_html(
                '<a href="{}" target="_blank">Предпросмотр HTML</a>',
                f"/admin/integrations/notification/{obj.pk}/preview/",
            )
            if obj and obj.pk and obj.audience != "telegram"
            else "—"
        )

    def get_urls(self):
        return [
            path(
                "<int:pk>/preview/",
                self.admin_site.admin_view(self.preview),
                name="notification_preview",
            )
        ] + super().get_urls()

    def preview(self, request, pk):
        from django.shortcuts import get_object_or_404

        obj = get_object_or_404(Notification, pk=pk)
        if not self.has_view_permission(request, obj):
            raise PermissionDenied
        response = HttpResponse(obj.html)
        response["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
        )
        return response

    @admin.action(
        description="Повторить отправку уведомлений с ошибками", permissions=["change"]
    )
    def retry(self, request, queryset):
        for obj in queryset.filter(status__in=["pending", "failed"]):
            deliver(obj)
        self.message_user(request, "Повторная обработка завершена.")
