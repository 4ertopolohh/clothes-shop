from django.db import models
from core.models import Singleton


class IntegrationSettings(Singleton):
    cdek_enabled = models.BooleanField("Подключить СДЭК", default=False)
    cdek_account = models.CharField("СДЭК: Account", max_length=200, blank=True)
    cdek_secret_encrypted = models.BinaryField(
        "СДЭК: зашифрованный ключ", default=bytes, editable=False
    )
    cdek_sandbox = models.BooleanField("СДЭК: тестовый API", default=True)
    origin_city_code = models.PositiveIntegerField(
        "СДЭК: код города отправления",
        default=44,
        help_text="Код из справочника СДЭК. 44 — Москва.",
    )
    pickup_tariff = models.PositiveIntegerField("Тариф до ПВЗ", default=136)
    courier_tariff = models.PositiveIntegerField("Курьерский тариф", default=137)
    yookassa_enabled = models.BooleanField("Подключить ЮKassa", default=False)
    shop_id = models.CharField("ЮKassa: shopId", max_length=100, blank=True)
    payment_secret_encrypted = models.BinaryField(
        "ЮKassa: зашифрованный ключ", default=bytes, editable=False
    )
    site_url = models.URLField(
        "Адрес витрины",
        default="http://127.0.0.1:5173",
        help_text="В production — HTTPS. Адрес возврата после оплаты формируется автоматически.",
    )
    receipts_enabled = models.BooleanField(
        "Передавать чеки в ЮKassa",
        default=False,
        help_text="Согласуйте фискализацию и налоговые параметры с вашим провайдером перед включением.",
    )
    vat_code = models.PositiveSmallIntegerField("Код НДС ЮKassa", default=1)
    tax_system_code = models.PositiveSmallIntegerField(
        "Система налогообложения", default=2
    )
    smtp_enabled = models.BooleanField("Отправлять email", default=False)
    smtp_host = models.CharField("SMTP: сервер", max_length=200, blank=True)
    smtp_port = models.PositiveIntegerField("SMTP: порт", default=587)
    smtp_user = models.CharField("SMTP: логин", max_length=200, blank=True)
    smtp_secret_encrypted = models.BinaryField(
        "SMTP: зашифрованный пароль", default=bytes, editable=False
    )
    smtp_security = models.CharField(
        "SMTP: защита",
        max_length=10,
        default="tls",
        choices=[("tls", "STARTTLS"), ("ssl", "SSL/TLS")],
    )
    from_email = models.EmailField(
        "Отправитель писем", default="orders@ateliernoir.example"
    )
    admin_email = models.EmailField(
        "Почта магазина для заказов", default="store@ateliernoir.example"
    )
    telegram_enabled = models.BooleanField(
        "Уведомлять администратора в Telegram", default=False
    )
    telegram_secret_encrypted = models.BinaryField(
        "Telegram: зашифрованный токен", default=bytes, editable=False
    )
    telegram_chat_id = models.CharField("Telegram: ID чата", max_length=100, blank=True)

    class Meta:
        verbose_name = "Настройки интеграций"
        verbose_name_plural = "СДЭК, ЮKassa, почта и Telegram"

    def __str__(self):
        return "Подключения магазина"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.conf import settings

        if not settings.LOCAL_DEVELOPMENT and not self.site_url.startswith("https://"):
            raise ValidationError({"site_url": "Для production необходим HTTPS."})
        if self.vat_code not in range(1, 13):
            raise ValidationError({"vat_code": "Проверьте код НДС ЮKassa."})
        if self.tax_system_code not in range(1, 7):
            raise ValidationError({"tax_system_code": "Допустимы коды от 1 до 6."})


class OperationLog(models.Model):
    provider = models.CharField("Сервис", max_length=40)
    operation = models.CharField("Операция", max_length=100)
    reference = models.CharField("Номер заказа / ссылка", max_length=100, blank=True)
    mock = models.BooleanField("Локальная имитация", default=True)
    success = models.BooleanField("Успешно", default=True)
    message = models.TextField("Сообщение", blank=True)
    created_at = models.DateTimeField("Время", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Операция интеграции"
        verbose_name_plural = "Журнал интеграций"


class Notification(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Заказ",
    )
    event = models.CharField("Событие", max_length=40)
    audience = models.CharField(
        "Получатель",
        max_length=20,
        choices=[
            ("customer", "Покупатель"),
            ("store", "Магазин"),
            ("telegram", "Администратор Telegram"),
        ],
    )
    recipient = models.CharField("Адрес / чат", max_length=250)
    subject = models.CharField("Тема", max_length=250)
    html = models.TextField("HTML письма", blank=True)
    text = models.TextField("Текстовая версия")
    status = models.CharField(
        "Статус",
        max_length=20,
        default="pending",
        choices=[
            ("pending", "В очереди"),
            ("simulated", "Имитировано"),
            ("sent", "Отправлено"),
            ("failed", "Ошибка"),
        ],
    )
    error = models.CharField("Ошибка", max_length=250, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "event", "audience"], name="notification_once"
            )
        ]
        verbose_name = "Уведомление"
        verbose_name_plural = "Письма и уведомления"
