import secrets
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


def make_token():
    return secrets.token_urlsafe(32)


class PromoCode(models.Model):
    code = models.CharField("Код", max_length=40, unique=True)
    percent = models.PositiveSmallIntegerField(
        "Скидка, %", validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    active = models.BooleanField("Действует", default=True)
    minimum = models.DecimalField(
        "Минимальная сумма товаров, ₽", max_digits=10, decimal_places=2, default=0
    )
    valid_until = models.DateTimeField("Действует до", null=True, blank=True)
    max_uses = models.PositiveIntegerField("Лимит применений", null=True, blank=True)
    uses = models.PositiveIntegerField(
        "Использован / зарезервирован", default=0, editable=False
    )

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        PAID = "paid", "Оплачен"
        SHIPPED = "shipped", "Передан в доставку"
        COMPLETE = "complete", "Завершён"
        CANCELED = "canceled", "Отменён"

    token = models.CharField(
        "Секретная ссылка",
        max_length=64,
        unique=True,
        default=make_token,
        editable=False,
    )
    request_key = models.UUIDField("Ключ повторного запроса", unique=True)
    payment_key = models.UUIDField("Ключ платежа", default=uuid.uuid4, editable=False)
    request_fingerprint = models.CharField(
        "Отпечаток запроса", max_length=64, editable=False
    )
    name = models.CharField("Имя и фамилия", max_length=150)
    email = models.EmailField("Email покупателя")
    phone = models.CharField("Телефон", max_length=30)
    city = models.CharField("Город", max_length=150)
    city_code = models.PositiveIntegerField("Код города СДЭК")
    delivery_method = models.CharField(
        "Доставка",
        max_length=10,
        choices=[("pickup", "Пункт выдачи"), ("courier", "Курьер")],
    )
    pickup_code = models.CharField("Код ПВЗ", max_length=80, blank=True)
    delivery_address = models.CharField("Адрес доставки", max_length=400)
    delivery_days = models.CharField("Срок доставки", max_length=100, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    status = models.CharField(
        "Статус", choices=Status.choices, default=Status.PENDING, max_length=20
    )
    subtotal = models.DecimalField("Сумма товаров, ₽", max_digits=12, decimal_places=2)
    discount = models.DecimalField(
        "Скидка, ₽", max_digits=12, decimal_places=2, default=0
    )
    shipping_cost = models.DecimalField("Доставка, ₽", max_digits=10, decimal_places=2)
    total = models.DecimalField("Итого, ₽", max_digits=12, decimal_places=2)
    promo = models.ForeignKey(
        PromoCode,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Промокод",
    )
    payment_id = models.CharField(
        "ID платежа ЮKassa", max_length=100, blank=True, db_index=True
    )
    payment_url = models.URLField("Ссылка оплаты", max_length=1000, blank=True)
    cdek_tracking = models.CharField(
        "Номер отправления СДЭК",
        max_length=100,
        blank=True,
        help_text="Подготовка отправления и передача посылки выполняются магазином после оплаты.",
    )
    expires_at = models.DateTimeField("Резерв до", db_index=True)
    paid_at = models.DateTimeField("Оплачен", null=True, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    consent_at = models.DateTimeField("Согласие с документами", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    @property
    def number(self):
        return f"AN-{self.pk:06d}"

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ"
    )
    variant = models.ForeignKey(
        "catalog.Variant", on_delete=models.PROTECT, verbose_name="Вариант"
    )
    name = models.CharField("Товар", max_length=200)
    sku = models.CharField("Артикул", max_length=80)
    size = models.CharField("Размер", max_length=20)
    color = models.CharField("Цвет", max_length=50)
    quantity = models.PositiveIntegerField("Количество")
    unit_price = models.DecimalField(
        "Цена до скидки, ₽", max_digits=10, decimal_places=2
    )
    unit_price_after_discount = models.DecimalField(
        "Цена со скидкой, ₽", max_digits=10, decimal_places=2
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Состав заказа"

    @property
    def line_total(self):
        return self.unit_price_after_discount * self.quantity
